"""Supervisor-controlled typed Task Blackboard.

Workers receive read-only views. Model-authored records remain advisory.
Only Supervisor-owned methods may append control/evidence/handoff records.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from engineering_ai.models.routing import (
    ModelTaskClass,
    RouteDecision,
    RouteRequest,
    RouteStatus,
)




class ContextResolutionMode(str, Enum):
    CONTEXT_READY = "CONTEXT_READY"
    DETERMINISTIC_ACQUISITION = "DETERMINISTIC_ACQUISITION"
    TOOL_PLANNER = "TOOL_PLANNER"
    DEEP_ESCALATION = "DEEP_ESCALATION"


@dataclass(frozen=True)
class ContextResolutionDecision:
    mode: ContextResolutionMode
    missing_context_keys: tuple[str, ...]
    route: RouteDecision | None = None


class BlackboardRecordKind(str, Enum):
    TASK_ASSIGNMENT = "TASK_ASSIGNMENT"
    CONTEXT_REQUIREMENT = "CONTEXT_REQUIREMENT"
    MODEL_CLAIM = "MODEL_CLAIM"
    TOOL_PROPOSAL = "TOOL_PROPOSAL"
    DETERMINISTIC_EVIDENCE = "DETERMINISTIC_EVIDENCE"
    HANDOFF = "HANDOFF"
    TERMINAL_STATE = "TERMINAL_STATE"


class BlackboardAuthority(str, Enum):
    SUPERVISOR = "SUPERVISOR"
    MODEL = "MODEL"
    DETERMINISTIC_TOOL = "DETERMINISTIC_TOOL"


class BlackboardValidationClass(str, Enum):
    CONTROL = "CONTROL"
    ADVISORY = "ADVISORY"
    DETERMINISTIC_EVIDENCE = "DETERMINISTIC_EVIDENCE"


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set | frozenset):
        return tuple(sorted((_freeze(item) for item in value), key=repr))
    return value


@dataclass(frozen=True)
class BlackboardRecord:
    record_id: int
    task_id: str
    kind: BlackboardRecordKind
    authority: BlackboardAuthority
    actor_id: str
    validation_class: BlackboardValidationClass
    payload: Mapping[str, Any]
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.record_id <= 0:
            raise ValueError("record_id must be positive")
        if not self.task_id.strip():
            raise ValueError("task_id must be non-empty")
        if not self.actor_id.strip():
            raise ValueError("actor_id must be non-empty")
        object.__setattr__(self, "payload", _freeze(dict(self.payload)))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))


@dataclass(frozen=True)
class BlackboardView:
    task_id: str
    records: tuple[BlackboardRecord, ...]


@dataclass(frozen=True)
class HandoffRequest:
    task_id: str
    target_task_class: ModelTaskClass
    required_context_keys: tuple[str, ...] = ()
    visible_record_ids: tuple[int, ...] = ()
    requires_native_tool_proposals: bool = False
    context_tokens: int = 8192
    max_output_tokens: int = 2048

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must be non-empty")
        if len(set(self.required_context_keys)) != len(self.required_context_keys):
            raise ValueError("required_context_keys must be unique")
        if len(set(self.visible_record_ids)) != len(self.visible_record_ids):
            raise ValueError("visible_record_ids must be unique")


@dataclass(frozen=True)
class HandoffDecision:
    route: RouteDecision
    handoff_record: BlackboardRecord | None
    visible_view: BlackboardView | None
    missing_context_keys: tuple[str, ...] = ()

    @property
    def created(self) -> bool:
        return self.handoff_record is not None


class TaskBlackboard:
    """Append-only ledger. Mutation methods are intended for Supervisor ownership."""

    def __init__(self, *, max_records: int = 1000) -> None:
        if max_records <= 0:
            raise ValueError("max_records must be positive")
        self._max_records = max_records
        self._records: list[BlackboardRecord] = []

    def view(
        self,
        *,
        task_id: str,
        visible_record_ids: Iterable[int] | None = None,
    ) -> BlackboardView:
        allowed = None if visible_record_ids is None else set(visible_record_ids)
        records = tuple(
            record
            for record in self._records
            if record.task_id == task_id
            and (allowed is None or record.record_id in allowed)
        )
        return BlackboardView(task_id=task_id, records=records)

    def context_keys(self, task_id: str) -> frozenset[str]:
        keys: set[str] = set()
        for record in self._records:
            if record.task_id != task_id:
                continue
            if record.kind is not BlackboardRecordKind.DETERMINISTIC_EVIDENCE:
                continue
            provided = record.payload.get("context_keys", ())
            if isinstance(provided, tuple):
                keys.update(str(item) for item in provided)
        return frozenset(keys)

    def _append(
        self,
        *,
        task_id: str,
        kind: BlackboardRecordKind,
        authority: BlackboardAuthority,
        actor_id: str,
        validation_class: BlackboardValidationClass,
        payload: Mapping[str, Any],
        evidence_refs: tuple[str, ...] = (),
    ) -> BlackboardRecord:
        if len(self._records) >= self._max_records:
            raise RuntimeError("blackboard record limit reached")
        if (
            validation_class is BlackboardValidationClass.DETERMINISTIC_EVIDENCE
            and authority is not BlackboardAuthority.DETERMINISTIC_TOOL
        ):
            raise ValueError("deterministic evidence requires deterministic-tool authority")
        if (
            validation_class is BlackboardValidationClass.DETERMINISTIC_EVIDENCE
            and not evidence_refs
        ):
            raise ValueError("deterministic evidence requires evidence_refs")
        if (
            authority is BlackboardAuthority.MODEL
            and validation_class is not BlackboardValidationClass.ADVISORY
        ):
            raise ValueError("model-authored blackboard records must remain advisory")

        record = BlackboardRecord(
            record_id=len(self._records) + 1,
            task_id=task_id,
            kind=kind,
            authority=authority,
            actor_id=actor_id,
            validation_class=validation_class,
            payload=payload,
            evidence_refs=evidence_refs,
        )
        self._records.append(record)
        return record

    # The following append methods are deliberately private to keep the worker
    # surface read-only. Supervisor wrappers are the supported write API.

    def _append_control(
        self,
        *,
        task_id: str,
        kind: BlackboardRecordKind,
        payload: Mapping[str, Any],
    ) -> BlackboardRecord:
        if kind in {
            BlackboardRecordKind.MODEL_CLAIM,
            BlackboardRecordKind.TOOL_PROPOSAL,
            BlackboardRecordKind.DETERMINISTIC_EVIDENCE,
        }:
            raise ValueError("invalid control record kind")
        return self._append(
            task_id=task_id,
            kind=kind,
            authority=BlackboardAuthority.SUPERVISOR,
            actor_id="supervisor",
            validation_class=BlackboardValidationClass.CONTROL,
            payload=payload,
        )

    def _append_model_record(
        self,
        *,
        task_id: str,
        model_id: str,
        kind: BlackboardRecordKind,
        payload: Mapping[str, Any],
    ) -> BlackboardRecord:
        if kind not in {
            BlackboardRecordKind.MODEL_CLAIM,
            BlackboardRecordKind.TOOL_PROPOSAL,
        }:
            raise ValueError("invalid model record kind")
        return self._append(
            task_id=task_id,
            kind=kind,
            authority=BlackboardAuthority.MODEL,
            actor_id=model_id,
            validation_class=BlackboardValidationClass.ADVISORY,
            payload=payload,
        )

    def _append_evidence(
        self,
        *,
        task_id: str,
        tool_id: str,
        context_keys: tuple[str, ...],
        summary: str,
        evidence_refs: tuple[str, ...],
    ) -> BlackboardRecord:
        if not context_keys:
            raise ValueError("deterministic evidence must identify provided context_keys")
        if not summary.strip():
            raise ValueError("deterministic evidence summary must be non-empty")
        return self._append(
            task_id=task_id,
            kind=BlackboardRecordKind.DETERMINISTIC_EVIDENCE,
            authority=BlackboardAuthority.DETERMINISTIC_TOOL,
            actor_id=tool_id,
            validation_class=BlackboardValidationClass.DETERMINISTIC_EVIDENCE,
            payload={"context_keys": context_keys, "summary": summary},
            evidence_refs=evidence_refs,
        )


def build_handoff(
    *,
    blackboard: TaskBlackboard,
    route: RouteDecision,
    request: HandoffRequest,
) -> HandoffDecision:
    """Build a Supervisor handoff after deterministic route/context checks."""

    if route.status is RouteStatus.NO_ROUTE:
        return HandoffDecision(route=route, handoff_record=None, visible_view=None)

    available = blackboard.context_keys(request.task_id)
    missing = tuple(
        key for key in request.required_context_keys if key not in available
    )
    if missing:
        return HandoffDecision(
            route=route,
            handoff_record=None,
            visible_view=None,
            missing_context_keys=missing,
        )

    visible = blackboard.view(
        task_id=request.task_id,
        visible_record_ids=request.visible_record_ids or None,
    )
    record = blackboard._append_control(
        task_id=request.task_id,
        kind=BlackboardRecordKind.HANDOFF,
        payload={
            "target_task_class": request.target_task_class.value,
            "model": route.model,
            "provider": route.provider,
            "reasoning_effort": route.reasoning_effort,
            "visible_record_ids": tuple(r.record_id for r in visible.records),
            "required_context_keys": request.required_context_keys,
            "route_evidence_refs": route.evidence_refs,
        },
    )
    return HandoffDecision(route=route, handoff_record=record, visible_view=visible)


def resolve_context(
    *,
    blackboard: TaskBlackboard,
    router,
    task_id: str,
    required_context_keys: tuple[str, ...],
    requirements_are_explicit: bool,
    ambiguous_tool_choice: bool = False,
    context_tokens: int = 8192,
    max_output_tokens: int = 2048,
) -> ContextResolutionDecision:
    """Choose the deterministic acquisition/planning path without executing it."""

    available = blackboard.context_keys(task_id)
    missing = tuple(key for key in required_context_keys if key not in available)
    if not missing:
        return ContextResolutionDecision(
            mode=ContextResolutionMode.CONTEXT_READY,
            missing_context_keys=(),
        )

    if requirements_are_explicit:
        return ContextResolutionDecision(
            mode=ContextResolutionMode.DETERMINISTIC_ACQUISITION,
            missing_context_keys=missing,
        )

    task_class = (
        ModelTaskClass.BASELINE_REASONING
        if ambiguous_tool_choice
        else ModelTaskClass.GENERAL_PLANNING
    )
    route = router.route(
        RouteRequest(
            task_class=task_class,
            context_tokens=context_tokens,
            max_output_tokens=max_output_tokens,
            requires_native_tool_proposals=True,
        )
    )
    return ContextResolutionDecision(
        mode=(
            ContextResolutionMode.DEEP_ESCALATION
            if ambiguous_tool_choice
            else ContextResolutionMode.TOOL_PLANNER
        ),
        missing_context_keys=missing,
        route=route,
    )
