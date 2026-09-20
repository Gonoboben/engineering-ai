from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


class Gate024CadSmokeTests(unittest.TestCase):
    def test_smoke_harness_passes(self) -> None:
        script_path = Path(__file__).resolve().parents[1] / "scripts" / "gate024_cad_smoke.py"
        spec = importlib.util.spec_from_file_location("gate024_cad_smoke", script_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not load Gate 024 CAD smoke script")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.main(), 0)


if __name__ == "__main__":
    unittest.main()
