from __future__ import annotations

import json

from engineering_ai.models import (
    DeterministicModelRouter,
    ModelCapability,
    ModelCapabilityRegistry,
    ModelMetrics,
    ModelResponse,
    ModelTaskClass,
    accepted_registry,
)
from engineering_ai.supervisor import (
    VisionAuthority,
    VisionInput,
    VisionRoutingError,
    VisionWorker,
    VisionWorkerRequest,
)


class FakeVisionProvider:
    provider_name = "fake"

    def __init__(self) -> None:
        self.calls = []

    def runtime_version(self):
        return "fake-vision-1"

    def runtime_diagnostics(self):
        return {"provider": "fake", "runtime_version": "fake-vision-1"}

    def chat(self, request, *, timeout_seconds=300.0):
        self.calls.append((request, timeout_seconds))
        return ModelResponse(
            provider="fake",
            runtime_version="fake-vision-1",
            model=request.model,
            content=json.dumps(
                {
                    "summary": "Synthetic Vision boundary smoke completed.",
                    "observations": [
                        {
                            "source_refs": ["smoke:schematic-1"],
                            "kind": "schematic",
                            "statement": "Synthetic visible feature.",
                        }
                    ],
                }
            ),
            done_reason="stop",
            metrics=ModelMetrics(eval_count=1, eval_duration_ns=1_000_000),
        )


def make_request() -> VisionWorkerRequest:
    return VisionWorkerRequest(
        project_id="engineering-ai",
        task_id="gate023-smoke",
        prompt="Return one bounded observation for the explicit image.",
        images=(
            VisionInput(
                source_ref="smoke:schematic-1",
                media_type="image/png",
                data=b"GATE023-SYNTHETIC-IMAGE-PAYLOAD",
            ),
        ),
    )


def main() -> int:
    provider = FakeVisionProvider()

    blocked_worker = VisionWorker(
        provider=provider,
        router=DeterministicModelRouter(accepted_registry()),
    )
    blocked = False
    try:
        blocked_worker.observe(make_request())
    except VisionRoutingError:
        blocked = True
    assert blocked
    assert provider.calls == []

    capability = ModelCapability(
        model="vision-qualified-smoke",
        provider="fake",
        task_classes=(ModelTaskClass.VISION_ANALYSIS,),
        qualification="QUALIFIED_SYNTHETIC_BOUNDARY_ONLY",
        max_qualified_context_tokens=8192,
        max_qualified_output_tokens=2048,
        reasoning_effort=None,
        supports_native_tool_proposals=False,
        supports_vision_inputs=True,
        evidence_refs=("ev-gate023-synthetic-boundary",),
        priority=10,
    )
    routed_worker = VisionWorker(
        provider=provider,
        router=DeterministicModelRouter(ModelCapabilityRegistry((capability,))),
    )
    result = routed_worker.observe(make_request(), timeout_seconds=30)
    assert len(provider.calls) == 1
    sent_request = provider.calls[0][0]
    assert sent_request.tools == ()
    assert result.authority is VisionAuthority.ADVISORY
    assert result.evidence_eligible is False
    assert result.physical_validation == "PHYSICAL_NOT_EXECUTED"
    assert result.sources[0].source_ref == "smoke:schematic-1"
    assert result.observations[0].source_refs == ("smoke:schematic-1",)
    assert "GATE023-SYNTHETIC-IMAGE-PAYLOAD" not in repr(result)

    payload = {
        "gate": "023",
        "state": "PASS_PROVENANCE_PRESERVING_VISION_BOUNDARY",
        "unmeasured_default_vision_route": "NO_ROUTE",
        "provider_calls_before_qualified_route": 0,
        "qualified_synthetic_route_status": "PASS",
        "provider_call_count": len(provider.calls),
        "tool_surface_exposed": False,
        "result_authority": result.authority.value,
        "evidence_eligible": result.evidence_eligible,
        "source_ref_preserved": True,
        "source_hash_preserved": len(result.sources[0].content_sha256) == 64,
        "raw_image_persisted_in_result": False,
        "external_network": False,
        "automatic_evidence_promotion": False,
        "production_vision_model_qualified": False,
        "physical_validation": result.physical_validation,
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
