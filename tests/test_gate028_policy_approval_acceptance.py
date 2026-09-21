from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Gate028PolicyApprovalAcceptanceTests(unittest.TestCase):
    def test_gate028_policy_approval_acceptance(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "gate028_policy_approval_acceptance.py"),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate"], "028")
        self.assertEqual(
            payload["state"],
            "PASS_V1_0_POLICY_APPROVAL_ENFORCEMENT",
        )
        assertions = payload["assertions"]
        self.assertTrue(assertions["deny_is_fail_closed"])
        self.assertTrue(assertions["approval_required_executes_zero_before_approval"])
        self.assertTrue(assertions["approval_without_identity_is_non_authorizing"])
        self.assertTrue(assertions["named_approval_is_bounded"])
        self.assertTrue(assertions["persisted_waiting_for_approval_survives_reopen"])
        self.assertTrue(assertions["external_provider_not_called_before_approval"])
        self.assertTrue(assertions["tool_handler_not_called_before_approval"])
        self.assertTrue(assertions["forbidden_tool_handler_not_called"])
        self.assertFalse(assertions["automatic_approval"])
        self.assertFalse(assertions["remote_git_mutation_authority"])
        self.assertFalse(assertions["release_authority"])
        self.assertFalse(assertions["fabrication_authority"])
        self.assertEqual(
            payload["physical_validation"],
            "PHYSICAL_NOT_EXECUTED",
        )


if __name__ == "__main__":
    unittest.main()
