from __future__ import annotations

import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from engineering_ai.models import (
    DeterministicModelRouter,
    ImageGenerationProviderResponse,
    ModelCapability,
    ModelCapabilityRegistry,
    ModelTaskClass,
    accepted_registry,
)
from engineering_ai.supervisor import (
    Decision,
    ImageGenerationRoutingError,
    ImageGenerationWorker,
    ImageGenerationWorkerRequest,
    Supervisor,
)
from engineering_ai.tools import (
    PngArtifactPublisher,
    PngValidationError,
    ToolAccessError,
    validate_png,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def load_fixture(name: str) -> dict:
    with (FIXTURES / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind)
    crc = zlib.crc32(payload, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)


def make_png(width: int = 64, height: int = 64) -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + (b"\x00\x00\x00" * width) for _ in range(height))
    return (
        signature
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", zlib.compress(raw))
        + png_chunk(b"IEND", b"")
    )


def qualified_router() -> DeterministicModelRouter:
    capability = ModelCapability(
        model="image-qualified-synthetic",
        provider="fake-image",
        task_classes=(ModelTaskClass.IMAGE_GENERATION,),
        qualification="QUALIFIED_IMAGE_GENERATION_SYNTHETIC_BOUNDARY",
        max_qualified_context_tokens=8192,
        max_qualified_output_tokens=2048,
        reasoning_effort=None,
        supports_native_tool_proposals=False,
        supports_image_generation=True,
        evidence_refs=("ev-gate025-image-boundary",),
        priority=10,
    )
    return DeterministicModelRouter(ModelCapabilityRegistry((capability,)))


class FakeImageProvider:
    provider_name = "fake-image"
    local_only = True

    def __init__(
        self,
        *,
        data: bytes | None = None,
        response_provider: str = "fake-image",
        response_model: str | None = None,
    ) -> None:
        self.data = data or make_png()
        self.response_provider = response_provider
        self.response_model = response_model
        self.calls = []

    def generate(self, request, *, timeout_seconds=300.0):
        self.calls.append((request, timeout_seconds))
        return ImageGenerationProviderResponse(
            provider=self.response_provider,
            model=self.response_model or request.model,
            media_type="image/png",
            data=self.data,
        )


def make_policy() -> dict:
    policy = load_fixture("valid_policy.json")
    policy["mandatory_validators"] = []
    return policy


def make_state(*, allow_propose_patch: bool) -> dict:
    state = load_fixture("valid_state.json")
    state["current_gate"] = "025"
    state["active_job_id"] = None
    state["repository_ref"] = {
        "branch": "gate-025-non-authoritative-image-generation-worker",
        "head_sha": "99a8e216dc2c8ec7b98c445f0e1909479bff6b52",
    }
    state["pending_checks"] = []
    state["blockers"] = []
    state["next_admissible_action"] = "validate image-generation proposal"
    autonomous = state["effective_permissions"]["autonomous"]
    if allow_propose_patch and "propose_patch" not in autonomous:
        autonomous.append("propose_patch")
    if not allow_propose_patch and "propose_patch" in autonomous:
        autonomous.remove("propose_patch")
    return state


def make_job() -> dict:
    job = load_fixture("valid_job.json")
    job["job_id"] = "gate-025-image-test"
    job["gate_id"] = "025"
    job["objective"] = "Generate one non-authoritative concept image"
    job["scope"] = ["text-to-image concept generation", "deterministic PNG validation"]
    job["out_of_scope"] = ["engineering drawing", "fabrication", "release"]
    job["requested_actions"] = ["propose_patch"]
    job["required_validators"] = []
    job["retry_limit"] = 1
    job["attempts"] = 0
    job["status"] = "QUEUED"
    job["blocker"] = None
    return job


def worker_request(path: str = "concepts/gate025.png") -> ImageGenerationWorkerRequest:
    return ImageGenerationWorkerRequest(
        project_id="engineering-ai",
        task_id="gate025-image",
        prompt="Conceptual enclosure form; non-authoritative visual aid only.",
        width=64,
        height=64,
        seed=25,
        output_relative_path=path,
        timeout_seconds=30,
    )


class PngValidationTests(unittest.TestCase):
    def test_valid_png_hash_dimensions_and_crc(self) -> None:
        data = make_png(64, 64)
        info = validate_png(data, expected_width=64, expected_height=64)
        self.assertEqual(info.width, 64)
        self.assertEqual(info.height, 64)
        self.assertEqual(info.size_bytes, len(data))
        self.assertEqual(len(info.sha256), 64)

    def test_crc_corruption_and_dimension_mismatch_fail_closed(self) -> None:
        data = bytearray(make_png())
        data[-1] ^= 1
        with self.assertRaises(PngValidationError):
            validate_png(bytes(data))
        with self.assertRaises(PngValidationError):
            validate_png(make_png(64, 64), expected_width=128, expected_height=64)

    def test_trailing_data_after_iend_fails_closed(self) -> None:
        with self.assertRaises(PngValidationError):
            validate_png(make_png() + b"trailing")


