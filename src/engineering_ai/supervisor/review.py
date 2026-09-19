"""Evidence-first disagreement review and escalation.

Gate 011 does not use majority voting or confidence aggregation. Model review
remains advisory. Deterministic evidence outranks model claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from engineering_ai.models.routing import (
    DeterministicModelRouter,
    ModelTaskClass,
    RouteRequest,
    RouteStatus,
)
from engineering_ai.supervisor.blackboard import (
    BlackboardRecord,
    BlackboardRecordKind,
    HandoffDecision,
    HandoffRequest,
    TaskBlackboard,
    build_handoff,
)


class EvidenceDisposition(str, Enum):
    SUPPORTS_CLAIM = "SUPPORTS_CLAIM"
    CONTRADICTS_CLAIM = "CONTRADICTS_CLAIM"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class IndependentReviewFinding(str, Enum):
    NO_SUBSTANTIVE_CONFLICT = "NO_SUBSTANTIVE_CONFLICT"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    INCONCLUSIVE = "INCONCLUSIVE"


class DisagreementState(str, Enum):
    RESOLVED_BY_EVIDENCE = "RESOLVED_BY_EVIDENCE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    RESOLVED_AFTER_REVIEW = "RESOLVED_AFTER_REVIEW"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    NEEDS_HUMAN_APPROVAL = "NEEDS_HUMAN_APPROVAL"


@dataclass(frozen=True)
class DisagreementRequest:
    task_id: str
    claim_record_id: int
    originating_model: str
    evidence_record_ids: tuple[int, ...]
    evidence_disposition: EvidenceDisposition
    revision_count: int = 0
    context_tokens: int = 8192
    max_output_tokens: int = 2048

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must be non-empty")
        if self.claim_record_id <= 0:
            raise ValueError("claim_record_id must be positive")
        if not self.originating_model.strip():
            raise ValueError("originating_model must be non-empty")
        if len(set(self.evidence_record_ids)) != len(self.evidence_record_ids):
            raise ValueError("evidence_record_ids must be unique")
        if self.revision_count < 0 or self.revision_count > 1:
            raise ValueError("revision_count must be 0 or 1")


@dataclass(frozen=True)
class ReviewApplication:
    task_id: str
    disagreement_record_id: int
    originating_model: str
    reviewer_model: str
    finding: IndependentReviewFinding
    summary: str
    revision_count: int = 0

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must be non-empty")
        if self.disagreement_record_id <= 0:
            raise ValueError("disagreement_record_id must be positive")
        if not self.originating_model.strip() or not self.reviewer_model.strip():
            raise ValueError("model identities must be non-empty")
        if not self.summary.strip():
            raise ValueError("summary must be non-empty")
        if self.revision_count < 0 or self.revision_count > 1:
            raise ValueError("revision_count must be 0 or 1")


@dataclass(frozen=True)
class DisagreementDecision:
    state: DisagreementState
    disagreement_record: BlackboardRecord
    control_record: BlackboardRecord | None = None
    review_handoff: HandoffDecision | None = None
    review_record: BlackboardRecord | None = None
    claim_outcome: str | None = None
    next_revision_count: int | None = None
    reason: str = ""


def _single_record(
    blackboard: TaskBlackboard,
    *,
    task_id: str,
    record_id: int,
) -> BlackboardRecord:
    view = blackboard.view(task_id=task_id, visible_record_ids=(record_id,))
    if len(view.records) != 1:
        raise ValueError(f"record {record_id} is not visible in task {task_id}")
    return view.records[0]


def _validate_disagreement_inputs(
    blackboard: TaskBlackboard,
    request: DisagreementRequest,
) -> tuple[BlackboardRecord, tuple[BlackboardRecord, ...]]:
    claim = _single_record(
        blackboard,
        task_id=request.task_id,
        record_id=request.claim_record_id,
    )
    if claim.kind is not BlackboardRecordKind.MODEL_CLAIM:
        raise ValueError("claim_record_id must reference MODEL_CLAIM")
    if claim.actor_id != request.originating_model:
        raise ValueError("originating_model must match claim actor")

    evidence: list[BlackboardRecord] = []
    for record_id in request.evidence_record_ids:
        record = _single_record(
            blackboard,
            task_id=request.task_id,
            record_id=record_id,
        )
        if record.kind is not BlackboardRecordKind.DETERMINISTIC_EVIDENCE:
            raise ValueError("evidence_record_ids must reference deterministic evidence")
        evidence.append(record)

    if (
        request.evidence_disposition
        in {
            EvidenceDisposition.SUPPORTS_CLAIM,
            EvidenceDisposition.CONTRADICTS_CLAIM,
            EvidenceDisposition.INCONCLUSIVE,
        }
        and not evidence
    ):
        raise ValueError(
            "evidence disposition requires at least one deterministic evidence record"
        )
    if (
        request.evidence_disposition is EvidenceDisposition.NOT_AVAILABLE
        and evidence
    ):
        raise ValueError("NOT_AVAILABLE cannot include evidence records")

    return claim, tuple(evidence)


def _append_human_escalation(
    blackboard: TaskBlackboard,
    *,
    task_id: str,
    disagreement_record_id: int,
    reason: str,
) -> BlackboardRecord:
    return blackboard._append_control(
        task_id=task_id,
        kind=BlackboardRecordKind.HUMAN_ESCALATION,
        payload={
            "state": DisagreementState.NEEDS_HUMAN_APPROVAL.value,
            "disagreement_record_id": disagreement_record_id,
            "reason": reason,
        },
    )


def plan_disagreement(
    *,
    blackboard: TaskBlackboard,
    router: DeterministicModelRouter,
    request: DisagreementRequest,
) -> DisagreementDecision:
    """Apply evidence-first resolution, otherwise create bounded review handoff."""

    claim, evidence = _validate_disagreement_inputs(blackboard, request)
    disagreement = blackboard._append_control(
        task_id=request.task_id,
        kind=BlackboardRecordKind.DISAGREEMENT,
        payload={
            "claim_record_id": claim.record_id,
            "originating_model": request.originating_model,
            "evidence_record_ids": tuple(record.record_id for record in evidence),
            "evidence_disposition": request.evidence_disposition.value,
            "revision_count": request.revision_count,
        },
    )

    if request.evidence_disposition is EvidenceDisposition.SUPPORTS_CLAIM:
        terminal = blackboard._append_control(
            task_id=request.task_id,
            kind=BlackboardRecordKind.TERMINAL_STATE,
            payload={
                "state": DisagreementState.RESOLVED_BY_EVIDENCE.value,
                "disagreement_record_id": disagreement.record_id,
                "claim_outcome": "SUPPORTED_BY_DETERMINISTIC_EVIDENCE",
            },
        )
        return DisagreementDecision(
            state=DisagreementState.RESOLVED_BY_EVIDENCE,
            disagreement_record=disagreement,
            control_record=terminal,
            claim_outcome="SUPPORTED_BY_DETERMINISTIC_EVIDENCE",
            reason="deterministic evidence supports the claim",
        )

    if request.evidence_disposition is EvidenceDisposition.CONTRADICTS_CLAIM:
        terminal = blackboard._append_control(
            task_id=request.task_id,
            kind=BlackboardRecordKind.TERMINAL_STATE,
            payload={
                "state": DisagreementState.RESOLVED_BY_EVIDENCE.value,
                "disagreement_record_id": disagreement.record_id,
                "claim_outcome": "REJECTED_BY_DETERMINISTIC_EVIDENCE",
            },
        )
        return DisagreementDecision(
            state=DisagreementState.RESOLVED_BY_EVIDENCE,
            disagreement_record=disagreement,
            control_record=terminal,
            claim_outcome="REJECTED_BY_DETERMINISTIC_EVIDENCE",
            reason="deterministic evidence contradicts the claim",
        )

    route = router.route(
        RouteRequest(
            task_class=ModelTaskClass.BASELINE_REASONING,
            context_tokens=request.context_tokens,
            max_output_tokens=request.max_output_tokens,
            requires_native_tool_proposals=False,
        )
    )
    if route.status is not RouteStatus.ROUTE or route.model is None:
        escalation = _append_human_escalation(
            blackboard,
            task_id=request.task_id,
            disagreement_record_id=disagreement.record_id,
            reason="no qualified independent reviewer route",
        )
        return DisagreementDecision(
            state=DisagreementState.NEEDS_HUMAN_APPROVAL,
            disagreement_record=disagreement,
            control_record=escalation,
            reason="no qualified independent reviewer route",
        )

    if route.model == request.originating_model:
        escalation = _append_human_escalation(
            blackboard,
            task_id=request.task_id,
            disagreement_record_id=disagreement.record_id,
            reason="review route is not independent from originating model",
        )
        return DisagreementDecision(
            state=DisagreementState.NEEDS_HUMAN_APPROVAL,
            disagreement_record=disagreement,
            control_record=escalation,
            reason="originating model cannot independently review itself",
        )

    visible_ids = (
        request.claim_record_id,
        *request.evidence_record_ids,
        disagreement.record_id,
    )
    handoff = build_handoff(
        blackboard=blackboard,
        route=route,
        request=HandoffRequest(
            task_id=request.task_id,
            target_task_class=ModelTaskClass.BASELINE_REASONING,
            visible_record_ids=visible_ids,
            context_tokens=request.context_tokens,
            max_output_tokens=request.max_output_tokens,
        ),
    )
    if not handoff.created:
        escalation = _append_human_escalation(
            blackboard,
            task_id=request.task_id,
            disagreement_record_id=disagreement.record_id,
            reason="independent review handoff could not be created",
        )
        return DisagreementDecision(
            state=DisagreementState.NEEDS_HUMAN_APPROVAL,
            disagreement_record=disagreement,
            control_record=escalation,
            review_handoff=handoff,
            reason="independent review handoff could not be created",
        )

    return DisagreementDecision(
        state=DisagreementState.REVIEW_REQUIRED,
        disagreement_record=disagreement,
        review_handoff=handoff,
        reason=f"bounded independent review routed to {route.model}",
    )


def apply_independent_review(
    *,
    blackboard: TaskBlackboard,
    application: ReviewApplication,
) -> DisagreementDecision:
    """Apply one advisory review without promoting it to deterministic evidence."""

    disagreement = _single_record(
        blackboard,
        task_id=application.task_id,
        record_id=application.disagreement_record_id,
    )
    if disagreement.kind is not BlackboardRecordKind.DISAGREEMENT:
        raise ValueError("disagreement_record_id must reference DISAGREEMENT")
    if application.reviewer_model == application.originating_model:
        raise ValueError("independent reviewer must differ from originating model")

    review = blackboard._append_model_record(
        task_id=application.task_id,
        model_id=application.reviewer_model,
        kind=BlackboardRecordKind.REVIEW_FINDING,
        payload={
            "disagreement_record_id": disagreement.record_id,
            "originating_model": application.originating_model,
            "finding": application.finding.value,
            "summary": application.summary,
            "revision_count": application.revision_count,
        },
    )

    if application.finding is IndependentReviewFinding.NO_SUBSTANTIVE_CONFLICT:
        terminal = blackboard._append_control(
            task_id=application.task_id,
            kind=BlackboardRecordKind.TERMINAL_STATE,
            payload={
                "state": DisagreementState.RESOLVED_AFTER_REVIEW.value,
                "disagreement_record_id": disagreement.record_id,
                "review_record_id": review.record_id,
                "validation_note": "workflow conflict resolved; model records remain advisory",
            },
        )
        return DisagreementDecision(
            state=DisagreementState.RESOLVED_AFTER_REVIEW,
            disagreement_record=disagreement,
            control_record=terminal,
            review_record=review,
            reason="review found no substantive conflict; validation class unchanged",
        )

    if application.finding is IndependentReviewFinding.REVISION_REQUIRED:
        if application.revision_count == 0:
            revision = blackboard._append_control(
                task_id=application.task_id,
                kind=BlackboardRecordKind.REVISION_REQUEST,
                payload={
                    "state": DisagreementState.REVISION_REQUIRED.value,
                    "disagreement_record_id": disagreement.record_id,
                    "review_record_id": review.record_id,
                    "next_revision_count": 1,
                },
            )
            return DisagreementDecision(
                state=DisagreementState.REVISION_REQUIRED,
                disagreement_record=disagreement,
                control_record=revision,
                review_record=review,
                next_revision_count=1,
                reason="one bounded revision is permitted",
            )

        escalation = _append_human_escalation(
            blackboard,
            task_id=application.task_id,
            disagreement_record_id=disagreement.record_id,
            reason="revision bound exhausted",
        )
        return DisagreementDecision(
            state=DisagreementState.NEEDS_HUMAN_APPROVAL,
            disagreement_record=disagreement,
            control_record=escalation,
            review_record=review,
            reason="revision bound exhausted",
        )

    escalation = _append_human_escalation(
        blackboard,
        task_id=application.task_id,
        disagreement_record_id=disagreement.record_id,
        reason="independent review remained inconclusive",
    )
    return DisagreementDecision(
        state=DisagreementState.NEEDS_HUMAN_APPROVAL,
        disagreement_record=disagreement,
        control_record=escalation,
        review_record=review,
        reason="independent review remained inconclusive",
    )
