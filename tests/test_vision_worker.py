from __future__ import annotations

import json
import unittest

from engineering_ai.models import (
    DeterministicModelRouter,
    ModelCapability,
    ModelCapabilityRegistry,
    ModelMetrics,
    ModelResponse,
    ModelTaskClass,
    ModelToolCall,
    accepted_registry,
)
from engineering_ai.supervisor import (
    VisionAuthority,
    VisionBudgetError,
    VisionInput,
    VisionProtocolError,
    VisionRoutingError,
    VisionWorker,
    VisionWorkerRequest,
)


class FakeVisionProvider:
    provider_name = "fake"

    def __init__(self, payload: dict, *, tool_calls=(), response_provider="fake") -> None:
        self.payload = payload
        self.tool_calls = tuple(tool_calls)
        self.response_provider = response_provider
        self.calls = []

    def runtime_version(self):
        return "fake-vision-1"

    def runtime_diagnostics(self):
        return {"provider": "fake", "runtime_version": "fake-vision-1"}

    def chat(self, request, *, timeout_seconds=300.0):
        self.calls.append((request, timeout_seconds))
        return ModelResponse(
            provider=self.response_provider,
            runtime_version="fake-vision-1",
            model=request.model,
            content=json.dumps(self.payload),
            tool_calls=self.tool_calls,
            done_reason="stop",
            metrics=ModelMetrics(eval_count=1, eval_duration_ns=1_000_000),
        )


def qualified_router() -> DeterministicModelRouter:
    capability = ModelCapability(
        model="vision-qualified",
        provider="fake",
        task_classes=(ModelTaskClass.VISION_ANALYSIS,),
        qualification="QUALIFIED_VISION_SYNTHETIC_BOUNDARY",
        max_qualified_context_tokens=8192,
        max_qualified_output_tokens=2048,
        reasoning_effort=None,
        supports_native_tool_proposals=False,
        supports_vision_inputs=True,
        evidence_refs=("ev-gate023-vision-boundary",),
        priority=10,
    )
    return DeterministicModelRouter(ModelCapabilityRegistry((capability,)))


def request(data: bytes = b"\x89PNG\r\n\x1a\npng-image-payload") -> VisionWorkerRequest:
    return VisionWorkerRequest(
        project_id="engineering-ai",
        task_id="vision-task-1",
        prompt="Inspect the explicit schematic image and report visible features.",
        images=(
            VisionInput(
                source_ref="schematic:page-1",
                media_type="image/png",
                data=data,
            ),
        ),
    )


class VisionInputTests(unittest.TestCase):
    def test_input_hash_and_descriptor_are_deterministic(self) -> None:
        item = request().images[0]
        self.assertEqual(item.size_bytes, len(b"\x89PNG\r\n\x1a\npng-image-payload"))
        self.assertEqual(len(item.content_sha256), 64)
        self.assertEqual(item.content_sha256, item.as_attachment().content_sha256)
        self.assertNotIn("png-image-payload", repr(request()))

    def test_unsupported_media_and_control_source_ref_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            VisionInput("x", "image/gif", b"x")
        with self.assertRaises(ValueError):
            VisionInput("bad\nref", "image/png", b"\x89PNG\r\n\x1a\nx")
        with self.assertRaises(ValueError):
            VisionInput("bad-signature", "image/png", b"not-a-png")


class VisionWorkerTests(unittest.TestCase):
    def test_valid_execution_returns_advisory_provenance_preserving_result(self) -> None:
        provider = FakeVisionProvider(
            {
                "summary": "One schematic source inspected.",
                "observations": [
                    {
                        "source_refs": ["schematic:page-1"],
                        "kind": "schematic",
                        "statement": "A rectangular component outline is visible.",
                    }
                ],
            }
        )
        worker = VisionWorker(provider=provider, router=qualified_router())
        result = worker.observe(request(), timeout_seconds=30)

        self.assertEqual(result.authority, VisionAuthority.ADVISORY)
        self.assertFalse(result.evidence_eligible)
        self.assertEqual(result.physical_validation, "PHYSICAL_NOT_EXECUTED")
        self.assertEqual(result.sources[0].source_ref, "schematic:page-1")
        self.assertEqual(result.observations[0].source_refs, ("schematic:page-1",))
        self.assertEqual(result.route_evidence_refs, ("ev-gate023-vision-boundary",))
        self.assertEqual(len(provider.calls), 1)

        sent = provider.calls[0][0]
        self.assertEqual(sent.tools, ())
        self.assertEqual(len(sent.messages[1].images), 1)
        self.assertEqual(sent.messages[1].images[0].source_ref, "schematic:page-1")
        self.assertNotIn("png-image-payload", repr(result))

    def test_default_accepted_registry_has_no_unmeasured_vision_route_and_no_provider_call(self) -> None:
        provider = FakeVisionProvider({"summary": "must not run", "observations": []})
        worker = VisionWorker(
            provider=provider,
            router=DeterministicModelRouter(accepted_registry()),
        )
        with self.assertRaises(VisionRoutingError):
            worker.observe(request())
        self.assertEqual(provider.calls, [])

    def test_unknown_source_ref_in_model_output_fails_closed(self) -> None:
        provider = FakeVisionProvider(
            {
                "summary": "bad source",
                "observations": [
                    {
                        "source_refs": ["not-supplied"],
                        "kind": "general",
                        "statement": "Must be rejected.",
                    }
                ],
            }
        )
        worker = VisionWorker(provider=provider, router=qualified_router())
        with self.assertRaises(VisionProtocolError):
            worker.observe(request())

    def test_response_provider_identity_mismatch_fails_closed(self) -> None:
        provider = FakeVisionProvider(
            {"summary": "provider mismatch", "observations": []},
            response_provider="unexpected-provider",
        )
        worker = VisionWorker(provider=provider, router=qualified_router())
        with self.assertRaises(VisionProtocolError):
            worker.observe(request())

    def test_tool_call_from_vision_provider_is_rejected(self) -> None:
        provider = FakeVisionProvider(
            {"summary": "bad tool", "observations": []},
            tool_calls=(ModelToolCall(name="read_repository", arguments={"path": "x"}),),
        )
        worker = VisionWorker(provider=provider, router=qualified_router())
        with self.assertRaises(VisionProtocolError):
            worker.observe(request())

    def test_image_budget_rejects_before_provider_call(self) -> None:
        provider = FakeVisionProvider({"summary": "must not run", "observations": []})
        worker = VisionWorker(
            provider=provider,
            router=qualified_router(),
            max_total_image_bytes=3,
        )
        with self.assertRaises(VisionBudgetError):
            worker.observe(request(b"\x89PNG\r\n\x1a\n1234"))
        self.assertEqual(provider.calls, [])

    def test_malformed_structured_output_fails_closed(self) -> None:
        provider = FakeVisionProvider(
            {
                "summary": "missing observation statement",
                "observations": [{"source_refs": ["schematic:page-1"], "kind": "x"}],
            }
        )
        worker = VisionWorker(provider=provider, router=qualified_router())
        with self.assertRaises(VisionProtocolError):
            worker.observe(request())


if __name__ == "__main__":
    unittest.main()
