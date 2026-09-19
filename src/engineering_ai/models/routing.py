"""Evidence-backed model capability registry and deterministic routing.

Gate 009 intentionally performs no model/provider/tool execution. It only selects
an evidence-qualified model configuration for an explicit task class. The
deterministic Supervisor remains the authority that may consume a route.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ModelTaskClass(str, Enum):
    GENERAL_PLANNING = "GENERAL_PLANNING"
    CODE_REPOSITORY = "CODE_REPOSITORY"
    BASELINE_REASONING = "BASELINE_REASONING"


class RouteStatus(str, Enum):
    ROUTE = "ROUTE"
    NO_ROUTE = "NO_ROUTE"


@dataclass(frozen=True)
class ModelCapability:
    model: str
    provider: str
    task_classes: tuple[ModelTaskClass, ...]
    qualification: str
    max_qualified_context_tokens: int
    max_qualified_output_tokens: int
    reasoning_effort: str | None
    supports_native_tool_proposals: bool
    limitations: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    priority: int = 100

    def __post_init__(self) -> None:
        if not self.model.strip():
            raise ValueError("model must be non-empty")
        if not self.provider.strip():
            raise ValueError("provider must be non-empty")
        if not self.task_classes:
            raise ValueError("task_classes must be non-empty")
        if len(set(self.task_classes)) != len(self.task_classes):
            raise ValueError("task_classes must be unique")
        if self.max_qualified_context_tokens <= 0:
            raise ValueError("max_qualified_context_tokens must be positive")
        if self.max_qualified_output_tokens <= 0:
            raise ValueError("max_qualified_output_tokens must be positive")
        if self.priority < 0:
            raise ValueError("priority must be non-negative")


@dataclass(frozen=True)
class RouteRequest:
    task_class: ModelTaskClass
    context_tokens: int = 8192
    max_output_tokens: int = 2048
    requires_native_tool_proposals: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.task_class, ModelTaskClass):
            raise ValueError("task_class must be an explicit ModelTaskClass")
        if self.context_tokens <= 0:
            raise ValueError("context_tokens must be positive")
        if self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")


@dataclass(frozen=True)
class RouteDecision:
    status: RouteStatus
    task_class: ModelTaskClass
    model: str | None
    provider: str | None
    reasoning_effort: str | None
    evidence_refs: tuple[str, ...]
    considered_models: tuple[str, ...]
    reason: str

    @property
    def routed(self) -> bool:
        return self.status is RouteStatus.ROUTE


class ModelCapabilityRegistry:
    """Immutable evidence-backed registry."""

    def __init__(self, entries: Iterable[ModelCapability]) -> None:
        ordered = tuple(entries)
        if not ordered:
            raise ValueError("registry must contain at least one model capability")
        keys = [(entry.provider, entry.model) for entry in ordered]
        if len(set(keys)) != len(keys):
            raise ValueError("registry model/provider identities must be unique")
        self._entries = ordered

    @property
    def entries(self) -> tuple[ModelCapability, ...]:
        return self._entries

    def candidates(self, task_class: ModelTaskClass) -> tuple[ModelCapability, ...]:
        if not isinstance(task_class, ModelTaskClass):
            raise ValueError("task_class must be an explicit ModelTaskClass")
        matches = [entry for entry in self._entries if task_class in entry.task_classes]
        return tuple(sorted(matches, key=lambda item: (item.priority, item.model)))


class DeterministicModelRouter:
    """Pure deterministic capability matcher; never calls models or tools."""

    def __init__(self, registry: ModelCapabilityRegistry) -> None:
        self._registry = registry

    def route(self, request: RouteRequest) -> RouteDecision:
        candidates = self._registry.candidates(request.task_class)
        considered = tuple(entry.model for entry in candidates)
        rejected: list[str] = []

        for entry in candidates:
            reasons: list[str] = []
            if request.context_tokens > entry.max_qualified_context_tokens:
                reasons.append(
                    "context exceeds qualified limit "
                    f"{entry.max_qualified_context_tokens}"
                )
            if request.max_output_tokens > entry.max_qualified_output_tokens:
                reasons.append(
                    "output exceeds qualified limit "
                    f"{entry.max_qualified_output_tokens}"
                )
            if (
                request.requires_native_tool_proposals
                and not entry.supports_native_tool_proposals
            ):
                reasons.append("native tool proposals not qualified")

            if reasons:
                rejected.append(f"{entry.model}: " + "; ".join(reasons))
                continue

            return RouteDecision(
                status=RouteStatus.ROUTE,
                task_class=request.task_class,
                model=entry.model,
                provider=entry.provider,
                reasoning_effort=entry.reasoning_effort,
                evidence_refs=entry.evidence_refs,
                considered_models=considered,
                reason=f"matched evidence-qualified capability: {entry.qualification}",
            )

        detail = "; ".join(rejected) if rejected else "no qualified candidates"
        return RouteDecision(
            status=RouteStatus.NO_ROUTE,
            task_class=request.task_class,
            model=None,
            provider=None,
            reasoning_effort=None,
            evidence_refs=(),
            considered_models=considered,
            reason=detail,
        )


def accepted_registry() -> ModelCapabilityRegistry:
    """Registry constructed only from accepted Gates 005, 006 and 008 evidence."""

    return ModelCapabilityRegistry(
        (
            ModelCapability(
                model="qwen3.5:9b",
                provider="ollama",
                task_classes=(ModelTaskClass.GENERAL_PLANNING,),
                qualification="QUALIFIED_GENERAL_PLANNER",
                max_qualified_context_tokens=8192,
                max_qualified_output_tokens=2048,
                reasoning_effort="none",
                supports_native_tool_proposals=True,
                evidence_refs=("docs/evidence/gate008/qualification.md",),
                priority=10,
            ),
            ModelCapability(
                model="qwen2.5-coder:7b-instruct",
                provider="ollama",
                task_classes=(ModelTaskClass.CODE_REPOSITORY,),
                qualification="QUALIFIED_WITH_LIMITATIONS_CODE_REPOSITORY",
                max_qualified_context_tokens=8192,
                max_qualified_output_tokens=2048,
                reasoning_effort=None,
                supports_native_tool_proposals=False,
                limitations=(
                    "NO_NATIVE_TOOL_PROPOSALS_UNDER_CURRENT_OLLAMA_CONTRACT",
                ),
                evidence_refs=("docs/evidence/gate008/qualification.md",),
                priority=10,
            ),
            ModelCapability(
                model="gpt-oss:20b",
                provider="ollama",
                task_classes=(ModelTaskClass.BASELINE_REASONING,),
                qualification="ACCEPTED_BASELINE_RUNTIME_VALIDATED",
                max_qualified_context_tokens=8192,
                max_qualified_output_tokens=2048,
                reasoning_effort="medium",
                supports_native_tool_proposals=True,
                evidence_refs=(
                    "docs/evidence/gate005/model-selection.md",
                    "docs/evidence/gate006/runtime-smoke.md",
                ),
                priority=10,
            ),
        )
    )
