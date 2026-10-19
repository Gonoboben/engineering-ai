from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from engineering_ai.projects import (
    BuoyCalcControlledEngineeringLoop,
    BuoyCalcControlledState,
)
from engineering_ai.projects.buoycalc import RELEASE_STATE
from engineering_ai.projects.buoycalc_controlled import (
    RuntimePrerequisiteStatus,
    _VALIDATOR_PROFILES,
    _VALIDATOR_SPECS,
)
from engineering_ai.supervisor.policy import Decision, PolicyEngine
from engineering_ai.tools import (
    NetworkRequirement,
    PatchProposal,
    ToolAccessError,
    ToolExecutionError,
    ToolResult,
)
from engineering_ai.validation import validate_instance


ROOT = Path(__file__).resolve().parents[1]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def satisfied_runtime() -> RuntimePrerequisiteStatus:
    return RuntimePrerequisiteStatus(
        dotnet_executable=sys.executable,
        pwsh_executable=sys.executable,
        dotnet_sdk8_available=True,
        dotnet_sdks=("8.0.999 [synthetic]",),
        blockers=(),
    )


class _FakeRunner:
    fail_step: str | None = None
    mutate_path: str | None = None

    def __init__(self, specs, *, root, offline=False):
        self.root = Path(root)
        self.offline = offline

    def run(self, command_id: str, *, cwd=".") -> ToolResult:
        if self.mutate_path is not None:
            path = self.root / self.mutate_path
            path.write_text("validator mutation\n", encoding="utf-8")
            self.__class__.mutate_path = None

        failed = command_id == self.fail_step
        return ToolResult(
            ok=not failed,
            operation=command_id,
            summary="fake",
            stdout=f"{command_id}:stdout",
            stderr="" if not failed else "fake failure",
            exit_code=0 if not failed else 7,
            timed_out=False,
            truncated=False,
        )


class Gate015SmokeHarnessTests(unittest.TestCase):
    def test_missing_repository_is_structured(self) -> None:
        missing = ROOT / "definitely-missing-buoycalc-gate015"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/gate015_buoycalc_controlled_smoke.py"),
                "--repository",
                str(missing),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["state"], "LOCAL_REPOSITORY_NOT_FOUND")
        self.assertEqual(payload["physical_validation"], "PHYSICAL_NOT_EXECUTED")
        self.assertEqual(result.stderr, "")

    def test_worktree_requires_explicit_cli_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/gate015_buoycalc_controlled_smoke.py"),
                    "--repository",
                    tmp,
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 3)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["state"], "NEEDS_HUMAN_APPROVAL")
        self.assertEqual(payload["required_action"], "write_worktree")
        self.assertEqual(payload["physical_validation"], "PHYSICAL_NOT_EXECUTED")
        self.assertEqual(result.stderr, "")


