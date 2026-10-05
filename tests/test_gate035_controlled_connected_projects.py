from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "gate035_controlled_connected_projects.py"

spec = importlib.util.spec_from_file_location("gate035_harness", SCRIPT)
assert spec is not None and spec.loader is not None
gate035 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate035)


class Gate035OpeningContractTests(unittest.TestCase):
    def test_opening_fixture_passes(self) -> None:
        result = gate035.evaluate(gate035.opening_fixture())
        self.assertTrue(result["passed"])
        self.assertEqual(result["state"], gate035.OPENING_PASS)
        self.assertEqual(result["connected_project_remote_mutations"], 0)
        self.assertFalse(result["false_pass"])

    def test_cancelled_native_cannot_be_promoted_to_ready(self) -> None:
        payload = gate035.opening_fixture()
        payload["platavm"]["native_current_head"] = "CANCELLED"
        payload["platavm"]["ready_for_review"] = True
        result = gate035.evaluate(payload)
        self.assertFalse(result["passed"])
        self.assertTrue(any("readiness promoted" in item for item in result["errors"]))

    def test_project_cross_contamination_fails(self) -> None:
        payload = gate035.opening_fixture()
        payload["control"]["project_cross_contamination"] = True
        result = gate035.evaluate(payload)
        self.assertFalse(result["passed"])

    def test_connected_project_mutation_fails(self) -> None:
        payload = gate035.opening_fixture()
        payload["control"]["connected_project_remote_mutations"] = 1
        result = gate035.evaluate(payload)
        self.assertFalse(result["passed"])

    def test_buoycalc_release_promotion_fails(self) -> None:
        payload = gate035.opening_fixture()
        payload["buoycalc"]["release_authorized"] = True
        result = gate035.evaluate(payload)
        self.assertFalse(result["passed"])

    def test_buoycalc_handoff_remains_experimental(self) -> None:
        payload = gate035.opening_fixture()
        payload["buoycalc"]["operational_handoff_authorized"] = True
        result = gate035.evaluate(payload)
        self.assertFalse(result["passed"])
        self.assertTrue(any("handoff" in item.lower() for item in result["errors"]))

    def test_script_self_test_exit_zero(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(gate035.OPENING_PASS, completed.stdout)


if __name__ == "__main__":
    unittest.main()
