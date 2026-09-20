"""Bounded provenance-preserving Vision worker.

Gate 023 treats visual model output as advisory observation only. Image bytes are
explicit transient inputs; the worker has no filesystem, URL, shell, Git, tool
or evidence-promotion authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping

from jsonschema import Draft202012Validator, ValidationError

from engineering_ai.models import (
    DeterministicModelRouter,
    ModelImageAttachment,
    ModelMessage,
    ModelProvider,
    ModelRequest,
    ModelTaskClass,
    RouteRequest,
    RouteStatus,
)


VISION_RESPONSE_SCHEMA: Mapping[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "observations"],
    "properties": {
        "summary": {"type": "string", "minLength": 1, "maxLength": 8192},
        "observations": {
            "type": "array",
            "maxItems": 64,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["source_refs", "kind", "statement"],
                "properties": {
                    "source_refs": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 8,
                        "uniqueItems": True,
                        "items": {"type": "string", "minLength": 1, "maxLength": 512},
                    },
                    "kind": {"type": "string", "minLength": 1, "maxLength": 64},
                    "statement": {"type": "string", "minLength": 1, "maxLength": 4096},
                },
            },
        },
    },
}


class VisionWorkerError(RuntimeError):
    """Base fail-closed Vision worker error."""


class VisionRoutingError(VisionWorkerError):
    """Raised when there is no evidence-qualified Vision route."""


class VisionBudgetError(VisionWorkerError):
    """Raised when explicit Vision input exceeds bounded request limits."""


class VisionProtocolError(VisionWorkerError):
    """Raised when model output violates the Vision contract."""


class VisionAuthority(str, Enum):
    ADVISORY = "ADVISORY"


@dataclass(frozen=True)
class VisionInput:
    source_ref: str
    media_type: str
    data: bytes

    def __post_init__(self) -> None:
        attachment = self.as_attachment()
        object.__setattr__(self, "source_ref", attachment.source_ref)

    def as_attachment(self) -> ModelImageAttachment:
        return ModelImageAttachment(
            source_ref=self.source_ref,
            media_type=self.media_type,
            data=self.data,
        )

    @property
    def content_sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()

    @property
    def size_bytes(self) -> int:
        return len(self.data)


@dataclass(frozen=True)
class VisionSourceDescriptor:
    source_ref: str
    media_type: str
    size_bytes: int
    content_sha256: str


@dataclass(frozen=True)
class VisionAdvisoryObservation:
    source_refs: tuple[str, ...]
    kind: str
    statement: str


@dataclass(frozen=True)
class VisionWorkerRequest:
    project_id: str
    task_id: str
    prompt: str
    images: tuple[VisionInput, ...]
    context_tokens: int = 8192
    max_output_tokens: int = 2048

    def __post_init__(self) -> None:
        if not self.project_id.strip():
            raise ValueError("project_id must be non-empty")
        if not self.task_id.strip():
            raise ValueError("task_id must be non-empty")
        if not self.prompt.strip():
            raise ValueError("prompt must be non-empty")
        if len(self.prompt) > 12000:
            raise ValueError("prompt exceeds 12000 character bound")
        images = tuple(self.images)
        if not images:
            raise ValueError("Vision request requires at least one image")
        if len({item.source_ref for item in images}) != len(images):
            raise ValueError("Vision image source_ref values must be unique")
        if self.context_tokens <= 0 or self.max_output_tokens <= 0:
            raise ValueError("token budgets must be positive")
        object.__setattr__(self, "images", images)


@dataclass(frozen=True)
class VisionWorkerResult:
    project_id: str
    task_id: str
    provider: str
    model: str
    summary: str
    observations: tuple[VisionAdvisoryObservation, ...]
    sources: tuple[VisionSourceDescriptor, ...]
    route_evidence_refs: tuple[str, ...]
    response_sha256: str
    authority: VisionAuthority = VisionAuthority.ADVISORY
    evidence_eligible: bool = False
    physical_validation: str = "PHYSICAL_NOT_EXECUTED"


class VisionWorker:
    """Execute one bounded routed Vision request through a replaceable provider."""

    def __init__(
        self,
        *,
        provider: ModelProvider,
        router: DeterministicModelRouter,
        max_images: int = 8,
        max_total_image_bytes: int = 32 * 1024 * 1024,
    ) -> None:
        if max_images <= 0:
            raise ValueError("max_images must be positive")
        if max_total_image_bytes <= 0:
            raise ValueError("max_total_image_bytes must be positive")
        self._provider = provider
        self._router = router
        self._max_images = max_images
        self._max_total_image_bytes = max_total_image_bytes

    def observe(
        self,
        request: VisionWorkerRequest,
        *,
        timeout_seconds: float = 300.0,
    ) -> VisionWorkerResult:
        if timeout_seconds <= 0 or timeout_seconds > 300:
            raise VisionBudgetError("timeout_seconds must be in (0, 300]")
        if len(request.images) > self._max_images:
            raise VisionBudgetError("image count exceeds Vision worker bound")
        total_bytes = sum(item.size_bytes for item in request.images)
        if total_bytes > self._max_total_image_bytes:
            raise VisionBudgetError("total image bytes exceed Vision worker bound")

        route = self._router.route(
            RouteRequest(
                task_class=ModelTaskClass.VISION_ANALYSIS,
                context_tokens=request.context_tokens,
                max_output_tokens=request.max_output_tokens,
                requires_vision_inputs=True,
            )
        )
        if route.status is not RouteStatus.ROUTE or route.model is None or route.provider is None:
            raise VisionRoutingError(f"no evidence-qualified Vision route: {route.reason}")
        if not route.evidence_refs:
            raise VisionRoutingError("Vision route must carry qualification evidence refs")
        if route.provider != self._provider.provider_name:
            raise VisionRoutingError("routed provider does not match configured Vision provider")

        attachments = tuple(item.as_attachment() for item in request.images)
        manifest_lines = [
            (
                f"{index}. source_ref={item.source_ref}; media_type={item.media_type}; "
                f"size_bytes={item.size_bytes}; sha256={item.content_sha256}"
            )
            for index, item in enumerate(attachments, start=1)
        ]
        user_content = (
            request.prompt.strip()
            + "\n\nExplicit image source manifest:\n"
            + "\n".join(manifest_lines)
            + "\n\nReturn only observations grounded in the supplied source_refs."
        )
        model_request = ModelRequest(
            model=route.model,
            messages=(
                ModelMessage(
                    role="system",
                    content=(
                        "You are a bounded engineering Vision worker. Return JSON matching "
                        "the supplied schema. Every observation must cite one or more exact "
                        "source_refs from the explicit manifest. Your output is ADVISORY only; "
                        "do not claim deterministic or physical validation and do not request "
                        "or invoke tools."
                    ),
                ),
                ModelMessage(
                    role="user",
                    content=user_content,
                    images=attachments,
                ),
            ),
            tools=(),
            response_schema=VISION_RESPONSE_SCHEMA,
            temperature=0.0,
            seed=0,
            context_tokens=request.context_tokens,
            max_output_tokens=request.max_output_tokens,
            reasoning_effort=route.reasoning_effort,
            keep_alive="0",
        )
        response = self._provider.chat(model_request, timeout_seconds=timeout_seconds)
        if response.tool_calls:
            raise VisionProtocolError("Vision provider returned tool calls; tool surface is forbidden")
        if response.model != route.model:
            raise VisionProtocolError("Vision provider response model does not match routed model")

        try:
            payload = json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise VisionProtocolError("Vision provider returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise VisionProtocolError("Vision provider output must be a JSON object")
        try:
            Draft202012Validator(VISION_RESPONSE_SCHEMA).validate(payload)
        except ValidationError as exc:
            raise VisionProtocolError("Vision provider output failed schema validation") from exc

        allowed_refs = {item.source_ref for item in attachments}
        observations: list[VisionAdvisoryObservation] = []
        for raw in payload["observations"]:
            refs = tuple(raw["source_refs"])
            if not set(refs).issubset(allowed_refs):
                raise VisionProtocolError("Vision observation referenced an unknown source_ref")
            observations.append(
                VisionAdvisoryObservation(
                    source_refs=refs,
                    kind=raw["kind"],
                    statement=raw["statement"],
                )
            )

        sources = tuple(
            VisionSourceDescriptor(
                source_ref=item.source_ref,
                media_type=item.media_type,
                size_bytes=item.size_bytes,
                content_sha256=item.content_sha256,
            )
            for item in attachments
        )
        return VisionWorkerResult(
            project_id=request.project_id,
            task_id=request.task_id,
            provider=response.provider,
            model=response.model,
            summary=payload["summary"],
            observations=tuple(observations),
            sources=sources,
            route_evidence_refs=route.evidence_refs,
            response_sha256=hashlib.sha256(response.content.encode("utf-8")).hexdigest(),
        )
