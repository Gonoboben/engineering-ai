from __future__ import annotations

import copy
import unittest

from scripts.gate036_real_connected_project_controlled_use import (
    BUOYCALC_EXPECTED_HEAD,
    PLATAVM_EXPECTED_HEAD,
    _synthetic_pass_payload,
    evaluate_gate036_payload,
)


class Gate036RealConnectedProjectControlledUseTests(unittest.TestCase):
    def test_platavm_expected_head_tracks_remediated_pr100(self) -> None:
        self.assertEqual(
            PLATAVM_EXPECTED_HEAD,
            "840435615d0b3ebf5f1137f575cfd75b66501964",
        )

    def test_complete_real_evidence_passes(self) -> None:
        payload = _synthetic_pass_payload()
        passed, errors = evaluate_gate036_payload(payload)
        self.assertTrue(passed)
        self.assertEqual(errors, ())

    def test_synthetic_or_non_real_execution_cannot_pass(self) -> None:
        payload = _synthetic_pass_payload()
        payload["real_execution"] = False
        passed, errors = evaluate_gate036_payload(payload)
        self.assertFalse(passed)
        self.assertIn("real execution missing", errors)

    def test_platavm_wrong_exact_head_blocks(self) -> None:
        payload = _synthetic_pass_payload()
        payload["platavm"]["before"]["head_sha"] = "0" * 40
        passed, errors = evaluate_gate036_payload(payload)
        self.assertFalse(passed)
        self.assertIn("PlataVM exact head mismatch", errors)
        self.assertNotEqual(payload["platavm"]["before"]["head_sha"], PLATAVM_EXPECTED_HEAD)

    def test_platavm_source_conflict_blocks(self) -> None:
        payload = _synthetic_pass_payload()
        payload["platavm"]["source_conflicts"] = ["stale PROJECT_STATUS"]
        passed, errors = evaluate_gate036_payload(payload)
        self.assertFalse(passed)
        self.assertIn("PlataVM source conflict remains", errors)

    def test_platavm_validator_missing_blocks(self) -> None:
        payload = _synthetic_pass_payload()
        payload["platavm"]["validators"] = payload["platavm"]["validators"][:1]
        passed, errors = evaluate_gate036_payload(payload)
        self.assertFalse(passed)
        self.assertIn("PlataVM validator set mismatch", errors)

    def test_platavm_cleanup_or_authority_promotion_blocks(self) -> None:
        payload = _synthetic_pass_payload()
        payload["platavm"]["cleanup_state"] = "FAIL"
        payload["platavm"]["authority_markers"]["fabrication_not_granted"] = False
        passed, errors = evaluate_gate036_payload(payload)
        self.assertFalse(passed)
        self.assertIn("PlataVM cleanup failed", errors)
        self.assertIn("PlataVM fabrication barrier not proven", errors)

    def test_buoycalc_requires_exact_clean_main(self) -> None:
        payload = _synthetic_pass_payload()
        payload["buoycalc"]["before"]["head_sha"] = "1" * 40
        passed, errors = evaluate_gate036_payload(payload)
        self.assertFalse(passed)
        self.assertIn("BuoyCalc exact head mismatch", errors)
        self.assertNotEqual(payload["buoycalc"]["before"]["head_sha"], BUOYCALC_EXPECTED_HEAD)

    def test_buoycalc_runtime_or_profile_failure_blocks(self) -> None:
        payload = _synthetic_pass_payload()
        payload["buoycalc"]["runtime"]["blockers"] = [".NET 8 SDK not found"]
        payload["buoycalc"]["profiles"][0]["passed"] = False
        passed, errors = evaluate_gate036_payload(payload)
        self.assertFalse(passed)
        self.assertIn("BuoyCalc runtime prerequisite blocked", errors)
        self.assertIn("BuoyCalc profile PASS closure missing", errors)

    def test_buoycalc_release_or_physical_promotion_blocks(self) -> None:
        payload = _synthetic_pass_payload()
        payload["buoycalc"]["release_state"] = "AUTHORIZED"
        payload["buoycalc"]["physical_validation"] = "PASS"
        passed, errors = evaluate_gate036_payload(payload)
        self.assertFalse(passed)
        self.assertIn("BuoyCalc release authority was promoted", errors)
        self.assertIn("BuoyCalc physical state was promoted", errors)

    def test_primary_repository_drift_blocks(self) -> None:
        payload = _synthetic_pass_payload()
        payload["platavm"]["after"] = copy.deepcopy(payload["platavm"]["after"])
        payload["platavm"]["after"]["status_sha256"] = "f" * 64
        payload["buoycalc"]["repository_unchanged"] = False
        passed, errors = evaluate_gate036_payload(payload)
        self.assertFalse(passed)
        self.assertIn("PlataVM primary repository changed", errors)
        self.assertIn("BuoyCalc primary repository changed", errors)

    def test_remote_mutation_attempt_blocks(self) -> None:
        payload = _synthetic_pass_payload()
        payload["remote_connected_project_mutation_attempted"] = True
        passed, errors = evaluate_gate036_payload(payload)
        self.assertFalse(passed)
        self.assertIn("remote connected-project mutation must remain false", errors)


if __name__ == "__main__":
    unittest.main()
