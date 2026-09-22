from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from engineering_ai.models import (
    DeterministicModelRouter,
    ModelCapability,
    ModelCapabilityRegistry,
    ModelTaskClass,
    RouteRequest,
    RouteStatus,
    accepted_registry,
)


ROOT = Path(__file__).resolve().parents[1]


def run_checked(args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr or result.stdout or "no output"
        raise RuntimeError(f"command failed: {args!r}\n{detail}")
    return result


def run_test_module(pattern: str) -> None:
    run_checked(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            pattern,
        ]
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    modules = (
        "test_models.py",
        "test_benchmark_outcomes.py",
        "test_benchmark_script.py",
        "test_benchmark_timeout.py",
        "test_gate008_qualification.py",
        "test_model_routing.py",
    )
    for pattern in modules:
        run_test_module(pattern)

    qualification_evidence = ROOT / "docs" / "evidence" / "gate008" / "qualification.md"
    routing_evidence = ROOT / "docs" / "evidence" / "gate009" / "routing.md"
    baseline_evidence = ROOT / "docs" / "evidence" / "gate005" / "model-selection.md"

    for path in (qualification_evidence, routing_evidence, baseline_evidence):
        require(path.is_file(), f"missing accepted evidence file: {path}")

    qualification_text = qualification_evidence.read_text(encoding="utf-8")
    routing_text = routing_evidence.read_text(encoding="utf-8")
    baseline_text = baseline_evidence.read_text(encoding="utf-8")

    require(
        "QUALIFIED_GENERAL_PLANNER" in qualification_text,
        "Gate 008 general planner qualification evidence missing",
    )
    require(
        "QUALIFIED_WITH_LIMITATIONS_CODE_REPOSITORY" in qualification_text,
        "Gate 008 code qualification evidence missing",
    )
    require(
        "QWEN35_GENERAL_4_OF_4_PASS" in qualification_text,
        "Gate 008 measured general benchmark evidence missing",
    )
    require(
        "QWEN25_CODER_3_OF_4_WITH_CONFIRMED_TOOL_TRANSPORT_LIMITATION"
        in qualification_text,
        "Gate 008 measured coder benchmark evidence missing",
    )
    require(
        "Gate 009" in routing_text and "deterministic" in routing_text.lower(),
        "Gate 009 deterministic routing evidence missing",
    )
    require(
        "gpt-oss:20b" in baseline_text,
        "Gate 005 accepted baseline evidence missing",
    )

    registry = accepted_registry()
    identities = tuple((entry.provider, entry.model) for entry in registry.entries)
    require(
        identities
        == (
            ("ollama", "qwen3.5:9b"),
            ("ollama", "qwen2.5-coder:7b-instruct"),
            ("ollama", "gpt-oss:20b"),
        ),
        f"unexpected accepted registry identities: {identities!r}",
    )
    require(
        all(entry.evidence_refs for entry in registry.entries),
        "accepted registry contains an entry without evidence refs",
    )
    require(
        all(
            (ROOT / ref).is_file()
            for entry in registry.entries
            for ref in entry.evidence_refs
        ),
        "accepted registry contains an evidence ref that does not resolve",
    )

    router = DeterministicModelRouter(registry)

    general = router.route(
        RouteRequest(task_class=ModelTaskClass.GENERAL_PLANNING)
    )
    code = router.route(
        RouteRequest(task_class=ModelTaskClass.CODE_REPOSITORY)
    )
    baseline = router.route(
        RouteRequest(task_class=ModelTaskClass.BASELINE_REASONING)
    )
    require(general.status is RouteStatus.ROUTE, "general planning did not route")
    require(general.model == "qwen3.5:9b", "unexpected general planning route")
    require(code.status is RouteStatus.ROUTE, "code repository did not route")
    require(
        code.model == "qwen2.5-coder:7b-instruct",
        "unexpected code repository route",
    )
    require(baseline.status is RouteStatus.ROUTE, "baseline reasoning did not route")
    require(baseline.model == "gpt-oss:20b", "unexpected baseline route")

    code_native_tools = router.route(
        RouteRequest(
            task_class=ModelTaskClass.CODE_REPOSITORY,
            native_tool_proposals_required=True,
        )
    )
    oversized_context = router.route(
        RouteRequest(
            task_class=ModelTaskClass.GENERAL_PLANNING,
            context_tokens=8193,
        )
    )
    oversized_output = router.route(
        RouteRequest(
            task_class=ModelTaskClass.CODE_REPOSITORY,
            max_output_tokens=2049,
        )
    )
    vision_default = router.route(
        RouteRequest(task_class=ModelTaskClass.VISION_ANALYSIS)
    )
    image_default = router.route(
        RouteRequest(task_class=ModelTaskClass.IMAGE_GENERATION)
    )

    for decision, label in (
        (code_native_tools, "coder native tools"),
        (oversized_context, "oversized context"),
        (oversized_output, "oversized output"),
        (vision_default, "unmeasured vision"),
        (image_default, "unmeasured image generation"),
    ):
        require(
            decision.status is RouteStatus.NO_ROUTE,
            f"{label} unexpectedly produced a route",
        )

    alternate = ModelCapability(
        model="synthetic-replaceable-planner",
        provider="synthetic-provider",
        task_classes=(ModelTaskClass.GENERAL_PLANNING,),
        qualification="QUALIFIED_SYNTHETIC_ROUTING_ACCEPTANCE_ONLY",
        max_qualified_context_tokens=8192,
        max_qualified_output_tokens=2048,
        native_tool_proposals=False,
        evidence_refs=("docs/evidence/gate009/routing.md",),
        priority=1,
    )
    alternate_router = DeterministicModelRouter(
        ModelCapabilityRegistry((alternate,))
    )
    alternate_decision = alternate_router.route(
        RouteRequest(task_class=ModelTaskClass.GENERAL_PLANNING)
    )
    require(
        alternate_decision.status is RouteStatus.ROUTE,
        "alternate evidence-qualified registry entry did not route",
    )
    require(
        alternate_decision.model == "synthetic-replaceable-planner"
        and alternate_decision.provider == "synthetic-provider",
        "alternate route did not preserve provider/model identity",
    )
    require(
        set(vars(alternate_router)) == {"_registry"},
        "router gained provider/tool execution dependency",
    )

    payload = {
        "gate": "031",
        "state": "PASS_V1_0_MEASURED_REPLACEABLE_MULTI_MODEL_ROUTING",
        "acceptance_basis": {
            "provider_neutral_model_contract_tests": True,
            "benchmark_contract_tests": True,
            "gate008_qualification_contract_tests": True,
            "gate009_routing_contract_tests": True,
            "accepted_registry_identities": [
                {"provider": provider, "model": model}
                for provider, model in identities
            ],
        },
        "routes": {
            "general_planning": general.model,
            "code_repository": code.model,
            "baseline_reasoning": baseline.model,
            "alternate_synthetic_provider": alternate_decision.provider,
            "alternate_synthetic_model": alternate_decision.model,
        },
        "assertions": {
            "accepted_routes_are_evidence_backed": True,
            "qualification_limits_are_fail_closed": True,
            "unmeasured_routes_are_absent": True,
            "router_is_provider_execution_neutral": True,
            "router_is_tool_execution_neutral": True,
            "registry_entry_is_replaceable_without_router_code_change": True,
            "new_model_qualification_performed": False,
            "production_runtime_replaced_in_practice": False,
            "automatic_specialist_fallback": False,
            "remote_git_mutation_authority": False,
            "release_authority": False,
            "fabrication_authority": False,
        },
        "later_v1_0_criterion_remaining": "MODEL_RUNTIME_REPLACEABILITY_DEMONSTRATED_IN_PRACTICE",
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
