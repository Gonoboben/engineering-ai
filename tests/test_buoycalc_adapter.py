from __future__ import annotations

import json
import shutil
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

from engineering_ai.projects import (
    BuoyCalcCIState,
    BuoyCalcReadOnlyAdapter,
    SourceBoundaryClass,
    classify_buoycalc_ci_state,
)
from engineering_ai.projects.buoycalc import (
    GOVERNANCE_REQUIRED_CHECKS,
    RELEASE_REQUIRED_CHECKS,
    RELEASE_STATE,
    REQUIRED_GOVERNANCE_FILES,
)
from engineering_ai.tools import ToolExecutionError
from engineering_ai.validation import validate_instance


ROOT = Path(__file__).resolve().parents[1]


class Gate014SmokeHarnessTests(unittest.TestCase):
    def test_missing_repository_is_structured_nonzero_state(self) -> None:
        missing = ROOT / "definitely-missing-buoycalc-checkout"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/gate014_buoycalc_readonly_smoke.py"),
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
        self.assertEqual(payload["snapshot_state"], "LOCAL_REPOSITORY_NOT_FOUND")
        self.assertEqual(payload["release_state"], "NOT_AUTHORIZED")
        self.assertEqual(payload["physical_validation"], "PHYSICAL_NOT_EXECUTED")
        self.assertEqual(result.stderr, "")


