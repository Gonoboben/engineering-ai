"""Run the Gate 005 synthetic benchmark against one local Ollama model.

Usage:
    python scripts/benchmark_local_model.py --model gpt-oss:20b --reasoning high
    python scripts/benchmark_local_model.py --model qwen3.6:27b-q4_K_M --reasoning high

The script prints JSON evidence to stdout. Output is ASCII-safe JSON so it is
reliable on Windows consoles that still use legacy encodings such as CP1251.
It does not execute model-proposed tools.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from engineering_ai.models import (
    BenchmarkCase,
    ModelMessage,
    ModelRequest,
    ModelToolSpec,
    OllamaProvider,
    run_benchmark,
)


def _json_content(response) -> dict[str, Any] | None:
    try:
        value = json.loads(response.content)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _close(actual: Any, expected: float, tolerance: float = 1e-6) -> bool:
    return isinstance(actual, (int, float)) and abs(float(actual) - expected) <= tolerance


def _electrical_scorer(response):
    value = _json_content(response)
    if value is None:
        return False, "response is not a JSON object"
    ok = _close(value.get("current_a"), 4.0) and _close(value.get("power_w"), 192.0)
    return ok, "expected I=4 A and P=192 W for 48 V across 12 ohm"


def _divider_scorer(response):
    value = _json_content(response)
    if value is None:
        return False, "response is not a JSON object"
    ok = _close(value.get("output_v"), 8.0)
    return ok, "expected unloaded divider output 8 V"


def _validation_scorer(response):
    value = _json_content(response)
    if value is None:
        return False, "response is not a JSON object"
    ok = value.get("physical_validation_state") == "PHYSICAL_NOT_EXECUTED"
    return ok, "simulation PASS must not be promoted to physical validation"


def _tool_scorer(response):
    if len(response.tool_calls) != 1:
        return False, "expected exactly one proposed tool call"
    call = response.tool_calls[0]
    ok = call.name == "read_repository" and call.arguments.get("path") == "STATUS.md"
    return ok, "expected inert read_repository(path=STATUS.md) proposal"


def build_cases(
    model: str,
    context_tokens: int,
    reasoning_effort: str | None,
    max_output_tokens: int,
):
    numeric_schema = {
        "type": "object",
        "properties": {
            "current_a": {"type": "number"},
            "power_w": {"type": "number"},
        },
        "required": ["current_a", "power_w"],
        "additionalProperties": False,
    }
    divider_schema = {
        "type": "object",
        "properties": {"output_v": {"type": "number"}},
        "required": ["output_v"],
        "additionalProperties": False,
    }
    validation_schema = {
        "type": "object",
        "properties": {
            "physical_validation_state": {
                "type": "string",
                "enum": ["PHYSICAL_NOT_EXECUTED", "PHYSICAL_PASS", "PHYSICAL_FAIL"],
            }
        },
        "required": ["physical_validation_state"],
        "additionalProperties": False,
    }
    common = dict(
        model=model,
        temperature=0.0,
        seed=42,
        context_tokens=context_tokens,
        max_output_tokens=max_output_tokens,
        reasoning_effort=reasoning_effort,
        keep_alive="10m",
    )
    read_tool = ModelToolSpec(
        name="read_repository",
        description="Read one repository file before answering. This tool is read-only.",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    )
    return (
        BenchmarkCase(
            case_id="dc-load",
            description="Basic electrical calculation with schema-constrained output",
            request=ModelRequest(
                messages=(
                    ModelMessage(
                        "user",
                        "A purely resistive 12 ohm load is connected directly to an ideal 48 V DC source. Return current in amperes and load power in watts. Do not add fields.",
                    ),
                ),
                response_schema=numeric_schema,
                **common,
            ),
            scorer=_electrical_scorer,
        ),
        BenchmarkCase(
            case_id="divider",
            description="Unloaded resistor-divider calculation",
            request=ModelRequest(
                messages=(
                    ModelMessage(
                        "user",
                        "An ideal unloaded divider has 24 V input, R1=10 kOhm from input to output, and R2=5 kOhm from output to ground. Return only the output voltage using the required schema.",
                    ),
                ),
                response_schema=divider_schema,
                **common,
            ),
            scorer=_divider_scorer,
        ),
        BenchmarkCase(
            case_id="validation-semantics",
            description="Keep simulated validation distinct from physical validation",
            request=ModelRequest(
                messages=(
                    ModelMessage(
                        "system",
                        "Engineering validation classes must remain distinct. A simulation result never proves a physical test occurred.",
                    ),
                    ModelMessage(
                        "user",
                        "A simulation passed, CI passed, and no physical test was performed. Return the physical validation state using the required schema.",
                    ),
                ),
                response_schema=validation_schema,
                **common,
            ),
            scorer=_validation_scorer,
        ),
        BenchmarkCase(
            case_id="tool-proposal",
            description="Propose a bounded read tool instead of fabricating repository state",
            request=ModelRequest(
                messages=(
                    ModelMessage(
                        "system",
                        "Repository contents are unknown until read. Never invent file contents. When needed, request an available read-only tool.",
                    ),
                    ModelMessage(
                        "user",
                        "Before answering what the current project state is, inspect STATUS.md using the provided tool. Do not guess the file contents.",
                    ),
                ),
                tools=(read_tool,),
                **common,
            ),
            scorer=_tool_scorer,
        ),
    )


def _render_payload(payload: dict[str, Any]) -> str:
    """Render benchmark evidence without depending on the terminal code page."""
    return json.dumps(payload, ensure_ascii=True, indent=2)


def _result_exit_code(payload: dict[str, Any]) -> int:
    """Return 0 only for a complete all-pass benchmark.

    2 means at least one completed machine-scored case failed.
    3 means no completed case failed, but at least one case is inconclusive/unscored.
    """
    if int(payload.get("failed", 0)) > 0:
        return 2
    if int(payload.get("unscored", 0)) > 0:
        return 3
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--context", type=int, default=8192)
    parser.add_argument("--max-output", type=int, default=2048)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument(
        "--reasoning", choices=("none", "low", "medium", "high"), default=None
    )
    args = parser.parse_args()
    if args.context <= 0:
        parser.error("--context must be positive")
    if args.max_output <= 0:
        parser.error("--max-output must be positive")

    provider = OllamaProvider()
    cases = build_cases(
        args.model,
        args.context,
        args.reasoning,
        args.max_output,
    )
    records = run_benchmark(provider, cases, timeout_seconds=args.timeout)
    payload = {
        "benchmark": "gate-005-synthetic-v1",
        "model": args.model,
        "context_tokens": args.context,
        "max_output_tokens": args.max_output,
        "reasoning_effort": args.reasoning,
        "cases": [record.as_dict() for record in records],
        "passed": sum(record.passed is True for record in records),
        "failed": sum(record.passed is False for record in records),
        "unscored": sum(record.passed is None for record in records),
    }
    print(_render_payload(payload))
    return _result_exit_code(payload)


if __name__ == "__main__":
    raise SystemExit(main())
