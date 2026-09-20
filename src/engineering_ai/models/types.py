"""Stable model-provider request/response types.

The Supervisor may ask a provider for model output, but provider responses remain
advisory. Tool calls are returned as proposals and are never executed here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Literal, Mapping, Sequence


Role = Literal["system", "user", "assistant", "tool"]
SUPPORTED_IMAGE_MEDIA_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})


@dataclass(frozen=True)
class ModelImageAttachment:
    """Explicit transient image input with source provenance."""

    source_ref: str
    media_type: str
    data: bytes = field(repr=False)
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        source_ref = self.source_ref.strip()
        if not source_ref or len(source_ref) > 512:
            raise ValueError("image source_ref must be 1..512 characters")
        if any(not ch.isprintable() or ch in "\r\n" for ch in source_ref):
            raise ValueError("image source_ref must not contain control/newline characters")
        if self.media_type not in SUPPORTED_IMAGE_MEDIA_TYPES:
            raise ValueError("unsupported image media_type")
        if not isinstance(self.data, bytes) or not self.data:
            raise ValueError("image data must be non-empty bytes")
        if len(self.data) > 16 * 1024 * 1024:
            raise ValueError("individual image exceeds 16 MiB transport bound")
        if self.media_type == "image/png" and not self.data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("image/png payload has invalid PNG signature")
        if self.media_type == "image/jpeg" and not self.data.startswith(b"\xff\xd8\xff"):
            raise ValueError("image/jpeg payload has invalid JPEG signature")
        if self.media_type == "image/webp" and not (
            len(self.data) >= 12
            and self.data.startswith(b"RIFF")
            and self.data[8:12] == b"WEBP"
        ):
            raise ValueError("image/webp payload has invalid WebP signature")
        object.__setattr__(self, "source_ref", source_ref)
        object.__setattr__(self, "content_sha256", hashlib.sha256(self.data).hexdigest())

    @property
    def size_bytes(self) -> int:
        return len(self.data)


@dataclass(frozen=True)
class ModelMessage:
    role: Role
    content: str
    name: str | None = None
    images: Sequence[ModelImageAttachment] = ()

    def __post_init__(self) -> None:
        images = tuple(self.images)
        if images and self.role != "user":
            raise ValueError("image attachments are accepted only on user messages")
        if not all(isinstance(item, ModelImageAttachment) for item in images):
            raise ValueError("images must contain ModelImageAttachment records")
        object.__setattr__(self, "images", images)


@dataclass(frozen=True)
class ModelToolSpec:
    name: str
    description: str
    parameters: Mapping[str, Any]


@dataclass(frozen=True)
class ModelRequest:
    model: str
    messages: Sequence[ModelMessage]
    tools: Sequence[ModelToolSpec] = ()
    response_schema: Mapping[str, Any] | None = None
    temperature: float = 0.0
    seed: int | None = 0
    context_tokens: int | None = None
    max_output_tokens: int | None = None
    reasoning_effort: Literal["none", "low", "medium", "high"] | None = None
    keep_alive: str | int = "0"


@dataclass(frozen=True)
class ModelToolCall:
    name: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True)
class ModelMetrics:
    total_duration_ns: int | None = None
    load_duration_ns: int | None = None
    prompt_eval_count: int | None = None
    prompt_eval_duration_ns: int | None = None
    eval_count: int | None = None
    eval_duration_ns: int | None = None

    @property
    def output_tokens_per_second(self) -> float | None:
        if not self.eval_count or not self.eval_duration_ns:
            return None
        return self.eval_count / (self.eval_duration_ns / 1_000_000_000)


@dataclass(frozen=True)
class ModelResponse:
    provider: str
    runtime_version: str | None
    model: str
    content: str
    thinking: str = ""
    tool_calls: tuple[ModelToolCall, ...] = ()
    done_reason: str | None = None
    metrics: ModelMetrics = field(default_factory=ModelMetrics)
    raw_metadata: Mapping[str, Any] = field(default_factory=dict)
