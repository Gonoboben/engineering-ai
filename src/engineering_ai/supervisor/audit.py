"""Structured audit-event emission for deterministic Supervisor operations."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from engineering_ai.supervisor.policy import PolicyDecision
from engineering_ai.validation import validate_instance


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _event_id() -> str:
    return f"evt-{uuid4()}"


class AuditEmitter:
    """Build and validate append-oriented audit events.

    Clock and ID generation are injectable so tests can prove deterministic behavior.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] = _utc_now,
        event_id_factory: Callable[[], str] = _event_id,
        supervisor_id: str = "engineering-ai-supervisor",
    ) -> None:
        self._clock = clock
        self._event_id_factory = event_id_factory
        self._supervisor_id = supervisor_id

    def policy_event(
        self,
        *,
        project_id: str,
        gate_id: str | None,
        job_id: str,
        decision: PolicyDecision,
        before_ref: str | None,
        after_ref: str | None,
    ) -> dict[str, Any]:
        if decision.decision.value == "ALLOW":
            status = "PASS"
        elif decision.decision.value == "NEEDS_HUMAN_APPROVAL":
            status = "NEEDS_HUMAN_APPROVAL"
        else:
            status = "BLOCKED"

        event = self._base_event(
            project_id=project_id,
            gate_id=gate_id,
            job_id=job_id,
            event_type="POLICY_CHECK",
            action=decision.action,
            status=status,
            summary=decision.reason,
            before_ref=before_ref,
            after_ref=after_ref,
            evidence_refs=[],
            approval_required=decision.approval_required,
            approval_obtained=decision.approval_obtained,
            approver=decision.approver,
        )
        validate_instance("audit-event.schema.json", event)
        return event

    def tool_event(
        self,
        *,
        project_id: str,
        gate_id: str | None,
        job_id: str,
        action: str,
        ok: bool,
        summary: str,
        before_ref: str | None,
        after_ref: str | None,
        evidence_refs: list[str],
        approval_required: bool,
        approval_obtained: bool,
        approver: str | None,
    ) -> dict[str, Any]:
        event = self._base_event(
            project_id=project_id,
            gate_id=gate_id,
            job_id=job_id,
            event_type="TOOL_CALL",
            action=action,
            status="PASS" if ok else "FAIL",
            summary=summary,
            before_ref=before_ref,
            after_ref=after_ref,
            evidence_refs=evidence_refs,
            approval_required=approval_required,
            approval_obtained=approval_obtained,
            approver=approver,
        )
        validate_instance("audit-event.schema.json", event)
        return event

    def state_event(
        self,
        *,
        project_id: str,
        gate_id: str | None,
        job_id: str,
        action: str,
        status: str,
        summary: str,
        before_ref: str | None,
        after_ref: str | None,
        evidence_refs: list[str] | None = None,
    ) -> dict[str, Any]:
        event = self._base_event(
            project_id=project_id,
            gate_id=gate_id,
            job_id=job_id,
            event_type="STATE_TRANSITION",
            action=action,
            status=status,
            summary=summary,
            before_ref=before_ref,
            after_ref=after_ref,
            evidence_refs=evidence_refs or [],
            approval_required=False,
            approval_obtained=False,
            approver=None,
        )
        validate_instance("audit-event.schema.json", event)
        return event

    def _base_event(
        self,
        *,
        project_id: str,
        gate_id: str | None,
        job_id: str,
        event_type: str,
        action: str,
        status: str,
        summary: str,
        before_ref: str | None,
        after_ref: str | None,
        evidence_refs: list[str],
        approval_required: bool,
        approval_obtained: bool,
        approver: str | None,
    ) -> dict[str, Any]:
        timestamp = self._clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return {
            "schema_version": "1.0",
            "event_id": self._event_id_factory(),
            "timestamp": timestamp,
            "actor": {
                "kind": "supervisor",
                "id": self._supervisor_id,
                "runtime": "python",
            },
            "project_id": project_id,
            "gate_id": gate_id,
            "job_id": job_id,
            "event_type": event_type,
            "action": action,
            "result": {"status": status, "summary": summary},
            "before_ref": before_ref,
            "after_ref": after_ref,
            "evidence_refs": evidence_refs,
            "approval": {
                "required": approval_required,
                "obtained": approval_obtained,
                "approver": approver,
            },
            "contains_secrets": False,
        }
