from __future__ import annotations

import hashlib
import json
import shutil
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
from engineering_ai.projects.buoycalc_controlled import _VALIDATOR_PROFILES, _VALIDATOR_SPECS
from engineering_ai.supervisor.policy import Decision, PolicyEngine
from engineering_ai.tools import PatchProposal, ToolAccessError, ToolResult
from engineering_ai.validation import validate_instance


ROOT = Path(__file__).resolve().parents[1]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class _FakeRunner:
    fail_step: str | None = None
    mutate_path: str | None = None

    def __init__(self, specs, *, root):
        self.root = Path(root)

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
            path.write_text(content, encoding="utf-8")

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

    def loop(self) -> BuoyCalcControlledEngineeringLoop:
        return BuoyCalcControlledEngineeringLoop(self.root, self.worktree_parent)

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

        proposal = PatchProposal(
            relative_path="docs/note.md",
            expected_sha256=sha256_text("before\n"),
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

        with patch(
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
            new_content="before\n",
            rationale="restore synthetic fixture",
        )
        loop.apply_patch(
            session=prep.session,
            proposal=rollback,
            allowed_paths=("docs/note.md",),
        )
        loop.cleanup(prep.session)
        self.assertEqual(self._git("rev-parse", "HEAD").strip(), self.base_sha)
        self.assertEqual(self._git("status", "--porcelain").strip(), "")

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
        with patch(
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
        with patch(
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

    def test_unknown_validator_profile_is_rejected(self) -> None:
        loop = self.loop()
        prep = loop.prepare(
            worktree_name="unknown-profile",
            branch="engineering-ai/buoycalc/unknown-profile",
        )
        assert prep.session is not None
        with self.assertRaises(ToolAccessError):
            loop.validate(session=prep.session, profiles=("arbitrary.shell",))
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
            (spec.executable, *spec.fixed_args)
            for spec in _VALIDATOR_SPECS
        )
        # tuple join above is not valid for nested tuples; use explicit string below.
        flattened = " ".join(
            " ".join((spec.executable, *spec.fixed_args))
            for spec in _VALIDATOR_SPECS
        ).casefold()
        self.assertNotIn("publish-windows.ps1", flattened)
        self.assertNotIn("package-windows-rc.ps1", flattened)
        self.assertNotIn("verify-windows-rc.ps1", flattened)
        self.assertNotIn("git tag", flattened)
        self.assertNotIn("gh release", flattened)


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


if __name__ == "__main__":
    unittest.main()
