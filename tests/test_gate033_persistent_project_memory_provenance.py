from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Gate033PersistentProjectMemoryProvenanceTests(unittest.TestCase):
    def test_gate033_persistent_project_memory_provenance(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(
                    ROOT
                    / "scripts"
                    / "gate033_persistent_project_memory_provenance.py"
                ),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate"], "033")
        self.assertEqual(
            payload["state"],
            "PASS_V1_0_PERSISTENT_PROJECT_MEMORY_PROVENANCE",
        )
        self.assertEqual(len(payload["source_revision"]), 40)

        persistence = payload["persistence"]
        self.assertTrue(persistence["memory_database_reopened"])
        self.assertTrue(persistence["lifecycle_database_reopened"])
        self.assertTrue(persistence["loaded_source_hash_preserved"])
        self.assertTrue(persistence["initial_memory_integrity"])
        self.assertTrue(persistence["initial_lifecycle_integrity"])
        self.assertTrue(persistence["final_memory_integrity"])
        self.assertTrue(persistence["final_lifecycle_integrity"])
        self.assertEqual(persistence["source_revision"], 1)
        self.assertEqual(len(persistence["source_content_sha256"]), 64)

        retrieval = payload["retrieval"]
        self.assertEqual(retrieval["status"], "READY")
        self.assertEqual(retrieval["project_id"], "engineering-ai")
        self.assertEqual(retrieval["revision"], 1)
        self.assertEqual(len(retrieval["content_sha256"]), 64)
        self.assertTrue(retrieval["provenance"])
        self.assertTrue(retrieval["source_refs"])
        self.assertFalse(retrieval["automatic_context_injection"])

        lifecycle = payload["lifecycle"]
        self.assertEqual(
            lifecycle["source_state_before_drift"],
            "ACCEPTED_CURRENT",
        )
        self.assertEqual(
            lifecycle["source_stale_state"],
            "STALE_SOURCE_REVISION",
        )
        self.assertEqual(
            lifecycle["evidence_state_before_drift"],
            "ACCEPTED_CURRENT",
        )
        self.assertEqual(
            lifecycle["evidence_stale_state"],
            "STALE_EVIDENCE_REVISION",
        )
        self.assertEqual(lifecycle["source_history_revisions"], [1, 2, 3, 4])
        self.assertEqual(
            lifecycle["evidence_history_revisions"],
            [1, 2, 3, 4],
        )
        self.assertTrue(lifecycle["source_old_history_preserved"])
        self.assertTrue(lifecycle["evidence_old_history_preserved"])

        assertions = payload["assertions"]
        self.assertTrue(assertions["same_memory_id_project_isolation"])
        self.assertTrue(assertions["cross_project_get_rejected"])
        self.assertTrue(assertions["cross_project_retrieval_rejected"])
        self.assertTrue(assertions["cross_project_lifecycle_rejected"])
        self.assertTrue(assertions["exact_source_revision_sha_binding"])
        self.assertTrue(assertions["exact_evidence_revision_sha_binding"])
        self.assertTrue(assertions["source_revision_drift_detected"])
        self.assertTrue(assertions["evidence_revision_drift_detected"])
        self.assertTrue(assertions["model_advisory_promotion_rejected"])
        self.assertFalse(assertions["automatic_model_or_blackboard_injection"])
        self.assertEqual(
            assertions["semantic_vector_backend"],
            "DEFERRED_NOT_JUSTIFIED",
        )
        self.assertFalse(assertions["new_memory_architecture"])
        self.assertFalse(assertions["new_model_qualification"])
        self.assertFalse(assertions["new_tool_authority"])
        self.assertFalse(assertions["new_git_authority"])
        self.assertFalse(assertions["new_network_authority"])
        self.assertFalse(assertions["release_authority"])
        self.assertFalse(assertions["fabrication_authority"])

        self.assertEqual(
            payload["physical_validation"],
            "PHYSICAL_NOT_EXECUTED",
        )


if __name__ == "__main__":
    unittest.main()
