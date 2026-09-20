"""Replaceable model-provider interfaces."""

from engineering_ai.models.benchmark import BenchmarkCase, BenchmarkRecord, run_benchmark
from engineering_ai.models.image_generation import (
    ImageGenerationProvider,
    ImageGenerationProviderRequest,
    ImageGenerationProviderResponse,
)
from engineering_ai.models.ollama import OllamaProvider
from engineering_ai.models.routing import (
    DeterministicModelRouter,
    ModelCapability,
    ModelCapabilityRegistry,
    ModelTaskClass,
    RouteDecision,
    RouteRequest,
    RouteStatus,
    accepted_registry,
)
from engineering_ai.models.protocol import (
    ModelProvider,
    ModelProviderError,
    ModelProviderProtocolError,
    ModelProviderUnavailable,
)
from engineering_ai.models.types import (
    ModelImageAttachment,
    ModelMessage,
    ModelMetrics,
    ModelRequest,
    ModelResponse,
    ModelToolCall,
    ModelToolSpec,
)

__all__ = [
    "BenchmarkCase",
    "BenchmarkRecord",
    "DeterministicModelRouter",
    "ImageGenerationProvider",
    "ImageGenerationProviderRequest",
    "ImageGenerationProviderResponse",
    "ModelCapability",
    "ModelCapabilityRegistry",
    "ModelTaskClass",
    "ModelImageAttachment",
    "ModelMessage",
    "ModelMetrics",
    "ModelProvider",
    "ModelProviderError",
    "ModelProviderProtocolError",
    "ModelProviderUnavailable",
    "ModelRequest",
    "ModelResponse",
    "ModelToolCall",
    "ModelToolSpec",
    "RouteDecision",
    "RouteRequest",
    "RouteStatus",
    "OllamaProvider",
    "accepted_registry",
    "run_benchmark",
]
