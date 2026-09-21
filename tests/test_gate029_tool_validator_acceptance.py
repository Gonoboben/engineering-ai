from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Gate029ToolValidatorAcceptanceTests(unittest.TestCase):
    def test_gate029_tool_validator_acceptance(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "gate029_tool_validator_acceptance.py"),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate"], "029")
        self.assertEqual(
            payload["state"],
            "PASS_V1_0_DETERMINISTIC_TOOL_VALIDATOR_INTEGRATION",
        )
        assertions = payload["assertions"]
        self.assertTrue(assertions["filesystem_root_bounded"])
        self.assertTrue(assertions["git_read_only_surface"])
        self.assertFalse(assertions["generic_git_command_surface"])
        self.assertTrue(assertions["process_fixed_allow_list"])
        self.assertTrue(assertions["process_shell_false_preserved"])
        self.assertTrue(assertions["process_timeout_bounded"])
        self.assertTrue(assertions["process_output_bounded"])
        self.assertTrue(assertions["offline_network_capable_pre_subprocess_block"])
        self.assertTrue(assertions["platavm_validator_failure_blocks_ready"])
        self.assertTrue(assertions["buoycalc_validator_failure_blocks_ready"])
        self.assertTrue(assertions["buoycalc_tracked_mutation_blocks_ready"])
        self.assertFalse(assertions["remote_git_mutation_authority"])
        self.assertFalse(assertions["generic_filesystem_write_authority"])
        self.assertFalse(assertions["release_authority"])
        self.assertFalse(assertions["fabrication_authority"])
        self.assertEqual(
            payload["physical_validation"],
            "PHYSICAL_NOT_EXECUTED",
        )


if __name__ == "__main__":
    unittest.main()