@unittest.skipIf(shutil.which("git") is None, "git executable is required")
class BuoyCalcReadOnlyAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.origin_tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.origin = Path(self.origin_tmp.name) / "origin.git"

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
            "Calculation/MooringCalculator.cs": "namespace Fixture;\n",
            "Services/MooringShapeSolver.cs": "namespace Fixture;\n",
            "ReadModels/SelectedShapeReadModel.cs": "namespace Fixture;\n",
            "Views/MainWindow.axaml.cs": "namespace Fixture;\n",
            "Reports/UserEngineeringReport.cs": "namespace Fixture;\n",
            "tools/check-repository-governance.ps1": "Write-Host PASS\n",
            "Validation601/Program.cs": "namespace Fixture;\n",
            "BuoyCalc.Windows.csproj": "<Project />\n",
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

    def tearDown(self) -> None:
        self.tmp.cleanup()
        self.origin_tmp.cleanup()

    def adapter(self, **kwargs) -> BuoyCalcReadOnlyAdapter:
        return BuoyCalcReadOnlyAdapter(self.root, **kwargs)

    def test_snapshot_resolves_governance_git_and_invariants(self) -> None:
        snapshot = self.adapter().snapshot()
        self.assertEqual(
            tuple(doc.path for doc in snapshot.governance_documents),
            REQUIRED_GOVERNANCE_FILES,
        )
        self.assertEqual(snapshot.git.branch, "main")
        self.assertEqual(snapshot.git.head_sha, snapshot.git.origin_main_sha)
        self.assertFalse(snapshot.git.dirty)
        self.assertEqual(snapshot.invariant_violations, ())
        self.assertTrue(all(check.passed for check in snapshot.invariant_checks))
        self.assertEqual(snapshot.release_state, RELEASE_STATE)
        self.assertEqual(snapshot.physical_validation, "PHYSICAL_NOT_EXECUTED")
        self.assertEqual(
            snapshot.governance_required_checks,
            GOVERNANCE_REQUIRED_CHECKS,
        )
        self.assertEqual(
            snapshot.release_required_checks,
            RELEASE_REQUIRED_CHECKS,
        )

    def test_missing_mandatory_governance_is_hard_error(self) -> None:
        (self.root / "AGENTS.md").unlink()
        with self.assertRaises(ToolExecutionError):
            self.adapter().governance_documents()

    def test_invariant_drift_is_explicit_non_pass_state(self) -> None:
        release = self.root / "RELEASE.md"
        release.write_text(
            release.read_text(encoding="utf-8").replace(
                "signed feedback budget = 64",
                "signed feedback budget = CHANGED",
            ),
            encoding="utf-8",
        )
        snapshot = self.adapter().snapshot()
        self.assertIn("signed-feedback-budget-64", snapshot.invariant_violations)
        self.assertFalse(
            next(
                item
                for item in snapshot.invariant_checks
                if item.invariant_id == "signed-feedback-budget-64"
            ).passed
        )

    def test_source_boundary_classification_preserves_physics_authority(self) -> None:
        snapshot = self.adapter().snapshot()
        by_path = {item.path: item.boundary_class for item in snapshot.source_inventory}
        self.assertEqual(
            by_path["Calculation/MooringCalculator.cs"],
            SourceBoundaryClass.CALCULATION_CORE_CANDIDATE,
        )
        self.assertEqual(
            by_path["Services/MooringShapeSolver.cs"],
            SourceBoundaryClass.CALCULATION_CORE_CANDIDATE,
        )
        self.assertEqual(
            by_path["ReadModels/SelectedShapeReadModel.cs"],
            SourceBoundaryClass.READ_MODEL_CONSUMER,
        )
        self.assertEqual(
            by_path["Views/MainWindow.axaml.cs"],
            SourceBoundaryClass.PRESENTATION_CONSUMER,
        )
        self.assertEqual(
            by_path["Reports/UserEngineeringReport.cs"],
            SourceBoundaryClass.PRESENTATION_CONSUMER,
        )
        self.assertNotEqual(
            by_path["Views/MainWindow.axaml.cs"],
            SourceBoundaryClass.CALCULATION_CORE_CANDIDATE,
        )
        self.assertNotEqual(
            by_path["Reports/UserEngineeringReport.cs"],
            SourceBoundaryClass.CALCULATION_CORE_CANDIDATE,
        )
        self.assertEqual(
            by_path["Validation601/Program.cs"],
            SourceBoundaryClass.VALIDATION_OR_TOOLING,
        )

    def test_inventory_is_bounded_by_tracked_file_count(self) -> None:
        with self.assertRaises(ToolExecutionError):
            self.adapter(max_scan_entries=2).source_inventory()

    def test_ci_state_preserves_non_pass_states(self) -> None:
        self.assertEqual(
            classify_buoycalc_ci_state("success", status="completed"),
            BuoyCalcCIState.PASS,
        )
        self.assertEqual(
            classify_buoycalc_ci_state("failure", status="completed"),
            BuoyCalcCIState.FAIL,
        )
        self.assertEqual(
            classify_buoycalc_ci_state("cancelled", status="completed"),
            BuoyCalcCIState.CANCELLED,
        )
        self.assertEqual(
            classify_buoycalc_ci_state(None, status="queued"),
            BuoyCalcCIState.PENDING,
        )
        self.assertEqual(
            classify_buoycalc_ci_state(None, present=False),
            BuoyCalcCIState.MISSING,
        )
        self.assertEqual(
            classify_buoycalc_ci_state(None, status="completed"),
            BuoyCalcCIState.UNKNOWN,
        )
        for state in (
            BuoyCalcCIState.FAIL,
            BuoyCalcCIState.CANCELLED,
            BuoyCalcCIState.PENDING,
            BuoyCalcCIState.MISSING,
            BuoyCalcCIState.UNKNOWN,
        ):
            self.assertNotEqual(state, BuoyCalcCIState.PASS)

    def test_adapter_exposes_no_write_release_or_execution_api(self) -> None:
        adapter = self.adapter()
        for name in (
            "write",
            "write_text",
            "delete",
            "commit",
            "push",
            "open_pr",
            "merge_pr",
            "run_validator",
            "run_calculation",
            "package_release",
            "authorize_release",
            "create_tag",
        ):
            self.assertFalse(hasattr(adapter, name))


class Gate014ProfilePolicyTests(unittest.TestCase):
    def test_committed_profile_and_policy_validate(self) -> None:
        profile = json.loads(
            (ROOT / "profiles/buoycalc-readonly.json").read_text(encoding="utf-8")
        )
        policy = json.loads(
            (ROOT / "profiles/buoycalc-readonly-policy.json").read_text(
                encoding="utf-8"
            )
        )
        validate_instance("project-profile.schema.json", profile)
        validate_instance("project-policy.schema.json", policy)
        self.assertEqual(profile["architecture_baseline"], "BuoyCalc v1.0.0 frozen engineering baseline")
        self.assertEqual(policy["autonomous_actions"], ["read_repository"])
        for action in (
            "run_calculation",
            "run_validator",
            "write_worktree",
            "local_commit",
            "push_remote",
            "open_pr",
            "merge_pr",
            "release_authorization",
            "physics_change",
            "validator_weakening",
        ):
            self.assertIn(action, policy["forbidden_actions"])
        self.assertEqual(
            tuple(policy["mandatory_validators"]),
            RELEASE_REQUIRED_CHECKS,
        )


if __name__ == "__main__":
    unittest.main()