@unittest.skipIf(shutil.which("git") is None, "git executable is required")
class BuoyCalcControlledLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_tmp = tempfile.TemporaryDirectory()
        self.origin_tmp = tempfile.TemporaryDirectory()
        self.worktree_tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.repo_tmp.name)
        self.origin = Path(self.origin_tmp.name) / "origin.git"
        self.worktree_parent = Path(self.worktree_tmp.name)

        subprocess.run(
            ["git", "init", "--bare", str(self.origin)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )
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
        subprocess.run(
            ["git", "remote", "add", "origin", str(self.origin)],
            cwd=self.root,
            check=True,
        )

        files = {
            "AGENTS.md": (
                "# BuoyCalc fixture\n"
                "The only user-facing geometry with engineering meaning is the selected calculated X/Z shape.\n"
            ),
            "docs/OPTIMIZATION_PLAN.md": (
                "# Optimization\n"
                "Engineering physics lives only in the calculation/solver domain.\n"
                "UI, PDF, 2D and report layers render calculated data; they do not invent coordinates.\n"
            ),
            "RELEASE.md": (
                "# Release\n"
                "Запрещено создавать git tag `v1.0.0` или GitHub Release до явного подтверждения пользователя.\n"
                "segmentation = 0.20 m\n"
                "signed feedback budget = 64\n"
                "signed WeightWaterKgM semantics = unchanged\n"
                "Accepted signed candidate = exact deterministic fixed point\n"
                "renderers = presentation only\n"
                "3D = post-v1\n"
            ),
            "docs/note.md": "before\n",
            "Views/InfoPanel.cs": "before presentation\n",
            "Services/MooringShapeSolver.cs": "core before\n",
            "tools/check-repository-governance.ps1": "Write-Host PASS\n",
        }
        for relative, content in files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode("utf-8"))

        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "fixture"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )
        self.base_sha = self._git("rev-parse", "HEAD").strip()

    def tearDown(self) -> None:
        _FakeRunner.fail_step = None
        _FakeRunner.mutate_path = None
        self.repo_tmp.cleanup()
        self.origin_tmp.cleanup()
        self.worktree_tmp.cleanup()

    def _git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def loop(self, *, offline: bool = False) -> BuoyCalcControlledEngineeringLoop:
        return BuoyCalcControlledEngineeringLoop(
            self.root,
            self.worktree_parent,
            offline=offline,
        )

    def prepare(self, name: str = "gate015-test"):
        return self.loop().prepare(
            worktree_name=name,
            branch=f"engineering-ai/buoycalc/{name}",
            base_ref="HEAD",
        )

    def test_controlled_non_core_patch_validate_restore_cleanup(self) -> None:
        loop = self.loop()
        prep = loop.prepare(
            worktree_name="pass",
            branch="engineering-ai/buoycalc/pass",
        )
        self.assertEqual(prep.state, BuoyCalcControlledState.WORKTREE_READY)
        self.assertEqual(prep.blockers, ())
        assert prep.session is not None

        worktree_target = Path(prep.session.worktree_root) / "docs" / "note.md"
        original_worktree_content = worktree_target.read_bytes().decode("utf-8")
        proposal = PatchProposal(
            relative_path="docs/note.md",
            expected_sha256=hashlib.sha256(worktree_target.read_bytes()).hexdigest(),
            new_content="after\n",
            rationale="synthetic non-core controlled patch",
        )
        applied = loop.apply_patch(
            session=prep.session,
            proposal=proposal,
            allowed_paths=("docs/note.md",),
        )
        self.assertEqual(applied.state, BuoyCalcControlledState.PATCH_APPLIED)
        self.assertEqual(
            (self.root / "docs/note.md").read_text(encoding="utf-8"),
            "before\n",
        )

        with patch.object(
            loop,
            "runtime_prerequisites",
            return_value=satisfied_runtime(),
        ), patch(
            "engineering_ai.projects.buoycalc_controlled.AllowListedProcessRunner",
            _FakeRunner,
        ):
            validated = loop.validate(session=prep.session)

        self.assertEqual(
            validated.state, BuoyCalcControlledState.READY_FOR_HUMAN_APPROVAL
        )
        self.assertTrue(validated.tracked_state_unchanged)
        self.assertEqual(validated.release_state, RELEASE_STATE)
        self.assertEqual(validated.physical_validation, "PHYSICAL_NOT_EXECUTED")
        self.assertEqual(
            tuple(item.profile_id for item in validated.profiles),
            loop.validator_profiles,
        )
        self.assertTrue(all(item.passed for item in validated.profiles))
        self.assertTrue(
            all(
                step.validation_class == "SOFTWARE_DETERMINISTIC"
                for profile in validated.profiles
                for step in profile.steps
            )
        )

        rollback = PatchProposal(
            relative_path="docs/note.md",
            expected_sha256=applied.application.after_sha256,
            new_content=original_worktree_content,
            rationale="restore exact synthetic fixture bytes",
        )
        loop.apply_patch(
            session=prep.session,
            proposal=rollback,
            allowed_paths=("docs/note.md",),
        )
        loop.cleanup(prep.session)
        self.assertEqual(self._git("rev-parse", "HEAD").strip(), self.base_sha)
        self.assertEqual(self._git("status", "--porcelain").strip(), "")

    def test_validator_network_classification_is_explicit(self) -> None:
        by_id = {spec.command_id: spec for spec in _VALIDATOR_SPECS}
        network_capable = {
            command_id
            for command_id, spec in by_id.items()
            if spec.network_requirement is NetworkRequirement.NETWORK_CAPABLE
        }
        self.assertEqual(
            network_capable,
            {
                "buoycalc.restore_app",
                "buoycalc.restore_engineering_regression",
                "buoycalc.restore_validation_601",
            },
        )
        self.assertTrue(
            all(
                spec.network_requirement
                in {NetworkRequirement.LOCAL_ONLY, NetworkRequirement.NETWORK_CAPABLE}
                for spec in by_id.values()
            )
        )
        for profile_id in (
            "buoycalc.selected_shape_consumer_scan",
            "buoycalc.report_store_consumer_scan",
        ):
            self.assertTrue(
                all(
                    by_id[step_id].network_requirement
                    is NetworkRequirement.LOCAL_ONLY
                    for step_id in _VALIDATOR_PROFILES[profile_id]
                )
            )

    def test_offline_validation_blocks_restore_before_process_execution(self) -> None:
        loop = self.loop(offline=True)
        prep = loop.prepare(
            worktree_name="offline-block",
            branch="engineering-ai/buoycalc/offline-block",
        )
        self.assertEqual(prep.state, BuoyCalcControlledState.WORKTREE_READY)
        assert prep.session is not None

        with patch.object(
            loop,
            "runtime_prerequisites",
            return_value=satisfied_runtime(),
        ):
            result = loop.validate(
                session=prep.session,
                profiles=("buoycalc.dotnet_build",),
            )

        self.assertEqual(
            result.state,
            BuoyCalcControlledState.BLOCKED_RUNTIME_PREREQUISITE,
        )
        self.assertTrue(result.offline)
        self.assertTrue(result.tracked_state_unchanged)
        first = result.profiles[0].steps[0]
        self.assertEqual(first.step_id, "buoycalc.restore_app")
        self.assertFalse(first.ok)
        self.assertTrue(first.blocked)
        self.assertEqual(first.block_reason, "OFFLINE_NETWORK_REQUIRED")
        self.assertEqual(
            first.network_requirement,
            NetworkRequirement.NETWORK_CAPABLE.value,
        )
        self.assertIsNone(first.exit_code)

        loop.cleanup(prep.session)

    def test_governance_and_calculation_core_patch_targets_are_blocked(self) -> None:
        loop = self.loop()
        prep = loop.prepare(
            worktree_name="blocked-targets",
            branch="engineering-ai/buoycalc/blocked-targets",
        )
        assert prep.session is not None

        with self.assertRaises(ToolAccessError):
            loop.apply_patch(
                session=prep.session,
                proposal=PatchProposal(
                    relative_path="RELEASE.md",
                    expected_sha256=sha256_text(
                        (self.root / "RELEASE.md").read_text(encoding="utf-8")
                    ),
                    new_content="forbidden\n",
                    rationale="governance block test",
                ),
                allowed_paths=("RELEASE.md",),
            )

        with self.assertRaises(ToolAccessError):
            loop.apply_patch(
                session=prep.session,
                proposal=PatchProposal(
                    relative_path="Services/MooringShapeSolver.cs",
                    expected_sha256=sha256_text("core before\n"),
                    new_content="core after\n",
                    rationale="physics boundary block test",
                ),
                allowed_paths=("Services/MooringShapeSolver.cs",),
            )

        self.assertEqual(
            (Path(prep.session.worktree_root) / "Services/MooringShapeSolver.cs").read_text(
                encoding="utf-8"
            ),
            "core before\n",
        )
        loop.cleanup(prep.session)

    def test_stale_sha_and_allow_list_are_enforced_by_shared_worktree_adapter(self) -> None:
        loop = self.loop()
        prep = loop.prepare(
            worktree_name="stale",
            branch="engineering-ai/buoycalc/stale",
        )
        assert prep.session is not None
        target = Path(prep.session.worktree_root) / "docs/note.md"

        with self.assertRaises(ToolAccessError):
            loop.apply_patch(
                session=prep.session,
                proposal=PatchProposal(
                    relative_path="docs/note.md",
                    expected_sha256="0" * 64,
                    new_content="must-not-write\n",
                    rationale="stale sha test",
                ),
                allowed_paths=("docs/note.md",),
            )
        self.assertEqual(target.read_text(encoding="utf-8"), "before\n")

        with self.assertRaises(ToolAccessError):
            loop.apply_patch(
                session=prep.session,
                proposal=PatchProposal(
                    relative_path="docs/note.md",
                    expected_sha256=sha256_text("before\n"),
                    new_content="must-not-write\n",
                    rationale="allow list test",
                ),
                allowed_paths=("Views/InfoPanel.cs",),
            )
        self.assertEqual(target.read_text(encoding="utf-8"), "before\n")
        loop.cleanup(prep.session)

    def test_dirty_or_non_main_primary_blocks_worktree(self) -> None:
        (self.root / "docs/note.md").write_text("dirty\n", encoding="utf-8")
        blocked = self.loop().prepare(
            worktree_name="dirty",
            branch="engineering-ai/buoycalc/dirty",
        )
        self.assertEqual(blocked.state, BuoyCalcControlledState.BLOCKED_BASELINE)
        self.assertTrue(any("dirty" in item for item in blocked.blockers))
        self.assertIsNone(blocked.session)

    def test_wrong_branch_prefix_is_rejected(self) -> None:
        with self.assertRaises(ToolAccessError):
            self.loop().prepare(
                worktree_name="prefix",
                branch="engineering-ai/not-buoycalc/prefix",
            )

    def test_validator_failure_blocks_ready_state(self) -> None:
        loop = self.loop()
        prep = loop.prepare(
            worktree_name="validator-fail",
            branch="engineering-ai/buoycalc/validator-fail",
        )
        assert prep.session is not None
        _FakeRunner.fail_step = "buoycalc.build_release"
        with patch.object(
            loop,
            "runtime_prerequisites",
            return_value=satisfied_runtime(),
        ), patch(
            "engineering_ai.projects.buoycalc_controlled.AllowListedProcessRunner",
            _FakeRunner,
        ):
            result = loop.validate(session=prep.session)
        self.assertEqual(result.state, BuoyCalcControlledState.VALIDATION_FAILED)
        self.assertTrue(result.tracked_state_unchanged)
        self.assertTrue(any(not profile.passed for profile in result.profiles))
        loop.cleanup(prep.session)

    def test_validator_tracked_mutation_blocks_ready_state(self) -> None:
        loop = self.loop()
        prep = loop.prepare(
            worktree_name="validator-mutation",
            branch="engineering-ai/buoycalc/validator-mutation",
        )
        assert prep.session is not None
        worktree_note = Path(prep.session.worktree_root) / "docs/note.md"
        _FakeRunner.mutate_path = "docs/note.md"
        with patch.object(
            loop,
            "runtime_prerequisites",
            return_value=satisfied_runtime(),
        ), patch(
            "engineering_ai.projects.buoycalc_controlled.AllowListedProcessRunner",
            _FakeRunner,
        ):
            result = loop.validate(
                session=prep.session,
                profiles=("buoycalc.selected_shape_consumer_scan",),
            )
        self.assertEqual(result.state, BuoyCalcControlledState.VALIDATION_FAILED)
        self.assertFalse(result.tracked_state_unchanged)

        worktree_note.write_text("before\n", encoding="utf-8")
        loop.cleanup(prep.session)

    def test_missing_runtime_prerequisite_blocks_validation_before_runner(self) -> None:
        loop = self.loop()
        prep = loop.prepare(
            worktree_name="runtime-block",
            branch="engineering-ai/buoycalc/runtime-block",
        )
        assert prep.session is not None
        missing = RuntimePrerequisiteStatus(
            dotnet_executable=None,
            pwsh_executable=sys.executable,
            dotnet_sdk8_available=False,
            dotnet_sdks=(),
            blockers=("dotnet executable not found",),
        )
        with patch.object(
            loop,
            "runtime_prerequisites",
            return_value=missing,
        ), patch(
            "engineering_ai.projects.buoycalc_controlled.AllowListedProcessRunner"
        ) as runner_cls:
            with self.assertRaises(ToolExecutionError):
                loop.validate(session=prep.session)
            runner_cls.assert_not_called()
        loop.cleanup(prep.session)

    def test_unknown_validator_profile_is_rejected(self) -> None:
        loop = self.loop()
        prep = loop.prepare(
            worktree_name="unknown-profile",
            branch="engineering-ai/buoycalc/unknown-profile",
        )
        assert prep.session is not None
        with patch.object(
            loop,
            "runtime_prerequisites",
            return_value=satisfied_runtime(),
        ):
            with self.assertRaises(ToolAccessError):
                loop.validate(session=prep.session, profiles=("arbitrary.shell",))
        loop.cleanup(prep.session)

    def test_disposable_cleanup_allows_generated_untracked_files_only(self) -> None:
        loop = self.loop()
        prep = loop.prepare(
            worktree_name="generated-cleanup",
            branch="engineering-ai/buoycalc/generated-cleanup",
        )
        assert prep.session is not None
        worktree = Path(prep.session.worktree_root)
        generated = worktree / "artifacts/generated.txt"
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text("generated\n", encoding="utf-8")

        loop.cleanup_disposable_generated(prep.session)
        self.assertFalse(worktree.exists())
        branch = subprocess.run(
            [
                "git",
                "show-ref",
                "--verify",
                "refs/heads/engineering-ai/buoycalc/generated-cleanup",
            ],
            cwd=self.root,
            check=False,
            capture_output=True,
        )
        self.assertNotEqual(branch.returncode, 0)
        self.assertEqual(self._git("rev-parse", "HEAD").strip(), self.base_sha)

    def test_disposable_cleanup_falls_back_after_git_permission_denied(self) -> None:
        loop = self.loop()
        prep = loop.prepare(
            worktree_name="permission-fallback",
            branch="engineering-ai/buoycalc/permission-fallback",
        )
        assert prep.session is not None
        worktree = Path(prep.session.worktree_root)
        generated = worktree / "artifacts/generated.txt"
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text("generated\n", encoding="utf-8")

        adapter = loop._worktrees
        original_run_git = adapter._run_git
        remove_attempts = {"count": 0}

        def flaky_run_git(args, *, operation):
            if operation == "git.worktree_remove_disposable":
                remove_attempts["count"] += 1
                return subprocess.CompletedProcess(
                    args=args,
                    returncode=1,
                    stdout="",
                    stderr="error: failed to delete worktree: Permission denied",
                )
            return original_run_git(args, operation=operation)

        with patch.object(adapter, "_run_git", side_effect=flaky_run_git):
            loop.cleanup_disposable_generated(prep.session)

        self.assertEqual(remove_attempts["count"], 3)
        self.assertTrue(any(
            event["stage"] == "git_metadata_remove"
            for event in adapter.cleanup_events
        ))
        self.assertFalse(worktree.exists())
        branch = subprocess.run(
            [
                "git",
                "show-ref",
                "--verify",
                "refs/heads/engineering-ai/buoycalc/permission-fallback",
            ],
            cwd=self.root,
            check=False,
            capture_output=True,
        )
        self.assertNotEqual(branch.returncode, 0)
        self.assertEqual(self._git("rev-parse", "HEAD").strip(), self.base_sha)

    def test_disposable_cleanup_retries_transient_filesystem_lock(self) -> None:
        loop = self.loop()
        prep = loop.prepare(
            worktree_name="transient-lock-fallback",
            branch="engineering-ai/buoycalc/transient-lock-fallback",
        )
        assert prep.session is not None
        worktree = Path(prep.session.worktree_root)
        generated = worktree / "artifacts/generated.txt"
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text("generated\n", encoding="utf-8")

        adapter = loop._worktrees
        original_rmtree = shutil.rmtree
        rmtree_attempts = {"count": 0}

        def flaky_rmtree(path, *args, **kwargs):
            rmtree_attempts["count"] += 1
            if rmtree_attempts["count"] == 1:
                raise PermissionError(32, "synthetic transient directory lock", str(path))
            return original_rmtree(path, *args, **kwargs)

        with patch.object(
            adapter,
            "_remove_disposable_worktree_with_retry",
            return_value="fatal: not a working tree",
        ), patch(
            "engineering_ai.tools.worktree.shutil.rmtree",
            side_effect=flaky_rmtree,
        ), patch("engineering_ai.tools.worktree.time.sleep") as sleep_mock:
            loop.cleanup_disposable_generated(prep.session)

        self.assertEqual(rmtree_attempts["count"], 2)
        attempts = [
            event for event in loop.cleanup_events
            if event["stage"] == "filesystem_remove"
        ]
        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[0]["error_type"], "PermissionError")
        self.assertFalse(attempts[-1]["worktree_exists"])
        self.assertGreaterEqual(sleep_mock.call_count, 1)
        self.assertFalse(worktree.exists())
        branch = subprocess.run(
            [
                "git",
                "show-ref",
                "--verify",
                "refs/heads/engineering-ai/buoycalc/transient-lock-fallback",
            ],
            cwd=self.root,
            check=False,
            capture_output=True,
        )
        self.assertNotEqual(branch.returncode, 0)
        self.assertEqual(self._git("rev-parse", "HEAD").strip(), self.base_sha)
        self.assertEqual(self._git("status", "--porcelain").strip(), "")

    def test_disposable_cleanup_persistent_filesystem_lock_fails_closed(self) -> None:
        loop = self.loop()
        prep = loop.prepare(
            worktree_name="persistent-lock-fallback",
            branch="engineering-ai/buoycalc/persistent-lock-fallback",
        )
        assert prep.session is not None
        worktree = Path(prep.session.worktree_root)
        generated = worktree / "artifacts/generated.txt"
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text("generated\n", encoding="utf-8")

        adapter = loop._worktrees
        persistent = PermissionError(
            32,
            "synthetic persistent directory lock",
            str(worktree),
        )

        with patch.object(
            adapter,
            "_remove_disposable_worktree_with_retry",
            return_value="fatal: not a working tree",
        ), patch(
            "engineering_ai.tools.worktree.shutil.rmtree",
            side_effect=persistent,
        ) as rmtree_mock, patch(
            "engineering_ai.tools.worktree.time.sleep"
        ) as sleep_mock:
            with self.assertRaisesRegex(
                ToolExecutionError,
                "disposable worktree cleanup failed after git remove error",
            ):
                loop.cleanup_disposable_generated(prep.session)

        self.assertEqual(rmtree_mock.call_count, 10)
        attempts = [
            event for event in loop.cleanup_events
            if event["stage"] == "filesystem_remove"
        ]
        self.assertEqual(len(attempts), 10)
        self.assertTrue(all(event["worktree_exists"] for event in attempts))
        self.assertGreaterEqual(sleep_mock.call_count, 9)
        self.assertTrue(worktree.exists())
        branch = subprocess.run(
            [
                "git",
                "show-ref",
                "--verify",
                "refs/heads/engineering-ai/buoycalc/persistent-lock-fallback",
            ],
            cwd=self.root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(branch.returncode, 0)
        self.assertIn(self.base_sha, branch.stdout)
        self.assertEqual(self._git("rev-parse", "HEAD").strip(), self.base_sha)
        self.assertEqual(self._git("status", "--porcelain").strip(), "")

        loop.cleanup_disposable_generated(prep.session)
        self.assertFalse(worktree.exists())


    def test_disposable_cleanup_rejects_tracked_diff(self) -> None:
        loop = self.loop()
        prep = loop.prepare(
            worktree_name="tracked-cleanup-block",
            branch="engineering-ai/buoycalc/tracked-cleanup-block",
        )
        assert prep.session is not None
        worktree = Path(prep.session.worktree_root)
        note = worktree / "docs/note.md"
        note.write_text("tracked mutation\n", encoding="utf-8")

        with self.assertRaises(ToolAccessError):
            loop.cleanup_disposable_generated(prep.session)

        note.write_text("before\n", encoding="utf-8")
        loop.cleanup(prep.session)

    def test_controlled_loop_exposes_no_remote_or_release_api(self) -> None:
        loop = self.loop()
        loop.assert_no_remote_or_release_api(loop)
        for name in (
            "commit",
            "push",
            "open_pr",
            "merge_pr",
            "release",
            "package_release",
            "publish",
            "create_tag",
            "authorize_release",
        ):
            self.assertFalse(hasattr(loop, name))

    def test_fixed_validator_profiles_exclude_publish_and_release_commands(self) -> None:
        self.assertEqual(
            set(_VALIDATOR_PROFILES),
            {
                "buoycalc.dotnet_build",
                "buoycalc.selected_shape_consumer_scan",
                "buoycalc.report_store_consumer_scan",
                "buoycalc.validation_601",
            },
        )
        flattened = " ".join(
            " ".join((spec.executable, *spec.fixed_args))
            for spec in _VALIDATOR_SPECS
        ).casefold()
        self.assertNotIn("publish-windows.ps1", flattened)
        self.assertNotIn("package-windows-rc.ps1", flattened)
        self.assertNotIn("verify-windows-rc.ps1", flattened)
        self.assertNotIn("git tag", flattened)
        self.assertNotIn("gh release", flattened)


@unittest.skipIf(shutil.which("git") is None, "git executable is required")
class Gate015RecoveryHarnessTests(unittest.TestCase):
    def test_already_deregistered_exact_smoke_residue_is_cleaned(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp, tempfile.TemporaryDirectory() as origin_tmp, tempfile.TemporaryDirectory(prefix="engineering-ai-gate015-buoycalc-") as parent_tmp:
            repo = Path(repo_tmp)
            origin = Path(origin_tmp) / "origin.git"
            subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)
            subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Engineering AI Test"], cwd=repo, check=True)
            subprocess.run(["git", "remote", "add", "origin", str(origin)], cwd=repo, check=True)
            (repo / "tracked.txt").write_text("baseline\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "baseline"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=repo, check=True, capture_output=True)
            base_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            suffix = base_sha[:12]
            branch = f"engineering-ai/buoycalc/gate015-smoke-{suffix}"
            subprocess.run(["git", "branch", branch, base_sha], cwd=repo, check=True)

            parent = Path(parent_tmp)
            worktree = parent / f"gate015-{suffix}"
            worktree.mkdir()
            (worktree / "generated.tmp").write_text("residue\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/gate015_cleanup_stale_worktree.py"),
                    "--repository",
                    str(repo),
                    "--worktree",
                    str(worktree),
                    "--branch",
                    branch,
                    "--base-sha",
                    base_sha,
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["state"], "STALE_DISPOSABLE_WORKTREE_CLEANED")
            self.assertFalse(payload["registered_before_cleanup"])
            self.assertTrue(payload["worktree_removed"])
            self.assertTrue(payload["branch_removed"])
            self.assertTrue(payload["repository_unchanged"])
            self.assertFalse(worktree.exists())

    def test_recovery_refuses_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Engineering AI Test"], cwd=repo, check=True)
            (repo / "tracked.txt").write_text("baseline\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "baseline"], cwd=repo, check=True, capture_output=True)
            base_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            with tempfile.TemporaryDirectory(prefix="engineering-ai-gate015-buoycalc-") as parent_tmp:
                worktree = Path(parent_tmp) / "wrong-name"
                worktree.mkdir()
                result = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts/gate015_cleanup_stale_worktree.py"),
                        "--repository",
                        str(repo),
                        "--worktree",
                        str(worktree),
                        "--branch",
                        f"engineering-ai/buoycalc/gate015-smoke-{base_sha[:12]}",
                        "--base-sha",
                        base_sha,
                    ],
                    cwd=ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                )
            self.assertEqual(result.returncode, 2)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["state"], "REFUSED")
            self.assertIn("exact smoke identity", payload["reason"])


