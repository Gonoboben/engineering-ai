from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from engineering_ai.tools.common import ToolAccessError, ToolExecutionError
from engineering_ai.tools.filesystem import ReadOnlyFilesystemAdapter
from engineering_ai.tools.git import GitReadOnlyAdapter
from engineering_ai.tools.process import AllowListedProcessRunner, CommandSpec


class FilesystemAdapterTests(unittest.TestCase):
    def test_reads_and_lists_only_inside_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "note.txt").write_text("engineering", encoding="utf-8")
            adapter = ReadOnlyFilesystemAdapter(root)

            self.assertEqual(adapter.read_text("docs/note.txt"), "engineering")
            entries = adapter.list_directory("docs")
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].relative_path, "docs/note.txt")

    def test_rejects_absolute_and_parent_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = ReadOnlyFilesystemAdapter(root)
            with self.assertRaises(ToolAccessError):
                adapter.read_text(root / "absolute.txt")
            with self.assertRaises(ToolAccessError):
                adapter.read_text("../escape.txt")

    def test_rejects_symlink_escape_when_platform_allows_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            target = Path(outside) / "secret.txt"
            target.write_text("outside", encoding="utf-8")
            link = root / "link.txt"
            try:
                os.symlink(target, link)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable on this platform/account")
            adapter = ReadOnlyFilesystemAdapter(root)
            with self.assertRaises(ToolAccessError):
                adapter.read_text("link.txt")

    def test_read_size_limit_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "large.txt").write_text("x" * 128, encoding="utf-8")
            adapter = ReadOnlyFilesystemAdapter(root, max_read_bytes=32)
            with self.assertRaises(ToolExecutionError):
                adapter.read_text("large.txt")


class ProcessRunnerTests(unittest.TestCase):
    def test_runs_only_allowlisted_fixed_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec = CommandSpec(
                command_id="python-smoke",
                executable=sys.executable,
                fixed_args=("-c", "print('tool-pass')"),
            )
            runner = AllowListedProcessRunner({"python-smoke": spec}, root=tmp)
            result = runner.run("python-smoke")
            self.assertTrue(result.ok)
            self.assertEqual(result.stdout.strip(), "tool-pass")

            with self.assertRaises(ToolAccessError):
                runner.run("not-allowed")

    def test_timeout_is_terminal_and_structured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec = CommandSpec(
                command_id="timeout-test",
                executable=sys.executable,
                fixed_args=("-c", "import time; time.sleep(2)"),
                timeout_seconds=0.05,
            )
            runner = AllowListedProcessRunner({"timeout-test": spec}, root=tmp)
            result = runner.run("timeout-test")
            self.assertFalse(result.ok)
            self.assertTrue(result.timed_out)

    def test_output_is_truncated_to_configured_bound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec = CommandSpec(
                command_id="bounded-output",
                executable=sys.executable,
                fixed_args=("-c", "print('x' * 1000)"),
                max_output_bytes=32,
            )
            runner = AllowListedProcessRunner({"bounded-output": spec}, root=tmp)
            result = runner.run("bounded-output")
            self.assertTrue(result.ok)
            self.assertTrue(result.truncated)
            self.assertLessEqual(len(result.stdout.encode("utf-8")), 32)

    def test_cwd_cannot_escape_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec = CommandSpec(
                command_id="cwd-test",
                executable=sys.executable,
                fixed_args=("-c", "print('ok')"),
            )
            runner = AllowListedProcessRunner({"cwd-test": spec}, root=tmp)
            with self.assertRaises(ToolAccessError):
                runner.run("cwd-test", cwd="..")


@unittest.skipIf(shutil.which("git") is None, "git executable is required")
class GitAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.invalid"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Engineering AI Test"],
            cwd=self.root,
            check=True,
        )
        (self.root / "file.txt").write_text("one\n", encoding="utf-8")
        subprocess.run(["git", "add", "file.txt"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=self.root, check=True, capture_output=True)
        self.adapter = GitReadOnlyAdapter(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_status_head_branch_log_and_diff_are_read_only(self) -> None:
        self.assertTrue(self.adapter.status().ok)
        self.assertTrue(self.adapter.head_sha().ok)
        self.assertEqual(len(self.adapter.head_sha().stdout.strip()), 40)
        self.assertTrue(self.adapter.current_branch().ok)
        self.assertIn("initial", self.adapter.log(max_count=1).stdout)

        (self.root / "file.txt").write_text("one\ntwo\n", encoding="utf-8")
        diff = self.adapter.diff_worktree()
        self.assertTrue(diff.ok)
        self.assertIn("+two", diff.stdout)

    def test_no_public_generic_git_command_api(self) -> None:
        self.assertFalse(hasattr(self.adapter, "run"))
        self.assertFalse(hasattr(self.adapter, "execute"))
        with self.assertRaises(ValueError):
            self.adapter.diff_between("--output=evil", "HEAD")
        with self.assertRaises(ValueError):
            self.adapter.log(max_count=101)


if __name__ == "__main__":
    unittest.main()
