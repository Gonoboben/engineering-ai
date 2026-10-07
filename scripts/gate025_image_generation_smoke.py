from __future__ import annotations

import json
import struct
import tempfile
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
from engineering_ai.tools import PngArtifactPublisher


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def load_fixture(name: str) -> dict:
    with (FIXTURES / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind)
    crc = zlib.crc32(payload, crc) & 0xFFFFFFFF
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", crc)
    )


def png(width: int = 64, height: int = 64) -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + (b"\x00\x00\x00" * width) for _ in range(height))
    return (
        signature
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class FakeImageProvider:
    provider_name = "fake-image"
    local_only = True

    def __init__(self, *, data: bytes | None = None) -> None:
        self.data = data or png()
        self.calls = []

    def generate(self, request, *, timeout_seconds=300.0):
        self.calls.append((request, timeout_seconds))
        return ImageGenerationProviderResponse(
            provider=self.provider_name,
            model=request.model,
            media_type="image/png",
            data=self.data,
        )


def qualified_router() -> DeterministicModelRouter:
    capability = ModelCapability(
        model="image-qualified-smoke",
        provider="fake-image",
        task_classes=(ModelTaskClass.IMAGE_GENERATION,),
        qualification="QUALIFIED_SYNTHETIC_BOUNDARY_ONLY",
        max_qualified_context_tokens=8192,
        max_qualified_output_tokens=2048,
        reasoning_effort=None,
        supports_native_tool_proposals=False,
        supports_image_generation=True,
        evidence_refs=("ev-gate025-synthetic-boundary",),
        priority=10,
    )
    return DeterministicModelRouter(ModelCapabilityRegistry((capability,)))


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
    state["next_admissible_action"] = "validate concept-image proposal"
    autonomous = state["effective_permissions"]["autonomous"]
    if allow_propose_patch and "propose_patch" not in autonomous:
        autonomous.append("propose_patch")
    if not allow_propose_patch and "propose_patch" in autonomous:
        autonomous.remove("propose_patch")
    return state


def make_job() -> dict:
    job = load_fixture("valid_job.json")
    job["job_id"] = "gate-025-image-smoke"
    job["gate_id"] = "025"
    job["objective"] = "Exercise non-authoritative concept image boundary"
    job["scope"] = ["text-to-image concept generation", "PNG validation"]
    job["out_of_scope"] = ["engineering drawing", "fabrication", "release"]
    job["requested_actions"] = ["propose_patch"]
    job["required_validators"] = []
    job["retry_limit"] = 1
    job["attempts"] = 0
    job["status"] = "QUEUED"
    job["blocker"] = None
    return job


def request(path: str = "concepts/gate025-smoke.png") -> ImageGenerationWorkerRequest:
    return ImageGenerationWorkerRequest(
        project_id="engineering-ai",
        task_id="gate025-smoke",
        prompt="Synthetic non-authoritative engineering concept visualization.",
        width=64,
        height=64,
        seed=25,
        output_relative_path=path,
        timeout_seconds=30,
    )


def main() -> int:
    unqualified_provider = FakeImageProvider()
    with tempfile.TemporaryDirectory() as tmp:
        worker = ImageGenerationWorker(
            provider=unqualified_provider,
            router=DeterministicModelRouter(accepted_registry()),
            publisher=PngArtifactPublisher(tmp),
        )
        no_route = False
        try:
            worker.generate_proposal(
                request(),
                supervisor=Supervisor(
                    policy=make_policy(),
                    state=make_state(allow_propose_patch=True),
                ),
                job=make_job(),
            )
        except ImageGenerationRoutingError:
            no_route = True
        assert no_route
        assert unqualified_provider.calls == []

    denied_provider = FakeImageProvider()
    with tempfile.TemporaryDirectory() as tmp:
        worker = ImageGenerationWorker(
            provider=denied_provider,
            router=qualified_router(),
            publisher=PngArtifactPublisher(tmp),
        )
        denied = worker.generate_proposal(
            request(),
            supervisor=Supervisor(
                policy=make_policy(),
                state=make_state(allow_propose_patch=False),
            ),
            job=make_job(),
        )
        assert denied.decision.decision is Decision.DENY
        assert denied.tool_called is False
        assert denied_provider.calls == []
        assert not (Path(tmp) / "concepts" / "gate025-smoke.png").exists()

    allowed_provider = FakeImageProvider()
    with tempfile.TemporaryDirectory() as tmp:
        worker = ImageGenerationWorker(
            provider=allowed_provider,
            router=qualified_router(),
            publisher=PngArtifactPublisher(tmp),
        )
        allowed = worker.generate_proposal(
            request(),
            supervisor=Supervisor(
                policy=make_policy(),
                state=make_state(allow_propose_patch=True),
            ),
            job=make_job(),
        )
        target = Path(tmp) / "concepts" / "gate025-smoke.png"
        assert allowed.decision.decision is Decision.ALLOW
        assert allowed.tool_called is True
        assert allowed.outcome_ok is True
        assert len(allowed_provider.calls) == 1
        assert target.is_file()
        assert allowed.artifact is not None
        assert allowed.artifact.width == 64
        assert allowed.artifact.height == 64
        assert len(allowed.artifact.sha256) == 64
        assert allowed.authority == "ADVISORY_CONCEPT_ONLY"
        assert allowed.evidence_eligible is False
        assert allowed.engineering_drawing is False
        assert allowed.physical_validation == "PHYSICAL_NOT_EXECUTED"

    mismatch_provider = FakeImageProvider(data=png(128, 64))
    with tempfile.TemporaryDirectory() as tmp:
        worker = ImageGenerationWorker(
            provider=mismatch_provider,
            router=qualified_router(),
            publisher=PngArtifactPublisher(tmp),
        )
        mismatch = worker.generate_proposal(
            request(),
            supervisor=Supervisor(
                policy=make_policy(),
                state=make_state(allow_propose_patch=True),
            ),
            job=make_job(),
        )
        assert mismatch.outcome_ok is False
        assert mismatch.failure_class == "IMAGE_PNG_VALIDATION_REJECTED"
        assert not (Path(tmp) / "concepts" / "gate025-smoke.png").exists()

    payload = {
        "gate": "025",
        "state": "PASS_NON_AUTHORITATIVE_IMAGE_GENERATION_BOUNDARY",
        "unmeasured_default_image_generation_route": "NO_ROUTE",
        "provider_calls_before_qualified_route": 0,
        "policy_denial_provider_calls": len(denied_provider.calls),
        "qualified_synthetic_provider_calls": len(allowed_provider.calls),
        "dimension_mismatch_blocked": True,
        "dimension_mismatch_artifact_published": False,
        "artifact_authority": "ADVISORY_CONCEPT_ONLY",
        "evidence_eligible": False,
        "engineering_drawing": False,
        "external_network": False,
        "automatic_evidence_promotion": False,
        "production_image_model_qualified": False,
        "fabrication_authority": False,
        "release_authority": False,
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