class Gate015PolicyTests(unittest.TestCase):
    def test_controlled_profile_policy_validate_and_preserve_approval_boundary(self) -> None:
        profile = json.loads(
            (ROOT / "profiles/buoycalc-controlled.json").read_text(encoding="utf-8")
        )
        policy = json.loads(
            (ROOT / "profiles/buoycalc-controlled-policy.json").read_text(
                encoding="utf-8"
            )
        )
        validate_instance("project-profile.schema.json", profile)
        validate_instance("project-policy.schema.json", policy)

        self.assertEqual(
            set(profile["tool_profiles"]),
            set(_VALIDATOR_PROFILES),
        )
        self.assertEqual(
            set(policy["mandatory_validators"]),
            set(_VALIDATOR_PROFILES),
        )

        state = {
            "schema_version": "1.0",
            "state_revision": 1,
            "project_id": "buoycalc",
            "current_gate": "015",
            "active_job_id": None,
            "repository_ref": {
                "branch": "main",
                "head_sha": "0123456789abcdef0123456789abcdef01234567",
            },
            "architecture_baseline": "BuoyCalc v1.0.0 frozen engineering baseline",
            "effective_permissions": {
                "autonomous": policy["autonomous_actions"],
                "approval_required": policy["approval_required_actions"],
                "forbidden": policy["forbidden_actions"],
            },
            "pending_checks": [],
            "blockers": [],
            "validation_states": [
                {
                    "check_id": "physical-validation",
                    "validation_class": "PHYSICAL",
                    "state": "PHYSICAL_NOT_EXECUTED",
                    "evidence_refs": [],
                }
            ],
            "next_admissible_action": None,
        }
        engine = PolicyEngine(policy, state)
        self.assertEqual(engine.evaluate("run_validator").decision, Decision.ALLOW)
        self.assertEqual(engine.evaluate("propose_patch").decision, Decision.ALLOW)
        self.assertEqual(
            engine.evaluate("write_worktree").decision,
            Decision.NEEDS_HUMAN_APPROVAL,
        )
        self.assertEqual(
            engine.evaluate(
                "write_worktree",
                approval_obtained=True,
                approver="human-owner",
            ).decision,
            Decision.ALLOW,
        )
        for action in (
            "run_calculation",
            "local_commit",
            "push_remote",
            "open_pr",
            "merge_pr",
            "release_authorization",
            "physics_change",
            "validator_weakening",
        ):
            self.assertEqual(engine.evaluate(action).decision, Decision.DENY)


