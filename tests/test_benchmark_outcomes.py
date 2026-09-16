from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

from engineering_ai.models import (
    BenchmarkCase,
    ModelMessage,
    ModelMetrics,
    ModelRequest,
    ModelResponse,
    run_benchmark,
)


class TruncatedProvider:
    provider_name = "fake"

    def runtime_version(self):
        return "fake-1"

    def runtime_diagnostics(self):
        return {"provider": "fake", "runtime_version": "fake-1", "running_models": []}

    def chat(self, request, *, timeout_seconds=300.0):
        return ModelResponse(
            provider="fake",
            runtime_version="fake-1",
            model=request.model,
            content="",
            thinking="unfinished reasoning",
            done_reason="length",
            metrics=ModelMetrics(eval_count=request.max_output_tokens or 1),
        )


class BenchmarkOutcomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        script_path = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_local_model.py"
        spec = importlib.util.spec_from_file_location("gate005_benchmark_outcomes", script_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not load Gate 005 benchmark script")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls._script = module

    def test_length_stop_is_inconclusive_not_domain_failure(self) -> None:
        case = BenchmarkCase(
            case_id="truncated",
            description="synthetic truncation",
            request=ModelRequest(
                model="candidate",
                messages=(ModelMessage("user", "answer"),),
                max_output_tokens=2048,
            ),
            scorer=lambda response: (False, "scorer must not classify truncated output"),
        )
        record = run_benchmark(TruncatedProvider(), (case,))[0]
        self.assertIsNone(record.passed)
        self.assertEqual(record.done_reason, "length")
        self.assertIn("INCONCLUSIVE", record.score_note or "")

    def test_exit_codes_distinguish_pass_fail_and_inconclusive(self) -> None:
        self.assertEqual(self._script._result_exit_code({"failed": 0, "unscored": 0}), 0)
        self.assertEqual(self._script._result_exit_code({"failed": 1, "unscored": 0}), 2)
        self.assertEqual(self._script._result_exit_code({"failed": 0, "unscored": 1}), 3)
        self.assertEqual(self._script._result_exit_code({"failed": 1, "unscored": 1}), 2)


if __name__ == "__main__":
    unittest.main()
