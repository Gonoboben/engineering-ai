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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    run_checked(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_model_routing.py",
        ]
    )

    gate005 = (ROOT / "docs/evidence/gate005/model-selection.md").read_text(encoding="utf-8")
    gate008 = (ROOT / "docs/evidence/gate008/qualification.md").read_text(encoding="utf-8")
    gate009 = (ROOT / "docs/evidence/gate009/routing.md").read_text(encoding="utf-8")

    require(
        "gpt-oss:20b" in gate005 and "4/4 machine-scored cases PASS" in gate005,
        "Gate 005 measured baseline evidence missing",
    )
    require(
        "qwen3.5:9b" in gate008 and "general suite: `4/4 PASS`" in gate008,
        "Gate 008 qwen3.5 measured qualification evidence missing",
    )
    require(
        "qwen2.5-coder:7b-instruct" in gate008
        and "corrected rerun result: `3 PASS / 1 FAIL / 0 INCONCLUSIVE`" in gate008,
        "Gate 008 coder measured qualification evidence missing",
    )
    require(
        "Deterministic routing table" in gate009,
        "Gate 009 deterministic routing evidence missing",
    )

    registry = accepted_registry()
    router = DeterministicModelRouter(registry)

    general = router.route(RouteRequest(task_class=ModelTaskClass.GENERAL_PLANNING))
    code = router.route(RouteRequest(task_class=ModelTaskClass.CODE_REPOSITORY))
    baseline = router.route(RouteRequest(task_class=ModelTaskClass.BASELINE_REASONING))
    code_tools = router.route(
        RouteRequest(
            task_class=ModelTaskClass.CODE_REPOSITORY,
            requires_native_tool_proposals=True,
        )
    )
    over_context = router.route(
        RouteRequest(
            task_class=ModelTaskClass.GENERAL_PLANNING,
            context_tokens=8193,
        )
    )
    over_output = router.route(
        RouteRequest(
            task_class=ModelTaskClass.CODE_REPOSITORY,
            max_output_tokens=2049,
        )
    )
    vision = router.route(
        RouteRequest(
            task_class=ModelTaskClass.VISION_ANALYSIS,
            requires_vision_inputs=True,
        )
    )
    image = router.route(
        RouteRequest(
            task_class=ModelTaskClass.IMAGE_GENERATION,
            requires_image_generation=True,
        )
    )

    require(
        general.status is RouteStatus.ROUTE and general.model == "qwen3.5:9b",
        "general planning did not route to measured qualified model",
    )
    require(
        code.status is RouteStatus.ROUTE
        and code.model == "qwen2.5-coder:7b-instruct",
        "code/repository did not route to measured qualified model",
    )
    require(
        baseline.status is RouteStatus.ROUTE and baseline.model == "gpt-oss:20b",
        "baseline reasoning did not route to accepted measured baseline",
    )
    require(
        code_tools.status is RouteStatus.NO_ROUTE,
        "unsupported native-tool coder requirement did not fail closed",
    )
    require(
        over_context.status is RouteStatus.NO_ROUTE,
        "context above measured envelope did not fail closed",
    )
    require(
        over_output.status is RouteStatus.NO_ROUTE,
        "output above measured envelope did not fail closed",
    )
    require(
        vision.status is RouteStatus.NO_ROUTE and image.status is RouteStatus.NO_ROUTE,
        "unmeasured multimodal route was inferred",
    )

    require(
        all(entry.evidence_refs for entry in registry.entries),
        "accepted registry contains entry without evidence refs",
    )

    replacement = ModelCapability(
        model="replacement-general",
        provider="replacement-provider",
        task_classes=(ModelTaskClass.GENERAL_PLANNING,),
        qualification="QUALIFIED_TEST_REPLACEMENT",
        max_qualified_context_tokens=8192,
        max_qualified_output_tokens=2048,
        reasoning_effort=None,
        supports_native_tool_proposals=False,
        evidence_refs=("synthetic:test-only:replacement-evidence",),
        priority=5,
    )
    replacement_registry = ModelCapabilityRegistry((*registry.entries, replacement))
    replacement_router = DeterministicModelRouter(replacement_registry)
    replacement_decision = replacement_router.route(
        RouteRequest(task_class=ModelTaskClass.GENERAL_PLANNING)
    )

    require(
        replacement_decision.status is RouteStatus.ROUTE
        and replacement_decision.model == "replacement-general"
        and replacement_decision.provider == "replacement-provider",
        "registry substitution did not change routing through the data-only boundary",
    )
    require(
        replacement_decision.evidence_refs
        == ("synthetic:test-only:replacement-evidence",),
        "replacement route lost evidence provenance",
    )
    require(
        set(vars(replacement_router)) == {"_registry"},
        "Router gained provider/tool execution dependency",
    )

    payload = {
        "gate": "031",
        "state": "PASS_V1_0_MEASURED_REPLACEABLE_MULTI_MODEL_ROUTING",
        "acceptance_basis": {
            "gate005_measured_baseline": True,
            "gate008_measured_specialists": True,
            "gate009_evidence_backed_router": True,
            "accepted_models": [entry.model for entry in registry.entries],
        },
        "routes": {
            "GENERAL_PLANNING": general.model,
            "CODE_REPOSITORY": code.model,
            "BASELINE_REASONING": baseline.model,
            "CODE_REPOSITORY_NATIVE_TOOL_REQUIRED": code_tools.status.value,
            "OVER_MEASURED_CONTEXT": over_context.status.value,
            "OVER_MEASURED_OUTPUT": over_output.status.value,
            "VISION_UNMEASURED": vision.status.value,
            "IMAGE_GENERATION_UNMEASURED": image.status.value,
        },
        "assertions": {
            "measured_evidence_required": True,
            "route_provenance_preserved": True,
            "registry_boundary_replaceable": True,
            "supervisor_router_architecture_unchanged": True,
            "router_executes_models": False,
            "router_executes_tools": False,
            "unmeasured_capability_auto_promoted": False,
            "practical_runtime_replacement_claimed": False,
            "remote_git_mutation_authority": False,
            "release_authority": False,
            "fabrication_authority": False,
        },
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
