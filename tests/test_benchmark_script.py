from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


class BenchmarkScriptOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        script_path = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_local_model.py"
        spec = importlib.util.spec_from_file_location("gate005_benchmark_script", script_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not load Gate 005 benchmark script")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls._module = module

    def test_render_payload_is_ascii_safe_and_round_trips_unicode(self) -> None:
        payload = {"symbol": "Ω", "text": "напряжение"}
        rendered = self._module._render_payload(payload)

        self.assertTrue(rendered.isascii())
        self.assertEqual(json.loads(rendered), payload)


if __name__ == "__main__":
    unittest.main()
