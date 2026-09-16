"""Deterministic non-LLM Supervisor core."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

from engineering_ai.supervisor.audit import AuditEmitter
from engineering_ai.supervisor.policy import Decision, PolicyDecision, PolicyEngine
from engineering_ai.validation import SemanticValidationError, validate_instance


@dataclass(frozen=True)
class ToolOutcome:
    ok: bool
    summary: str
    evidence_refs: tuple[str, ...] = ()


class ToolCallable(Protocol):
    def __call__(self, action: str) -> ToolOutcome: ...


@dataclass(frozen=True)
class ExecutionResult:
    decision: PolicyDecision
    job: dict[str, Any]
    state: dict[str, Any]
    audit_events: tuple[dict[str, Any], ...]
    tool_called: bool


class Supervisor:
    """Control authority for deterministic policy/state transitions.

    Input policy/state records are copied on construction. Callers receive snapshots,
    so advisory agents cannot mutate the Supervisor's authoritative state directly.
    """

    TERMINAL_JOB_STATES = {"PASS", "FAIL", "CANCELLED"}
    TRANSIENT_BLOCKER_PREFIXES = (
        "human approval required for action:",
        "policy denied action:",
        "tool failure; retry available:",
        "retry limit exhausted after tool failure:",
    )

    def __init__(
        self,
        *,
        policy: dict[str, Any],
        state: dict[str, Any],
        audit_emitter: AuditEmitter | None = None,
    ) -> None:
        self._policy = deepcopy(policy)
        self._state = deepcopy(state)
        self._policy_engine = PolicyEngine(self._policy, self._state)
        self._audit = audit_emitter or AuditEmitter()
        self._audit_events: list[dict[str, Any]] = []

    @property
    def state(self) -> dict[str, Any]:
        return deepcopy(self._state)

    @property
    def audit_events(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(self._audit_events))

    def execute(
        self,
        *,
        job: dict[str, Any],
        action: str,
        tool: ToolCallable,
        approval_obtained: bool = False,
        approver: str | None = None,
    ) -> ExecutionResult:
        working_job = deepcopy(job)
        validate_instance("job.schema.json", working_job)
        self._validate_job_context(working_job)

        if working_job["status"] in self.TERMINAL_JOB_STATES:
            raise SemanticValidationError(
                f"terminal job cannot execute action: {working_job['status']}"
            )

        before_ref = self._repository_ref()
        decision = self._decision_for_request(
            job=working_job,
            action=action,
            approval_obtained=approval_obtained,
            approver=approver,
        )
        self._record(
            self._audit.policy_event(
                project_id=working_job["project_id"],
                gate_id=working_job.get("gate_id"),
                job_id=working_job["job_id"],
                decision=decision,
                before_ref=before_ref,
                after_ref=before_ref,
            )
        )

        if decision.decision is Decision.DENY:
            blocker = f"policy denied action: {action}"
            working_job["status"] = "BLOCKED"
            working_job["blocker"] = blocker
            self._apply_state_blocker(working_job, blocker, next_action=None)
            self._record_transition(
                job=working_job,
                action=action,
                status="BLOCKED",
                summary=blocker,
                before_ref=before_ref,
            )
            return self._result(decision, working_job, tool_called=False)

        if decision.decision is Decision.NEEDS_HUMAN_APPROVAL:
            blocker = f"human approval required for action: {action}"
            working_job["status"] = "WAITING_FOR_APPROVAL"
            working_job["blocker"] = blocker
            self._apply_state_blocker(
                working_job,
                blocker,
                next_action=f"obtain human approval for {action}",
            )
            self._record_transition(
                job=working_job,
                action=action,
                status="NEEDS_HUMAN_APPROVAL",
                summary=blocker,
                before_ref=before_ref,
            )
            return self._result(decision, working_job, tool_called=False)

        working_job["status"] = "RUNNING"
        working_job["blocker"] = None
        self._state["active_job_id"] = working_job["job_id"]
        outcome = tool(action)
        if not isinstance(outcome, ToolOutcome):
            raise TypeError("tool must return ToolOutcome")

        self._record(
            self._audit.tool_event(
                project_id=working_job["project_id"],
                gate_id=working_job.get("gate_id"),
                job_id=working_job["job_id"],
                action=action,
                ok=outcome.ok,
                summary=outcome.summary,
                before_ref=before_ref,
                after_ref=self._repository_ref(),
                evidence_refs=list(outcome.evidence_refs),
                approval_required=decision.approval_required,
                approval_obtained=decision.approval_obtained,
                approver=decision.approver,
            )
        )

        if outcome.ok:
            working_job["status"] = "PASS"
            working_job["blocker"] = None
            self._clear_transient_supervisor_blockers()
            self._advance_state(active_job_id=None, next_action=None)
            self._record_transition(
                job=working_job,
                action=action,
                status="PASS",
                summary="tool action completed successfully",
                before_ref=before_ref,
                evidence_refs=list(outcome.evidence_refs),
            )
        else:
            self._handle_tool_failure(working_job, action, outcome, before_ref)

        return self._result(decision, working_job, tool_called=True)

    def _decision_for_request(
        self,
        *,
        job: dict[str, Any],
        action: str,
        approval_obtained: bool,
        approver: str | None,
    ) -> PolicyDecision:
        if action not in job["requested_actions"]:
            return PolicyDecision(
                action=action,
                decision=Decision.DENY,
                reason="action was not declared in the job requested_actions",
            )
        return self._policy_engine.evaluate(
            action,
            approval_obtained=approval_obtained,
            approver=approver,
        )

    def _handle_tool_failure(
        self,
        job: dict[str, Any],
        action: str,
        outcome: ToolOutcome,
        before_ref: str | None,
    ) -> None:
        if job["attempts"] >= job["retry_limit"]:
            blocker = f"retry limit exhausted after tool failure: {outcome.summary}"
            job["status"] = "FAIL"
            job["blocker"] = blocker
            self._apply_state_blocker(job, blocker, next_action=None)
            self._record_transition(
                job=job,
                action=action,
                status="FAIL",
                summary=blocker,
                before_ref=before_ref,
                evidence_refs=list(outcome.evidence_refs),
            )
            return

        job["attempts"] += 1
        blocker = f"tool failure; retry available: {outcome.summary}"
        job["status"] = "QUEUED"
        job["blocker"] = blocker
        self._apply_state_blocker(job, blocker, next_action=f"retry {action}")
        self._record_transition(
            job=job,
            action=action,
            status="FAIL",
            summary=blocker,
            before_ref=before_ref,
            evidence_refs=list(outcome.evidence_refs),
        )

    def _validate_job_context(self, job: dict[str, Any]) -> None:
        if job["project_id"] != self._policy["project_id"]:
            raise SemanticValidationError("job/policy project_id mismatch")
        if job["project_id"] != self._state["project_id"]:
            raise SemanticValidationError("job/state project_id mismatch")
        if job["retry_limit"] > self._policy["retry_limit"]:
            raise SemanticValidationError(
                "job retry_limit cannot exceed project policy retry_limit"
            )

    def _apply_state_blocker(
        self,
        job: dict[str, Any],
        blocker: str,
        *,
        next_action: str | None,
    ) -> None:
        self._state["active_job_id"] = job["job_id"]
        if blocker not in self._state["blockers"]:
            self._state["blockers"].append(blocker)
        self._advance_state(active_job_id=job["job_id"], next_action=next_action)

    def _clear_transient_supervisor_blockers(self) -> None:
        self._state["blockers"] = [
            blocker
            for blocker in self._state["blockers"]
            if not blocker.startswith(self.TRANSIENT_BLOCKER_PREFIXES)
        ]

    def _advance_state(
        self,
        *,
        active_job_id: str | None,
        next_action: str | None,
    ) -> None:
        self._state["state_revision"] += 1
        self._state["active_job_id"] = active_job_id
        self._state["next_admissible_action"] = next_action
        validate_instance("project-state.schema.json", self._state)

    def _record_transition(
        self,
        *,
        job: dict[str, Any],
        action: str,
        status: str,
        summary: str,
        before_ref: str | None,
        evidence_refs: list[str] | None = None,
    ) -> None:
        validate_instance("job.schema.json", job)
        self._record(
            self._audit.state_event(
                project_id=job["project_id"],
                gate_id=job.get("gate_id"),
                job_id=job["job_id"],
                action=action,
                status=status,
                summary=summary,
                before_ref=before_ref,
                after_ref=self._repository_ref(),
                evidence_refs=evidence_refs,
            )
        )

    def _record(self, event: dict[str, Any]) -> None:
        validate_instance("audit-event.schema.json", event)
        self._audit_events.append(deepcopy(event))

    def _repository_ref(self) -> str | None:
        ref = self._state.get("repository_ref")
        if not ref:
            return None
        sha = ref.get("head_sha") or "unknown"
        return f"{ref['branch']}@{sha}"

    def _result(
        self,
        decision: PolicyDecision,
        job: dict[str, Any],
        *,
        tool_called: bool,
    ) -> ExecutionResult:
        validate_instance("job.schema.json", job)
        validate_instance("project-state.schema.json", self._state)
        return ExecutionResult(
            decision=decision,
            job=deepcopy(job),
            state=deepcopy(self._state),
            audit_events=self.audit_events,
            tool_called=tool_called,
        )
