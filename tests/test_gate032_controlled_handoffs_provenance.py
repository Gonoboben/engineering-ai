from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Gate032ControlledHandoffsProvenanceTests(unittest.TestCase):
    def test_gate032_controlled_handoffs_provenance(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "gate032_controlled_handoffs_provenance.py"),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate"], "032")
        self.assertEqual(
            payload["state"],
            "PASS_V1_0_CONTROLLED_HANDOFFS_PROVENANCE",
        )
        provenance = payload["provenance"]
        self.assertTrue(provenance["task_id"])
        self.assertEqual(provenance["originating_role"], "GENERAL_PLANNING")
        self.assertEqual(provenance["originating_model"], "qwen3.5:9b")
        self.assertEqual(provenance["originating_provider"], "ollama")
        self.assertEqual(provenance["target_role"], "CODE_REPOSITORY")
        self.assertEqual(
            provenance["target_model"],
            "qwen2.5-coder:7b-instruct",
        )
        self.assertEqual(provenance["target_provider"], "ollama")
        self.assertTrue(provenance["visible_record_ids"])
        self.assertTrue(provenance["visible_evidence_refs"])
        self.assertTrue(provenance["source_version_refs"])
        self.assertTrue(provenance["route_evidence_refs"])

        assertions = payload["assertions"]
        self.assertTrue(assertions["supervisor_mediation"])
        self.assertFalse(assertions["direct_peer_to_peer_authority"])
        self.assertTrue(assertions["task_identity_preserved"])
        self.assertTrue(assertions["originating_role_model_provider_preserved"])
        self.assertTrue(assertions["target_role_model_provider_preserved"])
        self.assertTrue(assertions["visible_context_ids_preserved"])
        self.assertTrue(assertions["deterministic_evidence_refs_preserved"])
        self.assertTrue(assertions["source_version_identity_preserved"])
        self.assertTrue(assertions["hidden_context_rejected"])
        self.assertTrue(assertions["cross_task_context_rejected"])
        self.assertTrue(assertions["missing_required_context_fails_closed"])
        self.assertFalse(assertions["coder_native_tool_route_without_qualification"])
        self.assertTrue(assertions["reviewer_independence_preserved"])
        self.assertFalse(assertions["model_agreement_is_evidence"])
        self.assertFalse(assertions["new_model_qualification"])
        self.assertFalse(assertions["new_tool_authority"])
        self.assertFalse(assertions["new_git_authority"])
        self.assertFalse(assertions["new_network_authority"])
        self.assertFalse(assertions["release_authority"])
        self.assertFalse(assertions["fabrication_authority"])
        self.assertEqual(payload["physical_validation"], "PHYSICAL_NOT_EXECUTED")


if __name__ == "__main__":
    unittest.main()
