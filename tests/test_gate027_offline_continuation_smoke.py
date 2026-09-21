from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Gate027OfflineContinuationSmokeTests(unittest.TestCase):
    def test_gate027_offline_continuation_smoke(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "gate027_offline_continuation_smoke.py"),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate"], "027")
        self.assertEqual(payload["state"], "PASS_OFFLINE_CONTINUATION_BOUNDARY")
        self.assertFalse(payload["external_network_exercised"])
        self.assertFalse(payload["release_authority"])
        self.assertFalse(payload["fabrication_authority"])
        self.assertEqual(
            payload["physical_validation"],
            "PHYSICAL_NOT_EXECUTED",
        )
        self.assertTrue(all(payload["assertions"].values()))


if __name__ == "__main__":
    unittest.main()
