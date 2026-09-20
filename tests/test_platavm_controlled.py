from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from engineering_ai.projects import (
    ControlledLoopState,
    PlataVMControlledEngineeringLoop,
)
from engineering_ai.supervisor.policy import Decision, PolicyEngine
from engineering_ai.tools import PatchProposal, ToolAccessError
from engineering_ai.validation import validate_instance


ROOT = Path(__file__).resolve().parents[1]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@unittest.skipIf(shutil.which("git") is None, "git executable is required")
class PlataVMControlledLoopTests(unittest.TestCase):
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
        self._write_fixture_files(semantic_pass=True)
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
        self.repo_tmp.cleanup()
        self.origin_tmp.cleanup()
        self.worktree_tmp.cleanup()

    def _write_fixture_files(self, *, semantic_pass: bool) -> None:
        docs = {
            "AGENTS.md": "# fixture governance\n",
            "Docs/PROJECT_STATUS.md": "# fixture status without stale pointers\n",
            "Docs/PROJECT_CONTROL.md": "# control\n",
            "Docs/PROJECT_MASTER.md": "# master\n",
            "Docs/ARCHITECTURE_BASELINE.md": "# V1.9\n",
            "Docs/OPEN_QUESTIONS.md": "# questions\n",
            "Docs/TRACEABILITY_V1_9.md": "# traceability\n",
            "Docs/CHRONOLOGY.md": "# chronology\n",
            "Docs/chronology/2026-09-19-fixture.md": "fixture\n",
            "Docs/safe.txt": "before\n",
            "Hardware/KiCad/PlataVM.kicad_pro": "(project)\n",
            "Hardware/KiCad/PlataVM.kicad_sch": "(schematic)\n",
            "Tools/repository_integrity.py": "print('Repository integrity: PASS')\n",
            "Tools/run_all_gates.py": (
                "print('All registered semantic Gates: PASS')\n"
                if semantic_pass
                else "raise SystemExit(7)\n"
            ),
        }
        for relative, content in docs.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode("utf-8"))

    def _git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def loop(self) -> PlataVMControlledEngineeringLoop:
        return PlataVMControlledEngineeringLoop(
            self.root,
            self.worktree_parent,
            python_executable=sys.executable,
        )

    def prepare(self):
        return self.loop().prepare(
            worktree_name="gate013-test",
            branch="engineering-ai/gate013-test",
            base_ref="HEAD",
        )

    def test_controlled_patch_validate_restore_and_cleanup(self) -> None:
        loop = self.loop()
        primary_before = (self.root / "Docs/safe.txt").read_text(encoding="utf-8")
        prep = loop.prepare(
            worktree_name="gate013-pass",
            branch="engineering-ai/gate013-pass",
            base_ref="HEAD",
        )
        self.assertEqual(prep.state, ControlledLoopState.WORKTREE_READY)
        self.assertEqual(prep.source_conflicts, ())
        assert prep.session is not None

        worktree_target = Path(prep.session.worktree_root) / "Docs" / "safe.txt"
        original_worktree_content = worktree_target.read_bytes().decode("utf-8")
        proposal = PatchProposal(
            relative_path="Docs/safe.txt",
            expected_sha256=hashlib.sha256(worktree_target.read_bytes()).hexdigest(),
            new_content="after\n",
            rationale="bounded synthetic Gate 013 fixture change",
        )
        applied = loop.apply_patch(
            session=prep.session,
            proposal=proposal,
            allowed_paths=("Docs/safe.txt",),
        )
        self.assertEqual(applied.state, ControlledLoopState.PATCH_APPLIED)
        self.assertIn("+after", applied.application.diff)
        self.assertEqual(
            (self.root / "Docs/safe.txt").read_text(encoding="utf-8"),
            primary_before,
        )

        validated = loop.validate(session=prep.session)
        self.assertEqual(
            validated.state, ControlledLoopState.READY_FOR_HUMAN_APPROVAL
        )
        self.assertTrue(all(item.state.value == "PASS" for item in validated.validators))

        rollback = PatchProposal(
            relative_path="Docs/safe.txt",
            expected_sha256=applied.application.after_sha256,
            new_content=original_worktree_content,
            rationale="restore exact synthetic fixture bytes before controlled cleanup",
        )
        loop.apply_patch(
            session=prep.session,
            proposal=rollback,
            allowed_paths=("Docs/safe.txt",),
        )
        loop.cleanup(prep.session)
        self.assertFalse(Path(prep.session.worktree_root).exists())
        branch = subprocess.run(
            ["git", "show-ref", "--verify", "refs/heads/engineering-ai/gate013-pass"],
            cwd=self.root,
            check=False,
            capture_output=True,
        )
        self.assertNotEqual(branch.returncode, 0)
        self.assertEqual(self._git("rev-parse", "HEAD").strip(), self.base_sha)
        self.assertEqual(self._git("status", "--porcelain").strip(), "")

    def test_wrong_branch_prefix_is_rejected(self) -> None:
        with self.assertRaises(ToolAccessError):
            self.loop().prepare(
                worktree_name="bad-prefix",
                branch="agent/not-controlled",
                base_ref="HEAD",
            )

    def test_dirty_primary_repository_blocks_worktree_creation(self) -> None:
        (self.root / "Docs/safe.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaises(ToolAccessError):
            self.loop().prepare(
                worktree_name="dirty-base",
                branch="engineering-ai/dirty-base",
                base_ref="HEAD",
            )

    def test_stale_sha_rejects_patch_before_mutation(self) -> None:
        loop = self.loop()
        prep = loop.prepare(
            worktree_name="stale-sha",
            branch="engineering-ai/stale-sha",
        )
        assert prep.session is not None
        target = Path(prep.session.worktree_root) / "Docs/safe.txt"
        with self.assertRaises(ToolAccessError):
            loop.apply_patch(
                session=prep.session,
                proposal=PatchProposal(
                    relative_path="Docs/safe.txt",
                    expected_sha256="0" * 64,
                    new_content="must-not-write\n",
                    rationale="stale proposal test",
                ),
                allowed_paths=("Docs/safe.txt",),
            )
        self.assertEqual(target.read_text(encoding="utf-8"), "before\n")
        loop.cleanup(prep.session)

    def test_disallowed_and_escape_paths_are_rejected(self) -> None:
        loop = self.loop()
        prep = loop.prepare(
            worktree_name="path-guard",
            branch="engineering-ai/path-guard",
        )
        assert prep.session is not None

        with self.assertRaises(ToolAccessError):
            loop.apply_patch(
                session=prep.session,
                proposal=PatchProposal(
                    relative_path="Docs/PROJECT_STATUS.md",
                    expected_sha256=sha256_text("# fixture status without stale pointers\n"),
                    new_content="forbidden\n",
                    rationale="allow-list test",
                ),
                allowed_paths=("Docs/safe.txt",),
            )

        with self.assertRaises(ToolAccessError):
            loop.apply_patch(
                session=prep.session,
                proposal=PatchProposal(
                    relative_path="../escape.txt",
                    expected_sha256="0" * 64,
                    new_content="escape\n",
                    rationale="path escape test",
                ),
                allowed_paths=("../escape.txt",),
            )
        loop.cleanup(prep.session)

    def test_validator_failure_blocks_ready_state(self) -> None:
        (self.root / "Tools/run_all_gates.py").write_text(
            "raise SystemExit(7)\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "Tools/run_all_gates.py"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "failing semantic validator"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )

        loop = self.loop()
        prep = loop.prepare(
            worktree_name="validator-fail",
            branch="engineering-ai/validator-fail",
        )
        assert prep.session is not None
        validated = loop.validate(session=prep.session)
        self.assertEqual(validated.state, ControlledLoopState.VALIDATION_FAILED)
        self.assertTrue(any(item.state.value == "FAIL" for item in validated.validators))
        loop.cleanup(prep.session)

    def test_source_conflict_blocks_before_worktree_creation(self) -> None:
        status = self.root / "Docs/PROJECT_STATUS.md"
        status.write_text(
            "# status\n\n"
            "| Поле | Значение |\n"
            "|---|---|\n"
            "| Подтверждённый base main | `0000000000000000000000000000000000000000` |\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "Docs/PROJECT_STATUS.md"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "stale governance fixture"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )

        loop = self.loop()
        prep = loop.prepare(
            worktree_name="must-not-exist",
            branch="engineering-ai/must-not-exist",
        )
        self.assertEqual(prep.state, ControlledLoopState.BLOCKED_SOURCE_CONFLICT)
        self.assertIsNone(prep.session)
        self.assertTrue(prep.source_conflicts)
        self.assertFalse((self.worktree_parent / "must-not-exist").exists())

    def test_no_commit_push_pr_merge_api(self) -> None:
        loop = self.loop()
        loop.assert_no_remote_mutation_api()
        for name in ("commit", "push", "open_pr", "merge_pr"):
            self.assertFalse(hasattr(loop, name))


class Gate013PolicyTests(unittest.TestCase):
    def test_controlled_profile_policy_validate_and_enforce_write_approval(self) -> None:
        policy = json.loads(
            (ROOT / "profiles/platavm-controlled-policy.json").read_text(
                encoding="utf-8"
            )
        )
        profile = json.loads(
            (ROOT / "profiles/platavm-controlled.json").read_text(encoding="utf-8")
        )
        validate_instance("project-policy.schema.json", policy)
        validate_instance("project-profile.schema.json", profile)

        state = {
            "schema_version": "1.0",
            "state_revision": 1,
            "project_id": "platavm",
            "current_gate": "013",
            "active_job_id": None,
            "repository_ref": {
                "branch": "main",
                "head_sha": "0123456789abcdef0123456789abcdef01234567",
            },
            "architecture_baseline": "V1.9",
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
        self.assertEqual(engine.evaluate("propose_patch").decision, Decision.ALLOW)
        self.assertEqual(
            engine.evaluate("write_worktree").decision,
            Decision.NEEDS_HUMAN_APPROVAL,
        )
        approved = engine.evaluate(
            "write_worktree",
            approval_obtained=True,
            approver="human-owner",
        )
        self.assertEqual(approved.decision, Decision.ALLOW)
        for action in ("local_commit", "push_remote", "open_pr", "merge_pr"):
            self.assertEqual(engine.evaluate(action).decision, Decision.DENY)


if __name__ == "__main__":
    unittest.main()
