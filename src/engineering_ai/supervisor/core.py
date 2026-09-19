"""Deterministic non-LLM Supervisor core."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

from engineering_ai.models.routing import (
    DeterministicModelRouter,
    RouteDecision,
    RouteRequest,
)
from engineering_ai.supervisor.blackboard import (
    BlackboardRecord,
    BlackboardRecordKind,
    BlackboardView,
    ContextResolutionDecision,
    HandoffDecision,
    HandoffRequest,
    TaskBlackboard,
    build_handoff,
    resolve_context,
)
from engineering_ai.supervisor.review import (
    DisagreementDecision,
    DisagreementRequest,
    ReviewApplication,
    apply_independent_review,
    plan_disagreement,
)
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


@dataclass(frozen=True)
class ProposalExecutionResult:
    decision: PolicyDecision
    outcome: ToolOutcome | None
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
        model_router: DeterministicModelRouter | None = None,
        blackboard: TaskBlackboard | None = None,
    ) -> None:
        self._policy = deepcopy(policy)
        self._state = deepcopy(state)
        self._policy_engine = PolicyEngine(self._policy, self._state)
        self._audit = audit_emitter or AuditEmitter()
        self._model_router = model_router
        self._blackboard = blackboard
        self._audit_events: list[dict[str, Any]] = []

    @property
    def state(self) -> dict[str, Any]:
        return deepcopy(self._state)

    @property
    def audit_events(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(self._audit_events))

    def route_model(self, request: RouteRequest) -> RouteDecision:
        """Route an explicit task class through the configured deterministic router.

        Routing is selection only. It never invokes a provider, model, or tool.
        """
        if self._model_router is None:
            raise RuntimeError("Supervisor has no model router configured")
        return self._model_router.route(request)

    def blackboard_view(
        self,
        *,
        task_id: str,
        visible_record_ids: tuple[int, ...] | None = None,
    ) -> BlackboardView:
        board = self._require_blackboard()
        return board.view(
            task_id=task_id,
            visible_record_ids=visible_record_ids,
        )

    def blackboard_assign_task(
        self,
        *,
        task_id: str,
        objective: str,
        requested_task_class: str,
    ) -> BlackboardRecord:
        if not objective.strip():
            raise ValueError("objective must be non-empty")
        return self._require_blackboard()._append_control(
            task_id=task_id,
            kind=BlackboardRecordKind.TASK_ASSIGNMENT,
            payload={
                "objective": objective,
                "requested_task_class": requested_task_class,
            },
        )

    def blackboard_record_context_requirement(
        self,
        *,
        task_id: str,
        required_context_keys: tuple[str, ...],
    ) -> BlackboardRecord:
        if not required_context_keys:
            raise ValueError("required_context_keys must be non-empty")
        if len(set(required_context_keys)) != len(required_context_keys):
            raise ValueError("required_context_keys must be unique")
        return self._require_blackboard()._append_control(
            task_id=task_id,
            kind=BlackboardRecordKind.CONTEXT_REQUIREMENT,
            payload={"required_context_keys": required_context_keys},
        )

    def blackboard_record_model_claim(
        self,
        *,
        task_id: str,
        model_id: str,
        payload: dict[str, Any],
    ) -> BlackboardRecord:
        return self._require_blackboard()._append_model_record(
            task_id=task_id,
            model_id=model_id,
            kind=BlackboardRecordKind.MODEL_CLAIM,
            payload=payload,
        )

    def blackboard_record_tool_proposal(
        self,
        *,
        task_id: str,
        model_id: str,
        payload: dict[str, Any],
    ) -> BlackboardRecord:
        return self._require_blackboard()._append_model_record(
            task_id=task_id,
            model_id=model_id,
            kind=BlackboardRecordKind.TOOL_PROPOSAL,
            payload=payload,
        )

    def blackboard_record_evidence(
        self,
        *,
        task_id: str,
        tool_id: str,
        context_keys: tuple[str, ...],
        summary: str,
        evidence_refs: tuple[str, ...],
    ) -> BlackboardRecord:
        return self._require_blackboard()._append_evidence(
            task_id=task_id,
            tool_id=tool_id,
            context_keys=context_keys,
            summary=summary,
            evidence_refs=evidence_refs,
        )

    def resolve_blackboard_context(
        self,
        *,
        task_id: str,
        required_context_keys: tuple[str, ...],
        requirements_are_explicit: bool,
        ambiguous_tool_choice: bool = False,
        context_tokens: int = 8192,
        max_output_tokens: int = 2048,
    ) -> ContextResolutionDecision:
        if self._model_router is None:
            raise RuntimeError("Supervisor has no model router configured")
        return resolve_context(
            blackboard=self._require_blackboard(),
            router=self._model_router,
            task_id=task_id,
            required_context_keys=required_context_keys,
            requirements_are_explicit=requirements_are_explicit,
            ambiguous_tool_choice=ambiguous_tool_choice,
            context_tokens=context_tokens,
            max_output_tokens=max_output_tokens,
        )

    def create_model_handoff(self, request: HandoffRequest) -> HandoffDecision:
        if self._model_router is None:
            raise RuntimeError("Supervisor has no model router configured")
        route = self._model_router.route(
            RouteRequest(
                task_class=request.target_task_class,
                context_tokens=request.context_tokens,
                max_output_tokens=request.max_output_tokens,
                requires_native_tool_proposals=request.requires_native_tool_proposals,
            )
        )
        return build_handoff(
            blackboard=self._require_blackboard(),
            route=route,
            request=request,
        )

    def plan_disagreement_review(
        self,
        request: DisagreementRequest,
    ) -> DisagreementDecision:
        if self._model_router is None:
            raise RuntimeError("Supervisor has no model router configured")
        return plan_disagreement(
            blackboard=self._require_blackboard(),
            router=self._model_router,
            request=request,
        )

    def apply_disagreement_review(
        self,
        application: ReviewApplication,
    ) -> DisagreementDecision:
        return apply_independent_review(
            blackboard=self._require_blackboard(),
            application=application,
        )

    def _require_blackboard(self) -> TaskBlackboard:
        if self._blackboard is None:
            raise RuntimeError("Supervisor has no Task Blackboard configured")
        return self._blackboard

    def evaluate_tool_proposal(
        self,
        *,
        job: dict[str, Any],
        action: str,
        tool: ToolCallable,
        approval_obtained: bool = False,
        approver: str | None = None,
    ) -> ProposalExecutionResult:
        """Evaluate one inert model tool proposal without promoting job state.

        This is the Gate 006 path for role-loop proposals: the existing Supervisor
        remains the sole policy gate and the tool is called only after ALLOW.
        """
        working_job = deepcopy(job)
        validate_instance("job.schema.json", working_job)
        self._validate_job_context(working_job)
        if working_job["status"] in self.TERMINAL_JOB_STATES:
            raise SemanticValidationError(
                f"terminal job cannot evaluate proposal: {working_job['status']}"
            )

        start_index = len(self._audit_events)
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

        if decision.decision is not Decision.ALLOW:
            return ProposalExecutionResult(
                decision=decision,
                outcome=None,
                audit_events=tuple(
                    deepcopy(self._audit_events[start_index:])
                ),
                tool_called=False,
            )

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
        return ProposalExecutionResult(
            decision=decision,
            outcome=outcome,
            audit_events=tuple(deepcopy(self._audit_events[start_index:])),
            tool_called=True,
        )

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
