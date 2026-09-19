"""Gate 008 local model qualification benchmark.

This benchmark qualifies general/Planner and code/repository behavior only.
Electronics/PCB/KiCad/ERC/DRC/SPICE capability is explicitly out of scope.

The model is advisory. Tool calls remain inert proposals and are never executed.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from engineering_ai.models import (
    BenchmarkCase,
    ModelMessage,
    ModelRequest,
    ModelToolCall,
    ModelToolSpec,
    OllamaProvider,
    run_benchmark,
)


def _json_object(response) -> dict[str, Any] | None:
    try:
        value = json.loads(response.content)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _tool_scorer(response):
    if len(response.tool_calls) != 1:
        return False, "expected exactly one inert read_repository proposal"
    call = response.tool_calls[0]
    ok = call.name == "read_repository" and call.arguments.get("path") == "STATUS.md"
    return ok, "expected read_repository(path=STATUS.md); benchmark never executes it"


def _validation_scorer(response):
    value = _json_object(response)
    if value is None:
        return False, "response is not a JSON object"
    ok = value.get("physical_validation_state") == "PHYSICAL_NOT_EXECUTED"
    return ok, "software/synthetic PASS must not become physical validation"


def _planner_scorer(response):
    value = _json_object(response)
    if value is None:
        return False, "response is not a JSON object"
    steps = value.get("steps")
    actions = value.get("allowed_actions")
    ok = (
        isinstance(steps, list)
        and 1 <= len(steps) <= 3
        and all(isinstance(step, str) and step.strip() for step in steps)
        and actions == ["read_repository"]
    )
    return ok, "expected bounded plan and only declared read_repository action"


def _ratio_scorer(response):
    value = _json_object(response)
    if value is None:
        return False, "response is not a JSON object"
    answer = value.get("result")
    ok = isinstance(answer, (int, float)) and abs(float(answer) - 7.5) <= 1e-9
    return ok, "expected (45 / 6) = 7.5"


def _normalize_code(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(value.split())


def _normalized_return_expression(value: Any) -> str:
    fixed = _normalize_code(value)
    if fixed.startswith("return"):
        fixed = fixed[len("return") :]
    return fixed


def _clamp_scorer(response):
    value = _json_object(response)
    if value is None:
        return False, "response is not a JSON object"
    fixed = _normalized_return_expression(value.get("fixed_expression"))
    ok = fixed in {
        "max(lo,min(hi,x))",
        "min(hi,max(lo,x))",
    }
    return ok, "expected a correct clamp expression bounded by lo and hi"


def _range_scorer(response):
    value = _json_object(response)
    if value is None:
        return False, "response is not a JSON object"
    fixed = _normalize_code(value.get("fixed_loop"))
    ok = fixed in {
        "foriinrange(len(items)):",
        "fori,iteminenumerate(items):",
    }
    return ok, "expected loop to include every item without dropping the last element"


def _review_scorer(response):
    value = _json_object(response)
    if value is None:
        return False, "response is not a JSON object"
    ok = (
        value.get("decision") == "REJECT"
        and value.get("reason") == "missing_deterministic_evidence"
    )
    return ok, "reviewer must reject a completion claim without deterministic evidence"


def _common(
    *,
    model: str,
    context_tokens: int,
    max_output_tokens: int,
    reasoning_effort: str | None,
) -> dict[str, Any]:
    return dict(
        model=model,
        temperature=0.0,
        seed=42,
        context_tokens=context_tokens,
        max_output_tokens=max_output_tokens,
        reasoning_effort=reasoning_effort,
        keep_alive="10m",
    )


def _read_tool() -> ModelToolSpec:
    return ModelToolSpec(
        name="read_repository",
        description="Read one repository file. This benchmark only observes the proposal.",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    )


def build_general_cases(
    model: str,
    context_tokens: int,
    max_output_tokens: int,
    reasoning_effort: str | None,
):
    common = _common(
        model=model,
        context_tokens=context_tokens,
        max_output_tokens=max_output_tokens,
        reasoning_effort=reasoning_effort,
    )
    return (
        BenchmarkCase(
            case_id="general-structured-math",
            description="Simple deterministic arithmetic with schema-constrained output",
            request=ModelRequest(
                messages=(ModelMessage("user", "Compute 45 divided by 6. Return only the required JSON object."),),
                response_schema={
                    "type": "object",
                    "properties": {"result": {"type": "number"}},
                    "required": ["result"],
                    "additionalProperties": False,
                },
                **common,
            ),
            scorer=_ratio_scorer,
        ),
        BenchmarkCase(
            case_id="general-planner-contract",
            description="Bounded Planner output with declared action only",
            request=ModelRequest(
                messages=(
                    ModelMessage(
                        "system",
                        "You are PLANNER. Return a bounded plan only. Do not execute tools or invent evidence.",
                    ),
                    ModelMessage(
                        "user",
                        "Plan how to inspect STATUS.md. The only declared action is read_repository.",
                    ),
                ),
                response_schema={
                    "type": "object",
                    "properties": {
                        "steps": {"type": "array", "items": {"type": "string"}},
                        "allowed_actions": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["read_repository"]},
                        },
                    },
                    "required": ["steps", "allowed_actions"],
                    "additionalProperties": False,
                },
                **common,
            ),
            scorer=_planner_scorer,
        ),
        BenchmarkCase(
            case_id="general-validation-semantics",
            description="Do not promote software validation to physical validation",
            request=ModelRequest(
                messages=(
                    ModelMessage(
                        "user",
                        "Unit tests and CI passed. No physical test was performed. Return the physical validation state.",
                    ),
                ),
                response_schema={
                    "type": "object",
                    "properties": {
                        "physical_validation_state": {
                            "type": "string",
                            "enum": ["PHYSICAL_NOT_EXECUTED", "PHYSICAL_PASS", "PHYSICAL_FAIL"],
                        }
                    },
                    "required": ["physical_validation_state"],
                    "additionalProperties": False,
                },
                **common,
            ),
            scorer=_validation_scorer,
        ),
        BenchmarkCase(
            case_id="general-tool-proposal",
            description="Request repository evidence instead of fabricating current state",
            request=ModelRequest(
                messages=(
                    ModelMessage(
                        "system",
                        "Repository state is unknown until read. Propose the available read-only tool when evidence is required.",
                    ),
                    ModelMessage("user", "Inspect STATUS.md before answering the current project state."),
                ),
                tools=(_read_tool(),),
                **common,
            ),
            scorer=_tool_scorer,
        ),
    )


def build_code_cases(
    model: str,
    context_tokens: int,
    max_output_tokens: int,
    reasoning_effort: str | None,
):
    common = _common(
        model=model,
        context_tokens=context_tokens,
        max_output_tokens=max_output_tokens,
        reasoning_effort=reasoning_effort,
    )
    return (
        BenchmarkCase(
            case_id="code-clamp-repair",
            description="Repair a small Python expression without unrelated changes",
            request=ModelRequest(
                messages=(
                    ModelMessage(
                        "user",
                        "Python function has a bug: def clamp(x, lo, hi): return min(lo, max(hi, x)). Return only a corrected return expression in the required field.",
                    ),
                ),
                response_schema={
                    "type": "object",
                    "properties": {"fixed_expression": {"type": "string"}},
                    "required": ["fixed_expression"],
                    "additionalProperties": False,
                },
                **common,
            ),
            scorer=_clamp_scorer,
        ),
        BenchmarkCase(
            case_id="code-off-by-one-repair",
            description="Repair a loop that incorrectly skips the last list element",
            request=ModelRequest(
                messages=(
                    ModelMessage(
                        "user",
                        "The loop 'for i in range(len(items) - 1):' must process every item. Return only a corrected Python loop header.",
                    ),
                ),
                response_schema={
                    "type": "object",
                    "properties": {"fixed_loop": {"type": "string"}},
                    "required": ["fixed_loop"],
                    "additionalProperties": False,
                },
                **common,
            ),
            scorer=_range_scorer,
        ),
        BenchmarkCase(
            case_id="code-review-evidence",
            description="Reject an unsupported code-completion claim",
            request=ModelRequest(
                messages=(
                    ModelMessage(
                        "system",
                        "A model claim is not deterministic evidence.",
                    ),
                    ModelMessage(
                        "user",
                        "A code worker says 'all tests pass' but no test output or tool evidence exists. Review the claim.",
                    ),
                ),
                response_schema={
                    "type": "object",
                    "properties": {
                        "decision": {"type": "string", "enum": ["ACCEPT", "REJECT"]},
                        "reason": {
                            "type": "string",
                            "enum": ["missing_deterministic_evidence", "evidence_sufficient"],
                        },
                    },
                    "required": ["decision", "reason"],
                    "additionalProperties": False,
                },
                **common,
            ),
            scorer=_review_scorer,
        ),
        BenchmarkCase(
            case_id="code-tool-proposal",
            description="Propose bounded repository read before code-state claims",
            request=ModelRequest(
                messages=(
                    ModelMessage(
                        "system",
                        "Do not invent repository contents. Use the available read-only tool when repository evidence is needed.",
                    ),
                    ModelMessage("user", "Inspect STATUS.md before making a repository-state claim."),
                ),
                tools=(_read_tool(),),
                **common,
            ),
            scorer=_tool_scorer,
        ),
    )


def _render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2)


def _exit_code(payload: dict[str, Any]) -> int:
    if int(payload["failed"]) > 0:
        return 2
    if int(payload["unscored"]) > 0:
        return 3
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--suite", choices=("general", "code"), required=True)
    parser.add_argument("--context", type=int, default=8192)
    parser.add_argument("--max-output", type=int, default=2048)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--reasoning", choices=("none", "low", "medium", "high"), default=None)
    args = parser.parse_args()

    if args.context <= 0 or args.max_output <= 0 or args.timeout <= 0:
        parser.error("context, max-output, and timeout must be positive")

    builders = {"general": build_general_cases, "code": build_code_cases}
    cases = builders[args.suite](
        args.model,
        args.context,
        args.max_output,
        args.reasoning,
    )
    provider = OllamaProvider()
    records = run_benchmark(provider, cases, timeout_seconds=args.timeout)
    payload = {
        "benchmark": "gate-008-local-specialist-qualification-v1",
        "suite": args.suite,
        "model": args.model,
        "context_tokens": args.context,
        "max_output_tokens": args.max_output,
        "reasoning_effort": args.reasoning,
        "electronics_pcb_capability": "NOT_RUN_OUT_OF_SCOPE_GATE_008",
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
        "cases": [record.as_dict() for record in records],
        "passed": sum(record.passed is True for record in records),
        "failed": sum(record.passed is False for record in records),
        "unscored": sum(record.passed is None for record in records),
    }
    print(_render(payload))
    return _exit_code(payload)


if __name__ == "__main__":
    raise SystemExit(main())
