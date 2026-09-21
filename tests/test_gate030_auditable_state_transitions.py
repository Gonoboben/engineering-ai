from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Gate030AuditableStateTransitionsTests(unittest.TestCase):
    def test_gate030_auditable_state_transitions(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "gate030_auditable_state_transitions.py"),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate"], "030")
        self.assertEqual(
            payload["state"],
            "PASS_V1_0_AUDITABLE_STATE_TRANSITIONS",
        )
        assertions = payload["assertions"]
        self.assertTrue(assertions["supervisor_transitions_audited"])
        self.assertTrue(assertions["approval_blocked_transition_does_not_advance"])
        self.assertTrue(assertions["forbidden_transition_does_not_advance"])
        self.assertTrue(assertions["memory_history_append_only"])
        self.assertTrue(assertions["knowledge_source_drift_detected"])
        self.assertTrue(assertions["knowledge_stale_acceptance_invalidated"])
        self.assertTrue(assertions["job_queue_reopen_integrity"])
        self.assertTrue(assertions["waiting_for_approval_persists"])
        self.assertTrue(assertions["interrupted_run_recovers_fail_closed"])
        self.assertTrue(assertions["scheduled_run_reopen_integrity"])
        self.assertTrue(assertions["external_review_ledger_reopen_integrity"])
        self.assertTrue(assertions["controlled_tool_ledger_reopen_integrity"])
        self.assertFalse(assertions["automatic_approval"])
        self.assertFalse(assertions["history_rewrite_authority"])
        self.assertFalse(assertions["remote_git_mutation_authority"])
        self.assertFalse(assertions["release_authority"])
        self.assertFalse(assertions["fabrication_authority"])
        self.assertEqual(
            payload["physical_validation"],
            "PHYSICAL_NOT_EXECUTED",
        )


if __name__ == "__main__":
    unittest.main()
