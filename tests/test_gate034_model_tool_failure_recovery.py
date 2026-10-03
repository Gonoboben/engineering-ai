from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Gate034ModelToolFailureRecoveryTests(unittest.TestCase):
    def test_gate034_model_tool_failure_recovery(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(
                    ROOT
                    / "scripts"
                    / "gate034_model_tool_failure_recovery.py"
                ),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate"], "034")
        self.assertEqual(
            payload["state"],
            "PASS_V1_0_DOCUMENTED_MODEL_TOOL_FAILURE_RECOVERY",
        )
        self.assertEqual(len(payload["source_revision"]), 40)

        model = payload["model_recovery"]
        self.assertEqual(model["unavailable_first_state"], "QUEUED")
        self.assertEqual(model["unavailable_attempts"], 1)
        self.assertTrue(model["failed_model_audit_recorded"])
        self.assertEqual(model["persisted_reopen_state"], "QUEUED")
        self.assertEqual(model["persisted_reopen_attempts"], 1)
        self.assertEqual(model["recovered_state"], "PASS")
        self.assertEqual(model["recovered_attempts"], 1)
        self.assertEqual(model["retry_exhausted_state"], "FAIL")
        self.assertTrue(model["queue_integrity"])

        tool = payload["tool_recovery"]
        self.assertEqual(tool["first_state"], "QUEUED")
        self.assertEqual(tool["first_attempts"], 1)
        self.assertEqual(tool["recovered_state"], "PASS")
        self.assertEqual(tool["recovered_attempts"], 1)
        self.assertEqual(tool["retry_exhausted_state"], "FAIL")
        self.assertTrue(tool["supervisor_owned_retry_classification"])

        protocol = payload["protocol_recovery"]
        self.assertTrue(protocol["bounded_correction_recovered"])
        self.assertEqual(protocol["retry_exhausted_state"], "FAIL")

        process = payload["process_recovery"]
        self.assertTrue(process["timeout_structured"])
        self.assertFalse(process["timeout_ok"])
        self.assertTrue(process["offline_network_blocked_before_execution"])

        queue = payload["queue_recovery"]
        self.assertEqual(queue["interrupted_state"], "BLOCKED")
        self.assertEqual(queue["interrupted_event"], "INTERRUPTED_RECOVERY")
        self.assertEqual(queue["late_pass_state"], "BLOCKED")
        self.assertEqual(queue["late_pass_event"], "TIMEOUT_RECOVERY")
        self.assertTrue(queue["integrity"])

        boundaries = payload["authority_boundaries"]
        self.assertEqual(boundaries["policy_denial_state"], "BLOCKED")
        self.assertEqual(boundaries["policy_denial_attempts"], 0)
        self.assertFalse(boundaries["policy_denial_tool_called"])
        self.assertTrue(boundaries["approval_survived_reopen"])
        self.assertFalse(boundaries["automatic_approval"])
        self.assertFalse(boundaries["false_pass"])
        self.assertFalse(boundaries["new_architecture_authority"])
        self.assertFalse(boundaries["new_model_authority"])
        self.assertFalse(boundaries["new_tool_authority"])
        self.assertFalse(boundaries["new_git_authority"])
        self.assertFalse(boundaries["new_network_authority"])
        self.assertFalse(boundaries["release_authority"])
        self.assertFalse(boundaries["fabrication_authority"])

        self.assertEqual(
            payload["physical_validation"],
            "PHYSICAL_NOT_EXECUTED",
        )


if __name__ == "__main__":
    unittest.main()