@unittest.skipIf(shutil.which("git") is None, "git executable is required")
class DisposableWorktreeP0Tests(unittest.TestCase):
    """Existing commits only; every repository/holder is isolated and owned."""

    def setUp(self) -> None:
        from engineering_ai.tools.worktree import ControlledWorktreeAdapter
        self.fixture = Path(tempfile.mkdtemp(prefix="worktree-p0-"))
        configured = os.environ.get("P0_TEST_EVIDENCE")
        self.evidence_path = (
            Path(configured).resolve() if configured else
            Path(tempfile.mkdtemp(prefix="worktree-p0-evidence-")).resolve()
        )
        if self.evidence_path.is_relative_to(self.fixture.resolve()):
            raise ValueError("test evidence must be outside the disposable fixture")
        ControlledWorktreeAdapter._reject_reparse_points(self.evidence_path)
        self.evidence_path.mkdir(parents=True, exist_ok=True)
        self.evidence_counter = 0
        self.test_sessions = []
        self.root = self.fixture / "repo"
        self.parent = self.fixture / "worktrees"
        self.parent.mkdir()
        template = self.fixture / "empty-template"
        template.mkdir()
        self._command(
            self.fixture, "clone", "--no-local", "--no-hardlinks", "--no-checkout",
            "--no-tags", "--template=" + str(template), str(ROOT), str(self.root),
        )
        self._command(self.root, "remote", "remove", "origin")
        self.base_sha = self._command(ROOT, "rev-parse", "HEAD").stdout.strip()
        self._command(self.root, "checkout", "--detach", self.base_sha)
        self.assertFalse((self.root / ".git/objects/info/alternates").exists())
        self.assertTrue(all(p.stat().st_nlink == 1 for p in (self.root / ".git/objects").rglob("*") if p.is_file()))
        self.adapter = ControlledWorktreeAdapter(self.root, self.parent)
        self.holders = []
        self.observations = []

    def _command(self, cwd: Path, *args: str):
        return subprocess.run(
            ["git", "--no-optional-locks", "-c", "core.hooksPath=" + str(self.fixture / "empty-template"),
             "-c", "gc.auto=0", "-c", "maintenance.auto=false", *args],
            cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True,
            encoding="utf-8", timeout=30, check=True,
        )

    def session(self, name="owned"):
        session = self.adapter.create_worktree(
            worktree_name=name, branch="engineering-ai/p0/" + name, base_ref=self.base_sha,
        )
        self.test_sessions.append((session, self.adapter._session_metadata[session.worktree_root]))
        return session

    def _fixture_snapshot(self):
        import datetime
        registrations = set()
        branches = {}
        repository_exists = self.root.exists()
        if repository_exists:
            listing = self._command(self.root, "worktree", "list", "--porcelain", "-z").stdout
            registrations = {
                str(Path(field[9:]).resolve()) for field in listing.split("\0")
                if field.startswith("worktree ")
            }
            for line in self._command(
                self.root, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads",
            ).stdout.splitlines():
                ref, full_sha = line.split(" ", 1)
                branches[ref] = full_sha
        return dict(
            utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            fixture_exists=self.fixture.exists(), repository_exists=repository_exists,
            registration_probe_state="MEASURED" if repository_exists else "REPOSITORY_ABSENT",
            worktrees=[
                dict(path=session.worktree_root,
                     physical_exists=Path(session.worktree_root).exists(),
                     registered=(session.worktree_root in registrations) if repository_exists else None,
                     metadata_path=str(metadata), metadata_exists=metadata.exists(),
                     branch=session.branch,
                     branch_sha=branches.get("refs/heads/" + session.branch) if repository_exists else None)
                for session, metadata in self.test_sessions
            ],
        )

    def _short_test_id(self):
        return hashlib.sha256(self.id().encode("utf-8")).hexdigest()[:12]

    def _fixture_id(self):
        # tempfile's unique eight-character suffix; full identity stays in JSON.
        identity = self.fixture.name.removeprefix("worktree-p0-")
        self.assertEqual(len(identity), 8)
        return identity

    def _checked_evidence_path(self, *parts):
        path = self.evidence_path.joinpath(*parts)
        self.assertLess(len(str(path)), 240, "laboratory evidence path budget")
        self.assertTrue(path.resolve().is_relative_to(self.evidence_path.resolve()))
        self.assertFalse(path.resolve().is_relative_to(self.fixture.resolve()))
        self.adapter._reject_reparse_points(path)
        return path

    def _evidence(self, **extra):
        import datetime
        self.evidence_counter += 1
        self.assertLessEqual(self.evidence_counter, 999)
        name = f"t{self._short_test_id()}-f{self._fixture_id()}-e{self.evidence_counter:03d}"
        primary = self._checked_evidence_path(name + ".json")
        location_check = self._checked_evidence_path(name + ".loc.json")
        before = self._fixture_snapshot()
        record = dict(
            utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            test=self.id(), test_id=self.id(), fixture=str(self.fixture),
            fixture_id=self.fixture.name, evidence_ordinal=self.evidence_counter,
            evidence_path=str(primary), after_measurements_source=str(location_check),
            base_sha=self.base_sha,
            cleanup_events=list(self.adapter.cleanup_events),
            observations=self.observations, fixture_before_evidence=before, **extra,
        )
        destination = self.evidence_path
        self.assertFalse(destination.is_relative_to(self.fixture.resolve()))
        self.adapter._reject_reparse_points(destination)
        with primary.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
        after = self._fixture_snapshot()
        with location_check.open("x", encoding="utf-8") as stream:
            json.dump(dict(
                utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                test=self.id(), test_id=self.id(), fixture=str(self.fixture),
                fixture_id=self.fixture.name, evidence_ordinal=self.evidence_counter,
                evidence_path=str(primary), location_check_path=str(location_check),
                before=before, after=after,
            ), stream, ensure_ascii=False, indent=2)
        self.assertEqual(
            {k: v for k, v in before.items() if k != "utc"},
            {k: v for k, v in after.items() if k != "utc"},
            "writing evidence changed/recreated the disposable filesystem state",
        )

    def tearDown(self) -> None:
        result = self._outcome.result if self._outcome is not None else None
        failed = result is not None and any(
            case is self for case, _ in (*result.errors, *result.failures)
        )
        alive = [p.pid for p in self.holders if p.poll() is None]
        if failed or alive:
            self._evidence(state="STOP_PRESERVED", holders_alive=alive)
            return
        try:
            self.assertEqual(self.fixture, self.fixture.resolve())
            self.assertEqual(self.fixture.parent, Path(tempfile.gettempdir()).resolve())
            self.assertTrue(self.fixture.name.startswith("worktree-p0-"))
            self.adapter._reject_reparse_points(self.fixture, subtree=True)
            registration = self._command(self.root, "worktree", "list", "--porcelain").stdout
            self.assertEqual(registration.count("worktree "), 1)
            self.assertEqual(self._command(
                self.root, "for-each-ref", "--format=%(refname)", "refs/heads",
            ).stdout, "")
            self.observations.append(dict(
                operation="verified_before_fixture_delete",
                state=self._fixture_snapshot(),
            ))
            # Only this owned fixture, checked above; retry readonly files once.
            def clear_readonly(function, path, exc_info):
                import stat
                os.chmod(path, stat.S_IWRITE)
                function(path)
            shutil.rmtree(self.fixture, onerror=clear_readonly)
            self.assertFalse(self.fixture.exists())
        except Exception:
            self._evidence(state="STOP_PRESERVED", holders_alive=alive)
            raise
        self._evidence(state="PASS", holders_alive=[], fixture_deleted=True)

    @staticmethod
    def _identity(holder):
        import ctypes
        from ctypes import wintypes as w
        class FT(ctypes.Structure):
            _fields_ = [("lo", w.DWORD), ("hi", w.DWORD)]
        dll = ctypes.WinDLL("kernel32", use_last_error=True)
        dll.GetProcessTimes.argtypes = [w.HANDLE, *[ctypes.POINTER(FT)] * 4]
        dll.GetProcessTimes.restype = w.BOOL
        values = [FT() for _ in range(4)]
        if not dll.GetProcessTimes(int(holder._handle), *[ctypes.byref(x) for x in values]):
            raise ctypes.WinError(ctypes.get_last_error())
        return dict(
            pid=holder.pid, creation_filetime=(values[0].hi << 32) | values[0].lo,
            exit_filetime=(values[1].hi << 32) | values[1].lo,
        )

    def _wait_json(self, path, holder):
        import time
        end = time.monotonic() + 8
        while time.monotonic() < end:
            if path.exists():
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    pass
            self.assertIsNone(holder.poll(), "holder exited before handshake")
            time.sleep(.01)
        self.fail("bounded holder handshake timeout")

    def _windows_case(self, mode, access=None, share=None):
        session = self.session()
        target = Path(session.worktree_root)
        signal = self._checked_evidence_path(
            "s-" + self._short_test_id() + "-" + self._fixture_id(),
        )
        for filename in ("READY.json", "PROBE", "PROBE.json", "RELEASE", "RELEASED.json",
                         "stdout.txt", "stderr.txt"):
            self._checked_evidence_path(signal.name, filename)
        signal.mkdir()
        script = r"""
import os,sys,pathlib,time,json,ctypes as C,datetime
from ctypes import wintypes as W
target=pathlib.Path(sys.argv[1]);outside=pathlib.Path(sys.argv[2]);sig=pathlib.Path(sys.argv[3])
mode=sys.argv[4];access=int(sys.argv[5]);share=int(sys.argv[6])
K=C.WinDLL('kernel32',use_last_error=True)
class FT(C.Structure):_fields_=[('lo',W.DWORD),('hi',W.DWORD)]
class FI(C.Structure):_fields_=[('attr',W.DWORD),('creation',FT),('access',FT),('write',FT),('volume',W.DWORD),('sizehi',W.DWORD),('sizelo',W.DWORD),('links',W.DWORD),('indexhi',W.DWORD),('indexlo',W.DWORD)]
for name,args,rt in [('CreateFileW',[W.LPCWSTR,W.DWORD,W.DWORD,W.LPVOID,W.DWORD,W.DWORD,W.HANDLE],W.HANDLE),('GetProcessTimes',[W.HANDLE,*[C.POINTER(FT)]*4],W.BOOL),('GetCurrentProcess',[],W.HANDLE),('GetHandleInformation',[W.HANDLE,C.POINTER(W.DWORD)],W.BOOL),('GetFileInformationByHandle',[W.HANDLE,C.POINTER(FI)],W.BOOL),('CloseHandle',[W.HANDLE],W.BOOL)]:
 f=getattr(K,name);f.argtypes=args;f.restype=rt
a=[FT() for _ in range(4)]
assert K.GetProcessTimes(K.GetCurrentProcess(),*[C.byref(x) for x in a])
identity=dict(pid=os.getpid(),ppid=os.getppid(),creation_filetime=(a[0].hi<<32)|a[0].lo)
def save(n,**data):
 with (sig/n).open('x',encoding='utf-8') as f:json.dump(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),identity=identity,cwd=os.getcwd(),**data),f)
h=None;create_error=None;start=time.monotonic()
try:
 if mode!='cwd':
  C.set_last_error(0);h=K.CreateFileW(str(target),access,share,None,3,0x02000000,None)
  create_error=C.get_last_error()
  assert h and h!=C.c_void_p(-1).value,create_error
 def resource():
  if h is None:return dict(cwd_only=True,cwd=os.getcwd())
  flags=W.DWORD();info=FI();assert K.GetHandleInformation(h,C.byref(flags)),C.get_last_error()
  assert K.GetFileInformationByHandle(h,C.byref(info)),C.get_last_error()
  return dict(handle=int(h),valid=True,create_last_error=create_error,flags=flags.value,access=access,share=share,volume=info.volume,file_index=(info.indexhi<<32)|info.indexlo)
 save('READY.json',resource=resource(),ttl_seconds=30)
 while time.monotonic()-start<30:
  if (sig/'PROBE').exists() and not (sig/'PROBE.json').exists():save('PROBE.json',resource=resource())
  if (sig/'RELEASE').exists():break
  time.sleep(.01)
 else:raise RuntimeError('TTL expired before RELEASE')
finally:
 if h is not None:assert K.CloseHandle(h),C.get_last_error()
 os.chdir(outside)
 save('RELEASED.json',released=True)
"""
        argv = [sys.executable, "-B", "-c", script, str(target), str(self.fixture),
                str(signal), mode, str(access or 0), str(share or 0)]
        with (signal / "stdout.txt").open("x", encoding="utf-8") as out, (signal / "stderr.txt").open("x", encoding="utf-8") as err:
            holder = subprocess.Popen(
                argv, cwd=target if mode == "cwd" else self.fixture,
                stdin=subprocess.DEVNULL, stdout=out, stderr=err, close_fds=True,
            )
        self.holders.append(holder)
        identity = None
        try:
            identity = self._identity(holder)
            ready = self._wait_json(signal / "READY.json", holder)
            self.assertEqual(ready["identity"]["pid"], holder.pid)
            self.assertEqual(ready["identity"]["creation_filetime"], identity["creation_filetime"])
            self.assertEqual(ready["identity"]["ppid"], os.getpid())
            self.assertEqual(Path(ready["cwd"]), target if mode == "cwd" else self.fixture)
            self.assertEqual(self._identity(holder)["exit_filetime"], 0)
            before = self.adapter._cleanup_state(target, session)
            self.assertTrue(before["registered"] and before["metadata_exists"])
            self.assertEqual(before["branch_sha"], self.base_sha)
            locked = mode == "cwd" or (access == 1 and share == 3)
            if locked:
                with self.assertRaises(ToolExecutionError):
                    self.adapter.cleanup_disposable_generated(session)
                attempts = [x for x in self.adapter.cleanup_events if x["stage"] == "git_worktree_remove"]
                self.assertEqual(len(attempts), 1)
                self.assertNotEqual(attempts[0]["exit_code"], 0)
                self.assertIn("Permission denied", attempts[0]["git_stderr"])
                state = attempts[0]["after"]
                self.assertTrue(state["worktree_exists"])
                self.assertFalse(state["registered"] or state["metadata_exists"])
                self.assertEqual(state["branch_sha"], self.base_sha)
                fs = [x for x in self.adapter.cleanup_events if x["stage"] == "filesystem_remove"]
                self.assertEqual(len(fs), 10)
                self.assertTrue(all(x["winerror"] == 32 for x in fs))
                self.assertEqual(self.adapter.cleanup_events[-1]["stage"], "cleanup_stopped")
            else:
                self.adapter.cleanup_disposable_generated(session)
                self.assertFalse(target.exists())
                last = self.adapter.cleanup_events[-1]["state"]
                self.assertFalse(last["registered"] or last["metadata_exists"] or last["branch_exists"])
            signal.joinpath("PROBE").touch()
            probe = self._wait_json(signal / "PROBE.json", holder)
            self.assertEqual(probe["resource"], ready["resource"])
            self.observations.append(dict(mode=mode, before=before, ready=ready, probe=probe,
                                          failed_attempt_events=list(self.adapter.cleanup_events)))
        finally:
            signal.joinpath("RELEASE").touch(exist_ok=True)
            self.assertEqual(holder.wait(timeout=6), 0)
            released = self._wait_json(signal / "RELEASED.json", holder)
            final_identity = self._identity(holder)
            if identity is not None:
                self.assertEqual(identity["creation_filetime"], final_identity["creation_filetime"])
            self.assertGreater(final_identity["exit_filetime"], 0)
            self.observations.append(dict(released=released, native_exit=final_identity))
        if locked:
            self.adapter.cleanup_disposable_generated(session)
            self.assertFalse(target.exists())
            self.assertFalse(any(x["stage"] == "git_worktree_remove" for x in self.adapter.cleanup_events))
        final = self.adapter.cleanup_events[-1]["state"]
        self.assertFalse(final["worktree_exists"] or final["registered"] or final["metadata_exists"] or final["branch_exists"])

    @unittest.skipUnless(os.name == "nt", "Windows required")
    def test_cwd_only_lock(self):
        self._windows_case("cwd")

    @unittest.skipUnless(os.name == "nt", "Windows required")
    def test_explicit_list_directory_lock(self):
        self._windows_case("handle", 1, 3)

    @unittest.skipUnless(os.name == "nt", "Windows required")
    def test_metadata_only_control(self):
        self._windows_case("handle", 0, 3)

    @unittest.skipUnless(os.name == "nt", "Windows required")
    def test_share_delete_control(self):
        self._windows_case("handle", 1, 7)

    def test_existing_clean_patch_and_cleanup_contract(self):
        session = self.session()
        target = Path(session.worktree_root) / "README.md"
        saved = target.read_bytes()
        applied = self.adapter.apply_exact_replacement(
            session=session,
            proposal=PatchProposal(
                relative_path="README.md",
                expected_sha256=hashlib.sha256(saved).hexdigest(),
                new_content=saved.decode("utf-8") + "\\np0 isolated patch\\n",
                rationale="Check existing exact replacement and clean cleanup contract",
            ),
            allowed_paths=("README.md",),
        )
        self.assertNotEqual(applied.before_sha256, applied.after_sha256)
        with self.assertRaises(ToolAccessError):
            self.adapter.cleanup(session)
        target.write_bytes(saved)
        self.adapter.cleanup(session)
        self.assertFalse(Path(session.worktree_root).exists())

    def test_normal_control(self):
        session = self.session()
        target = Path(session.worktree_root)
        (target / "p0-generated-untracked.txt").write_text("generated", encoding="utf-8")
        before = self.adapter._cleanup_state(target, session)
        self.assertEqual(before["branch_sha"], self.base_sha)
        self.adapter.cleanup_disposable_generated(session)
        removal = next(x for x in self.adapter.cleanup_events if x["stage"] == "git_worktree_remove")
        self.assertEqual(removal["exit_code"], 0)
        self.assertTrue(removal["before"]["registered"] and removal["before"]["metadata_exists"])
        self.assertTrue(removal["after"]["branch_exists"])
        final = self.adapter.cleanup_events[-1]["state"]
        self.assertFalse(any(final[k] for k in ("worktree_exists", "registered", "metadata_exists", "branch_exists")))

    def test_foreign_directory_and_ownership_fail_closed(self):
        from dataclasses import replace
        session = self.session()
        foreign = self.fixture / "foreign"
        foreign.mkdir()
        for invalid in (replace(session, worktree_root=str(foreign)),
                        replace(session, repository_root=str(foreign))):
            with self.assertRaises(ToolAccessError):
                self.adapter.cleanup_disposable_generated(invalid)
            self.assertTrue(foreign.exists() and Path(session.worktree_root).exists())
            self.assertEqual(self.adapter.cleanup_events[-1]["stage"], "cleanup_stopped")
        self.adapter.cleanup_disposable_generated(session)

    def test_moved_branch_fails_before_delete(self):
        session = self.session()
        previous = self._command(self.root, "rev-parse", self.base_sha + "^").stdout.strip()
        ref = "refs/heads/" + session.branch
        self._command(self.root, "update-ref", ref, previous, self.base_sha)
        with self.assertRaises(ToolAccessError):
            self.adapter.cleanup_disposable_generated(session)
        self.assertTrue(Path(session.worktree_root).exists())
        self.assertFalse(any(x["stage"] == "git_worktree_remove" for x in self.adapter.cleanup_events))
        self._command(self.root, "update-ref", ref, self.base_sha, previous)
        self.adapter.cleanup_disposable_generated(session)

    def test_tracked_modification_fails_closed(self):
        session = self.session()
        target = Path(session.worktree_root) / "README.md"
        before = target.read_bytes()
        target.write_bytes(before + b"\np0 tracked mutation\n")
        with self.assertRaises(ToolAccessError):
            self.adapter.cleanup_disposable_generated(session)
        self.assertTrue(target.exists())
        target.write_bytes(before)
        self.adapter.cleanup_disposable_generated(session)

    @unittest.skipUnless(os.name == "nt", "Windows junction required")
    def test_reparse_point_fails_closed(self):
        session = self.session()
        target = Path(session.worktree_root)
        junction = target / "p0-junction"
        outside = self.fixture / "junction-target"
        outside.mkdir()
        # Literal, freshly owned paths; no recursive operation on the junction.
        result = subprocess.run(
            ["cmd", "/d", "/c", "mklink", "/J", str(junction), str(outside)],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        try:
            with self.assertRaises(ToolAccessError):
                self.adapter.cleanup_disposable_generated(session)
            self.assertTrue(target.exists() and outside.exists())
        finally:
            os.rmdir(junction)
        self.adapter.cleanup_disposable_generated(session)

    def test_unknown_metadata_fails_closed(self):
        import base64
        session = self.session()
        pointer = Path(session.worktree_root) / ".git"
        saved = pointer.read_bytes()
        attributes = getattr(pointer.stat(), "st_file_attributes", None)
        if os.name == "nt":
            self.assertTrue(attributes & 2, "expected test-owned hidden Git pointer")
            self.assertFalse(attributes & 1, "unexpected readonly Git pointer")
        self.observations.append(dict(
            operation="unknown_metadata_input_before_mutation", path=str(pointer),
            original_bytes_base64=base64.b64encode(saved).decode("ascii"),
            original_attributes=attributes,
        ))
        self._evidence(state="INPUT_BEFORE_MUTATION")
        mutated = False
        try:
            # Existing-file open preserves Windows Hidden and avoids CREATE_ALWAYS.
            with pointer.open("r+b") as stream:
                self.assertEqual(stream.read(), saved)
                stream.seek(0)
                mutated = True
                stream.write(b"gitdir: missing-owned-metadata\n")
                stream.truncate()
                stream.flush()
                os.fsync(stream.fileno())
            self.assertEqual(pointer.read_bytes(), b"gitdir: missing-owned-metadata\n")
            self.assertEqual(getattr(pointer.stat(), "st_file_attributes", None), attributes)
            self.observations.append(dict(operation="production_cleanup_invoked", path=str(pointer)))
            with self.assertRaises(ToolAccessError) as refusal:
                self.adapter.cleanup_disposable_generated(session)
            self.observations.append(dict(
                operation="unknown_metadata_fail_closed", exception=str(refusal.exception),
                events=list(self.adapter.cleanup_events),
            ))
            self.assertTrue(Path(session.worktree_root).exists())
            self.assertFalse(any(
                x["stage"] == "git_worktree_remove" for x in self.adapter.cleanup_events
            ))
            self.assertEqual(self.adapter.cleanup_events[-1]["stage"], "cleanup_stopped")
            self._evidence(state="EXPECTED_FAIL_CLOSED")
        finally:
            if mutated:
                with pointer.open("r+b") as stream:
                    stream.seek(0)
                    stream.write(saved)
                    stream.truncate()
                    stream.flush()
                    os.fsync(stream.fileno())
                self.assertEqual(pointer.read_bytes(), saved)
                self.assertEqual(getattr(pointer.stat(), "st_file_attributes", None), attributes)
        self.adapter.cleanup_disposable_generated(session)


    def test_post_create_metadata_failure_preserves_recovery_evidence(self):
        from engineering_ai.tools.worktree import WorktreeSession
        cases = (
            ("revparse", ToolExecutionError),
            ("unexpected", ToolAccessError),
            ("filesystem", OSError),
        )
        original_git = self.adapter._run_git
        original_resolve = Path.resolve
        for mode, exception_type in cases:
            name = "b01-" + mode
            target = self.parent / name
            branch = "engineering-ai/p0/" + name
            ref = "refs/heads/" + branch
            calls = []
            def metadata_failure(args, *, operation):
                calls.append(list(args))
                if operation == "git.worktree_metadata":
                    if mode == "revparse":
                        return subprocess.CompletedProcess(args, 128, "", "injected metadata failure")
                    if mode == "unexpected":
                        return subprocess.CompletedProcess(args, 0, str(self.root / ".git") + "\n", "")
                return original_git(args, operation=operation)
            def filesystem_failure(path, *args, **kwargs):
                if mode == "filesystem" and path == target and kwargs.get("strict"):
                    raise OSError(5, "injected post-add filesystem error", str(path))
                return original_resolve(path, *args, **kwargs)
            # Saturation must not suppress the current creation recovery record.
            if mode == "unexpected":
                while len(self.adapter._cleanup_events) < 32:
                    self.adapter._record_cleanup_event(stage="test_prior_diagnostic")
            with patch.object(self.adapter, "_run_git", side_effect=metadata_failure):
                with patch.object(Path, "resolve", new=filesystem_failure):
                    with self.assertRaises(exception_type) as caught:
                        self.adapter.create_worktree(
                            worktree_name=name, branch=branch, base_ref=self.base_sha,
                        )
            recovery = caught.exception.recovery_evidence
            self.assertEqual(recovery["outcome"], "FAIL_PRESERVED")
            self.assertFalse(recovery["automatic_cleanup"])
            self.assertFalse(recovery["session_registered"])
            self.assertEqual(recovery["base_sha"], self.base_sha)
            self.assertEqual(recovery["branch_ref"], ref)
            self.assertEqual(recovery["worktree_path"], str(target))
            self.assertEqual(recovery["git_add"]["exit_code"], 0)
            self.assertIn(recovery, self.adapter.cleanup_events)
            self.assertNotIn(str(target), self.adapter._sessions)
            self.assertNotIn(str(target), self.adapter._session_metadata)
            self.assertNotIn(str(target), self.adapter._disposable_proofs)
            self.assertFalse(any(a[:2] == ["worktree", "remove"] or a[0] in
                                 {"update-ref", "branch", "prune"} for a in calls))
            listing = self._command(self.root, "worktree", "list", "--porcelain", "-z").stdout
            self.assertIn("worktree " + target.as_posix() + "\0", listing)
            self.assertIn("branch " + ref + "\0", listing)
            self.assertTrue(target.is_dir())
            self.assertEqual(self._command(self.root, "rev-parse", "--verify", ref).stdout.strip(),
                             self.base_sha)
            metadata = Path(self._command(
                target, "rev-parse", "--absolute-git-dir",
            ).stdout.strip()).resolve(strict=True)
            self.assertEqual(metadata.parent, self.root / ".git/worktrees")
            self.assertTrue(metadata.is_dir())
            self.assertEqual((metadata / "HEAD").read_text().strip(), "ref: " + ref)
            self.assertEqual(Path((metadata / "gitdir").read_text().strip()).resolve(),
                             target / ".git")
            observed = recovery["observations"]
            self.assertTrue(observed["physical_directory"]["value"])
            self.assertEqual(observed["branch"]["value"]["exit_code"], 0)
            self.assertEqual(observed["branch_sha"]["value"]["stdout"].strip(), self.base_sha)
            self.assertIn("branch " + ref + "\0", observed["registration"]["value"]["stdout"])
            self.assertTrue(observed["metadata_pointer"]["value"]["metadata_exists"])
            self.assertEqual(observed["metadata_pointer"]["value"]["metadata_path"], str(metadata))
            if mode == "revparse":
                self.assertEqual(recovery["metadata_command"]["exit_code"], 128)
                self.assertEqual(recovery["metadata_command"]["stderr"], "injected metadata failure")
            elif mode == "unexpected":
                self.assertEqual(recovery["metadata_command"]["stdout"].strip(), str(self.root / ".git"))
            else:
                self.assertIsNone(recovery["metadata_command"])
                self.assertIn("injected post-add filesystem error", recovery["stop_reason"])
            session = WorktreeSession(str(self.root), str(target), branch, self.base_sha)
            # Evidence never registers a usable session or authorizes adapter cleanup.
            with self.assertRaises(ToolAccessError):
                self.adapter.cleanup_disposable_generated(session)
            self.assertTrue(target.exists())
            self.test_sessions.append((session, metadata))
            self.observations.append(dict(operation="post_create_failure", mode=mode,
                                          recovery=recovery, state=self._fixture_snapshot()))
            self._evidence(state="EXPECTED_FAIL_CLOSED", mode=mode, recovery=recovery)
            # Independent test-owned recovery only after exact metadata/identity,
            # clean HEAD/index, SHA and reparse checks. No production compensation.
            self.assertEqual(target.resolve(strict=True), target)
            self.assertEqual(target.parent, self.parent)
            self.adapter._reject_reparse_points(target, subtree=True)
            self.adapter._reject_reparse_points(metadata, subtree=True)
            self.assertEqual(self._command(target, "rev-parse", "HEAD").stdout.strip(), self.base_sha)
            self.assertEqual(self._command(target, "diff", "--name-only").stdout, "")
            self.assertEqual(self._command(target, "diff", "--cached", "--name-only").stdout, "")
            self.assertEqual(self._command(self.root, "rev-parse", "--verify", ref).stdout.strip(), self.base_sha)
            self._command(self.root, "worktree", "remove", "--force", str(target))
            self.assertFalse(target.exists())
            self.assertFalse(metadata.exists())
            self.assertNotIn("branch " + ref + "\0", self._command(
                self.root, "worktree", "list", "--porcelain", "-z",
            ).stdout)
            self._command(self.root, "update-ref", "-d", ref, self.base_sha)
            self.assertNotIn(ref, self._command(self.root, "for-each-ref", "--format=%(refname)").stdout)
            self.assertNotIn(str(target), self.adapter._sessions)
            self.observations.append(dict(operation="verified_post_create_recovery", mode=mode,
                                          state=self._fixture_snapshot()))

    def test_ref_execution_error_is_not_absence(self):
        session = self.session()
        original = self.adapter._run_git
        def failed_ref(args, *, operation):
            if args[:3] == ["show-ref", "--verify", "--quiet"]:
                return subprocess.CompletedProcess(args, 128, "", "synthetic Git ref error")
            return original(args, operation=operation)
        with patch.object(self.adapter, "_run_git", side_effect=failed_ref):
            with self.assertRaises(ToolExecutionError):
                self.adapter.cleanup_disposable_generated(session)
        self.assertTrue(Path(session.worktree_root).exists())
        self.assertTrue(any(x["stage"] == "ref_probe_error" and x["exit_code"] == 128
                            for x in self.adapter.cleanup_events))
        self.adapter.cleanup_disposable_generated(session)

    def test_targeted_metadata_cleanup_preserves_foreign_stale_registration(self):
        session = self.session()
        foreign = self.session("foreign")
        foreign_path = Path(foreign.worktree_root)
        backup = self.fixture / "foreign-backup"
        metadata = self.adapter._session_metadata[str(foreign_path)]
        before = {str(p.relative_to(metadata)): p.read_bytes() for p in metadata.rglob("*") if p.is_file()}
        foreign_path.rename(backup)
        original = self.adapter._run_git
        commands = []
        def permission_failure(args, *, operation):
            commands.append(args)
            if operation == "git.worktree_remove_disposable":
                return subprocess.CompletedProcess(args, 1, "", "synthetic Permission denied")
            return original(args, operation=operation)
        try:
            with patch.object(self.adapter, "_run_git", side_effect=permission_failure):
                self.adapter.cleanup_disposable_generated(session)
            self.assertFalse(any(args[:2] == ["worktree", "prune"] for args in commands))
            self.assertEqual(before, {str(p.relative_to(metadata)): p.read_bytes()
                                      for p in metadata.rglob("*") if p.is_file()})
            self.assertIn("foreign", self._command(self.root, "worktree", "list", "--porcelain").stdout)
        finally:
            backup.rename(foreign_path)
        self.adapter.cleanup_disposable_generated(foreign)

    def test_nonempty_deregistered_residue_fails_closed(self):
        session = self.session()
        target = Path(session.worktree_root)
        # Capture the pre-removal clean/base proof without creating a commit.
        state = self.adapter._cleanup_state(target, session)
        self.adapter._verify_disposable_state(target, session, state)
        self._command(self.root, "worktree", "remove", "--force", str(target))
        target.mkdir()
        residue = target / "unknown.txt"
        residue.write_text("unverified residue", encoding="utf-8")
        with self.assertRaises(ToolAccessError):
            self.adapter.cleanup_disposable_generated(session)
        self.assertTrue(residue.exists())
        residue.unlink()
        self.adapter.cleanup_disposable_generated(session)

    def test_transient_filesystem_lock_keeps_bounded_retry(self):
        session = self.session()
        original = shutil.rmtree
        calls = []
        def transient(path, *args, **kwargs):
            calls.append(path)
            if len(calls) == 1:
                raise PermissionError(13, "synthetic transient lock", str(path))
            return original(path, *args, **kwargs)
        with patch.object(self.adapter, "_remove_disposable_worktree_with_retry", return_value="synthetic"):
            with patch("engineering_ai.tools.worktree.shutil.rmtree", side_effect=transient):
                self.adapter.cleanup_disposable_generated(session)
        self.assertEqual(len(calls), 2)
        fs = [x for x in self.adapter.cleanup_events if x["stage"] == "filesystem_remove"]
        self.assertEqual(len(fs), 2)
        self.assertFalse(fs[-1]["worktree_exists"])



class Gate036CleanupContractP0Tests(unittest.TestCase):
    def test_cleanup_diagnostics_cannot_override_failed_acceptance(self):
        from scripts.gate036_real_connected_project_controlled_use import (
            _synthetic_pass_payload, evaluate_gate036_payload,
        )
        payload = _synthetic_pass_payload()
        payload["buoycalc"]["cleanup_state"] = "FAIL"
        payload["buoycalc"]["cleanup_events"] = [{"stage": "cleanup_complete"}]
        passed, errors = evaluate_gate036_payload(payload)
        self.assertFalse(passed)
        self.assertIn("BuoyCalc cleanup failed", errors)


if __name__ == "__main__":
    unittest.main()
