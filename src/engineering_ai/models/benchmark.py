"""Measured local-model benchmark harness.

The harness records observations. It does not promote model answers to evidence of
engineering correctness; domain correctness must be scored against deterministic
checks or explicit review criteria.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from engineering_ai.models.protocol import ModelProvider
from engineering_ai.models.types import ModelRequest, ModelResponse


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    description: str
    request: ModelRequest
    scorer: Callable[[ModelResponse], tuple[bool, str]] | None = None


@dataclass(frozen=True)
class BenchmarkRecord:
    case_id: str
    description: str
    provider: str
    runtime_version: str | None
    model: str
    elapsed_seconds: float
    passed: bool | None
    score_note: str | None
    content: str
    thinking: str
    done_reason: str | None
    tool_calls: tuple[Mapping[str, Any], ...]
    metrics: Mapping[str, Any]
    runtime_diagnostics: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_benchmark(
    provider: ModelProvider,
    cases: Sequence[BenchmarkCase],
    *,
    timeout_seconds: float = 300.0,
) -> tuple[BenchmarkRecord, ...]:
    """Run cases sequentially and return immutable benchmark observations.

    A response stopped by an output-token limit is recorded as inconclusive rather
    than as a domain failure, because the deterministic scorer never received a
    complete model answer.
    """
    records: list[BenchmarkRecord] = []
    for case in cases:
        started = perf_counter()
        response = provider.chat(case.request, timeout_seconds=timeout_seconds)
        elapsed = perf_counter() - started
        if response.done_reason == "length":
            passed: bool | None = None
            note: str | None = "INCONCLUSIVE: generation stopped at output-token limit"
        elif case.scorer is None:
            passed = None
            note = None
        else:
            passed, note = case.scorer(response)
        diagnostics = provider.runtime_diagnostics()
        records.append(
            BenchmarkRecord(
                case_id=case.case_id,
                description=case.description,
                provider=response.provider,
                runtime_version=response.runtime_version,
                model=response.model,
                elapsed_seconds=elapsed,
                passed=passed,
                score_note=note,
                content=response.content,
                thinking=response.thinking,
                done_reason=response.done_reason,
                tool_calls=tuple(
                    {"name": call.name, "arguments": dict(call.arguments)}
                    for call in response.tool_calls
                ),
                metrics=asdict(response.metrics),
                runtime_diagnostics=dict(diagnostics),
            )
        )
    return tuple(records)
