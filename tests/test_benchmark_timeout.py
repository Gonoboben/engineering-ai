from __future__ import annotations

import unittest

from engineering_ai.models import BenchmarkCase, ModelMessage, ModelRequest, run_benchmark
from engineering_ai.models.protocol import ModelProviderUnavailable


class TimeoutProvider:
    provider_name = "timeout-fake"

    def runtime_version(self):
        return "timeout-fake-1"

    def runtime_diagnostics(self):
        return {"provider": self.provider_name}

    def chat(self, request, *, timeout_seconds=300.0):
        raise ModelProviderUnavailable("synthetic timeout")


class BenchmarkTimeoutTests(unittest.TestCase):
    def test_provider_timeout_is_preserved_as_inconclusive_record(self) -> None:
        case = BenchmarkCase(
            case_id="timeout",
            description="Synthetic provider timeout",
            request=ModelRequest(
                model="candidate",
                messages=(ModelMessage("user", "test"),),
            ),
        )

        records = run_benchmark(TimeoutProvider(), (case,), timeout_seconds=1.0)

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertIsNone(record.passed)
        self.assertEqual(record.done_reason, "provider_error")
        self.assertIn("INCONCLUSIVE", record.score_note or "")
        self.assertIn("synthetic timeout", record.score_note or "")
        self.assertEqual(record.provider, "timeout-fake")
        self.assertEqual(record.model, "candidate")
        self.assertEqual(record.metrics, {})
        self.assertEqual(record.runtime_diagnostics, {})


if __name__ == "__main__":
    unittest.main()
