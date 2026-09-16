"""Replaceable model-provider protocol."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from engineering_ai.models.types import ModelRequest, ModelResponse


class ModelProviderError(RuntimeError):
    """Base error for local model-provider failures."""


class ModelProviderUnavailable(ModelProviderError):
    """Raised when the configured runtime is unreachable or unavailable."""


class ModelProviderProtocolError(ModelProviderError):
    """Raised when the runtime returns malformed or unexpected data."""


class ModelProvider(Protocol):
    """Stable boundary used by the Supervisor/agent layers.

    Implementations may speak to Ollama, llama.cpp, or another local runtime,
    but callers must not depend on provider-specific wire formats.
    """

    @property
    def provider_name(self) -> str:
        ...

    def runtime_version(self) -> str | None:
        ...

    def runtime_diagnostics(self) -> Mapping[str, Any]:
        """Return non-authoritative runtime/resource observations for evidence."""
        ...

    def chat(self, request: ModelRequest, *, timeout_seconds: float = 300.0) -> ModelResponse:
        ...
