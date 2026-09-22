from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Gate031MeasuredReplaceableRoutingTests(unittest.TestCase):
    def test_gate031_measured_replaceable_routing(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "gate031_measured_replaceable_routing.py"),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate"], "031")
        self.assertEqual(
            payload["state"],
            "PASS_V1_0_MEASURED_REPLACEABLE_MULTI_MODEL_ROUTING",
        )
        self.assertEqual(payload["routes"]["GENERAL_PLANNING"], "qwen3.5:9b")
        self.assertEqual(
            payload["routes"]["CODE_REPOSITORY"],
            "qwen2.5-coder:7b-instruct",
        )
        self.assertEqual(payload["routes"]["BASELINE_REASONING"], "gpt-oss:20b")
        self.assertEqual(
            payload["routes"]["CODE_REPOSITORY_NATIVE_TOOL_REQUIRED"],
            "NO_ROUTE",
        )
        self.assertEqual(payload["routes"]["OVER_MEASURED_CONTEXT"], "NO_ROUTE")
        self.assertEqual(payload["routes"]["OVER_MEASURED_OUTPUT"], "NO_ROUTE")
        self.assertEqual(payload["routes"]["VISION_UNMEASURED"], "NO_ROUTE")
        self.assertEqual(payload["routes"]["IMAGE_GENERATION_UNMEASURED"], "NO_ROUTE")
        assertions = payload["assertions"]
        self.assertTrue(assertions["measured_evidence_required"])
        self.assertTrue(assertions["route_provenance_preserved"])
        self.assertTrue(assertions["registry_boundary_replaceable"])
        self.assertTrue(assertions["supervisor_router_architecture_unchanged"])
        self.assertFalse(assertions["router_executes_models"])
        self.assertFalse(assertions["router_executes_tools"])
        self.assertFalse(assertions["unmeasured_capability_auto_promoted"])
        self.assertFalse(assertions["practical_runtime_replacement_claimed"])
        self.assertFalse(assertions["remote_git_mutation_authority"])
        self.assertFalse(assertions["release_authority"])
        self.assertFalse(assertions["fabrication_authority"])
        self.assertEqual(
            payload["physical_validation"],
            "PHYSICAL_NOT_EXECUTED",
        )


if __name__ == "__main__":
    unittest.main()