class ImageGenerationWorkerTests(unittest.TestCase):
    def test_default_registry_has_no_unmeasured_route_and_provider_is_not_called(self) -> None:
        provider = FakeImageProvider()
        with tempfile.TemporaryDirectory() as tmp:
            worker = ImageGenerationWorker(
                provider=provider,
                router=DeterministicModelRouter(accepted_registry()),
                publisher=PngArtifactPublisher(tmp),
            )
            with self.assertRaises(ImageGenerationRoutingError):
                worker.generate_proposal(
                    worker_request(),
                    supervisor=Supervisor(
                        policy=make_policy(),
                        state=make_state(allow_propose_patch=True),
                    ),
                    job=make_job(),
                )
        self.assertEqual(provider.calls, [])

    def test_policy_denial_makes_zero_provider_calls_and_no_artifact(self) -> None:
        provider = FakeImageProvider()
        with tempfile.TemporaryDirectory() as tmp:
            worker = ImageGenerationWorker(
                provider=provider,
                router=qualified_router(),
                publisher=PngArtifactPublisher(tmp),
            )
            result = worker.generate_proposal(
                worker_request(),
                supervisor=Supervisor(
                    policy=make_policy(),
                    state=make_state(allow_propose_patch=False),
                ),
                job=make_job(),
            )
            self.assertEqual(result.decision.decision, Decision.DENY)
            self.assertFalse(result.tool_called)
            self.assertFalse(result.outcome_ok)
            self.assertEqual(provider.calls, [])
            self.assertFalse((Path(tmp) / "concepts" / "gate025.png").exists())

    def test_valid_generation_is_non_authoritative_concept_only(self) -> None:
        provider = FakeImageProvider()
        with tempfile.TemporaryDirectory() as tmp:
            worker = ImageGenerationWorker(
                provider=provider,
                router=qualified_router(),
                publisher=PngArtifactPublisher(tmp),
            )
            result = worker.generate_proposal(
                worker_request(),
                supervisor=Supervisor(
                    policy=make_policy(),
                    state=make_state(allow_propose_patch=True),
                ),
                job=make_job(),
            )
            target = Path(tmp) / "concepts" / "gate025.png"
            self.assertEqual(result.decision.decision, Decision.ALLOW)
            self.assertTrue(result.tool_called)
            self.assertTrue(result.outcome_ok)
            self.assertEqual(len(provider.calls), 1)
            self.assertTrue(target.is_file())
            self.assertIsNotNone(result.artifact)
            assert result.artifact is not None
            self.assertEqual(result.artifact.width, 64)
            self.assertEqual(result.artifact.height, 64)
            self.assertEqual(len(result.artifact.sha256), 64)
            self.assertEqual(result.route_evidence_refs, ("ev-gate025-image-boundary",))
            self.assertEqual(result.authority, "ADVISORY_CONCEPT_ONLY")
            self.assertFalse(result.evidence_eligible)
            self.assertFalse(result.engineering_drawing)
            self.assertEqual(result.physical_validation, "PHYSICAL_NOT_EXECUTED")
            self.assertNotIn(worker_request().prompt, repr(result))

    def test_provider_identity_mismatch_fails_without_publication(self) -> None:
        provider = FakeImageProvider(response_provider="wrong-provider")
        with tempfile.TemporaryDirectory() as tmp:
            worker = ImageGenerationWorker(
                provider=provider,
                router=qualified_router(),
                publisher=PngArtifactPublisher(tmp),
            )
            result = worker.generate_proposal(
                worker_request(),
                supervisor=Supervisor(
                    policy=make_policy(),
                    state=make_state(allow_propose_patch=True),
                ),
                job=make_job(),
            )
            self.assertFalse(result.outcome_ok)
            self.assertEqual(result.failure_class, "IMAGE_PROVIDER_PROTOCOL_REJECTED")
            self.assertFalse((Path(tmp) / "concepts" / "gate025.png").exists())

    def test_dimension_mismatch_fails_without_publication(self) -> None:
        provider = FakeImageProvider(data=make_png(128, 64))
        with tempfile.TemporaryDirectory() as tmp:
            worker = ImageGenerationWorker(
                provider=provider,
                router=qualified_router(),
                publisher=PngArtifactPublisher(tmp),
            )
            result = worker.generate_proposal(
                worker_request(),
                supervisor=Supervisor(
                    policy=make_policy(),
                    state=make_state(allow_propose_patch=True),
                ),
                job=make_job(),
            )
            self.assertFalse(result.outcome_ok)
            self.assertEqual(result.failure_class, "IMAGE_PNG_VALIDATION_REJECTED")
            self.assertFalse((Path(tmp) / "concepts" / "gate025.png").exists())

    def test_path_escape_fails_before_route_or_provider(self) -> None:
        provider = FakeImageProvider()
        with tempfile.TemporaryDirectory() as tmp:
            worker = ImageGenerationWorker(
                provider=provider,
                router=qualified_router(),
                publisher=PngArtifactPublisher(tmp),
            )
            with self.assertRaises(ToolAccessError):
                worker.generate_proposal(
                    worker_request("../escape.png"),
                    supervisor=Supervisor(
                        policy=make_policy(),
                        state=make_state(allow_propose_patch=True),
                    ),
                    job=make_job(),
                )
            self.assertEqual(provider.calls, [])


if __name__ == "__main__":
    unittest.main()
