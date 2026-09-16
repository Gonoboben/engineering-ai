"""Replaceable model-provider interfaces."""

from engineering_ai.models.benchmark import BenchmarkCase, BenchmarkRecord, run_benchmark
from engineering_ai.models.ollama import OllamaProvider
from engineering_ai.models.protocol import (
    ModelProvider,
    ModelProviderError,
    ModelProviderProtocolError,
    ModelProviderUnavailable,
)
from engineering_ai.models.types import (
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
    "OllamaProvider",
    "run_benchmark",
]
