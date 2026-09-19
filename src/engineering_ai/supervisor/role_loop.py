"""Deterministic Planner / Executor / Reviewer orchestration for Gate 006.

The model is advisory. This module owns role transitions, proposal validation,
evidence requirements, retries, and terminal outcomes. Tool calls from the model
remain inert until policy evaluation permits execution.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

from engineering_ai.models import (
    ModelMessage,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    ModelToolCall,
    ModelToolSpec,
)
from engineering_ai.supervisor.audit import AuditEmitter
from engineering_ai.supervisor.core import Supervisor, ToolOutcome
from engineering_ai.supervisor.policy import Decision
from engineering_ai.validation import SemanticValidationError, validate_instance


class EngineeringRole(str, Enum):
    PLANNER = "PLANNER"
    EXECUTOR = "EXECUTOR"
    REVIEWER = "REVIEWER"


class ReviewDecision(str, Enum):
    ACCEPT = "ACCEPT"
    REVISE = "REVISE"
    REJECT = "REJECT"
    NEEDS_HUMAN_APPROVAL = "NEEDS_HUMAN_APPROVAL"


class LoopState(str, Enum):
    PLAN = "PLAN"
    PLAN_VALIDATED = "PLAN_VALIDATED"
    EXECUTE = "EXECUTE"
    EVIDENCE_COLLECTED = "EVIDENCE_COLLECTED"
    REVIEW = "REVIEW"
    COMPLETE = "COMPLETE"
    FAIL = "FAIL"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"


_ALLOWED_TRANSITIONS: dict[LoopState, frozenset[LoopState]] = {
    LoopState.PLAN: frozenset({LoopState.PLAN_VALIDATED, LoopState.FAIL}),
    LoopState.PLAN_VALIDATED: frozenset({LoopState.EXECUTE, LoopState.FAIL}),
    LoopState.EXECUTE: frozenset(
        {
            LoopState.EVIDENCE_COLLECTED,
            LoopState.FAIL,
            LoopState.WAITING_FOR_APPROVAL,
        }
    ),
    LoopState.EVIDENCE_COLLECTED: frozenset({LoopState.REVIEW, LoopState.FAIL}),
    LoopState.REVIEW: frozenset(
        {
            LoopState.COMPLETE,
            LoopState.PLAN,
            LoopState.FAIL,
            LoopState.WAITING_FOR_APPROVAL,
        }
    ),
    LoopState.COMPLETE: frozenset(),
    LoopState.FAIL: frozenset(),
    LoopState.WAITING_FOR_APPROVAL: frozenset(),
}


@dataclass(frozen=True)
class RoleModelConfig:
    model: str
    reasoning_effort: str = "medium"
    context_tokens: int = 8192
    max_output_tokens: int = 2048
    timeout_seconds: float = 300.0


@dataclass(frozen=True)
class PlanResult:
    steps: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    model_response: ModelResponse


@dataclass(frozen=True)
class ExecutionResult:
    summary: str
    proposed_tools: tuple[ModelToolCall, ...]
    executed_actions: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    model_response: ModelResponse


@dataclass(frozen=True)
class ReviewResult:
    decision: ReviewDecision
    summary: str
    model_response: ModelResponse


@dataclass(frozen=True)
class RoleLoopResult:
    state: LoopState
    job: dict[str, Any]
    project_state: dict[str, Any]
    plan: PlanResult | None
    execution: ExecutionResult | None
    review: ReviewResult | None
    revision_count: int
    audit_events: tuple[dict[str, Any], ...]
    blocker: str | None = None


ToolExecutor = Callable[[Mapping[str, Any]], ToolOutcome]


class RoleStateMachine:
    """Small deterministic state machine with explicit legal transitions."""

    def __init__(self) -> None:
        self._state = LoopState.PLAN

    @property
    def state(self) -> LoopState:
        return self._state

    def transition(self, next_state: LoopState) -> None:
        if next_state not in _ALLOWED_TRANSITIONS[self._state]:
            raise SemanticValidationError(
                f"illegal role-loop transition: {self._state.value} -> {next_state.value}"
            )
        self._state = next_state


class PlannerExecutorReviewerLoop:
    """Supervisor-owned orchestration around one replaceable model provider."""

    def __init__(
        self,
        *,
        policy: dict[str, Any],
        state: dict[str, Any],
        provider: ModelProvider,
        model_config: RoleModelConfig,
        tool_specs: Mapping[str, ModelToolSpec],
        tool_executors: Mapping[str, ToolExecutor],
        audit_emitter: AuditEmitter | None = None,
        max_plan_steps: int = 16,
        max_tool_calls: int = 8,
        max_revisions: int = 1,
    ) -> None:
        if max_plan_steps <= 0 or max_tool_calls <= 0 or max_revisions < 0:
            raise ValueError("role-loop bounds must be positive/non-negative")
        self._policy = deepcopy(policy)
        self._state = deepcopy(state)
        validate_instance("project-policy.schema.json", self._policy)
        validate_instance("project-state.schema.json", self._state)
        self._audit = audit_emitter or AuditEmitter()
        self._supervisor = Supervisor(
            policy=self._policy, state=self._state, audit_emitter=self._audit
        )
        self._provider = provider
        self._config = model_config
        self._tool_specs = dict(tool_specs)
        self._tool_executors = dict(tool_executors)
        self._audit_events: list[dict[str, Any]] = []
        self._max_plan_steps = max_plan_steps
        self._max_tool_calls = max_tool_calls
        self._max_revisions = max_revisions

    @property
    def state(self) -> dict[str, Any]:
        return deepcopy(self._state)

    def run(self, *, job: dict[str, Any], user_task: str) -> RoleLoopResult:
        working_job = deepcopy(job)
        validate_instance("job.schema.json", working_job)
        self._validate_job(working_job)
        if not user_task.strip():
            raise ValueError("user_task must not be empty")

        machine = RoleStateMachine()
        plan: PlanResult | None = None
        execution: ExecutionResult | None = None
        review: ReviewResult | None = None
        revision_count = 0
        revision_note: str | None = None

        while True:
            plan = self._run_planner(
                job=working_job, user_task=user_task, revision_note=revision_note
            )
            try:
                self._validate_plan(working_job, plan)
            except (SemanticValidationError, ValueError) as exc:
                machine.transition(LoopState.FAIL)
                return self._finish(
                    machine=machine,
                    job=working_job,
                    plan=plan,
                    execution=execution,
                    review=review,
                    revision_count=revision_count,
                    blocker=f"invalid planner output: {exc}",
                    status="FAIL",
                )

            machine.transition(LoopState.PLAN_VALIDATED)
            self._record_transition(
                working_job,
                action="planner_plan_validated",
                status="PASS",
                summary=f"validated {len(plan.steps)} planner steps",
            )
            machine.transition(LoopState.EXECUTE)

            execution_or_terminal = self._run_executor(
                job=working_job,
                user_task=user_task,
                plan=plan,
            )
            if isinstance(execution_or_terminal, RoleLoopResult):
                return execution_or_terminal
            execution = execution_or_terminal

            machine.transition(LoopState.EVIDENCE_COLLECTED)
            if not execution.evidence_refs:
                machine.transition(LoopState.FAIL)
                return self._finish(
                    machine=machine,
                    job=working_job,
                    plan=plan,
                    execution=execution,
                    review=review,
                    revision_count=revision_count,
                    blocker="missing deterministic evidence; completion is prohibited",
                    status="FAIL",
                )

            self._record_transition(
                working_job,
                action="execution_evidence_collected",
                status="PASS",
                summary=f"collected {len(execution.evidence_refs)} deterministic evidence refs",
                evidence_refs=list(execution.evidence_refs),
            )
            machine.transition(LoopState.REVIEW)

            review = self._run_reviewer(
                job=working_job,
                user_task=user_task,
                plan=plan,
                execution=execution,
            )

            if review.decision is ReviewDecision.ACCEPT:
                machine.transition(LoopState.COMPLETE)
                return self._finish(
                    machine=machine,
                    job=working_job,
                    plan=plan,
                    execution=execution,
                    review=review,
                    revision_count=revision_count,
                    blocker=None,
                    status="PASS",
                )

            if review.decision is ReviewDecision.REJECT:
                machine.transition(LoopState.FAIL)
                return self._finish(
                    machine=machine,
                    job=working_job,
                    plan=plan,
                    execution=execution,
                    review=review,
                    revision_count=revision_count,
                    blocker=f"reviewer rejected execution: {review.summary}",
                    status="FAIL",
                )

            if review.decision is ReviewDecision.NEEDS_HUMAN_APPROVAL:
                machine.transition(LoopState.WAITING_FOR_APPROVAL)
                return self._finish(
                    machine=machine,
                    job=working_job,
                    plan=plan,
                    execution=execution,
                    review=review,
                    revision_count=revision_count,
                    blocker=f"reviewer requested human approval: {review.summary}",
                    status="WAITING_FOR_APPROVAL",
                )

            if revision_count >= self._max_revisions:
                machine.transition(LoopState.FAIL)
                return self._finish(
                    machine=machine,
                    job=working_job,
                    plan=plan,
                    execution=execution,
                    review=review,
                    revision_count=revision_count,
                    blocker="bounded revision limit exhausted",
                    status="FAIL",
                )

            revision_count += 1
            revision_note = review.summary
            self._record_transition(
                working_job,
                action="reviewer_revision_requested",
                status="FAIL",
                summary=(
                    f"revision {revision_count}/{self._max_revisions} requested: "
                    f"{review.summary}"
                ),
                evidence_refs=list(execution.evidence_refs),
            )
            machine.transition(LoopState.PLAN)

    def _run_planner(
        self,
        *,
        job: dict[str, Any],
        user_task: str,
        revision_note: str | None,
    ) -> PlanResult:
        context = {
            "objective": job["objective"],
            "scope": job["scope"],
            "out_of_scope": job["out_of_scope"],
            "requested_actions": job["requested_actions"],
            "task": user_task,
            "revision_note": revision_note,
        }
        request = ModelRequest(
            model=self._config.model,
            messages=(
                ModelMessage(
                    "system",
                    "You are PLANNER. Return only a bounded JSON plan. "
                    "Do not execute tools, invent evidence, or change policy/state.",
                ),
                ModelMessage("user", json.dumps(context, sort_keys=True)),
            ),
            response_schema={
                "type": "object",
                "properties": {
                    "steps": {"type": "array", "items": {"type": "string"}},
                    "allowed_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["steps", "allowed_actions"],
                "additionalProperties": False,
            },
            temperature=0.0,
            seed=0,
            context_tokens=self._config.context_tokens,
            max_output_tokens=self._config.max_output_tokens,
            reasoning_effort=self._config.reasoning_effort,
        )
        response = self._provider.chat(
            request, timeout_seconds=self._config.timeout_seconds
        )
        self._record_model_call(job, EngineeringRole.PLANNER, response)
        payload = self._json_object(response.content, EngineeringRole.PLANNER)
        steps = self._string_tuple(payload.get("steps"), "steps")
        allowed = self._string_tuple(payload.get("allowed_actions"), "allowed_actions")
        return PlanResult(steps=steps, allowed_actions=allowed, model_response=response)

    def _run_executor(
        self,
        *,
        job: dict[str, Any],
        user_task: str,
        plan: PlanResult,
    ) -> ExecutionResult | RoleLoopResult:
        specs = tuple(
            self._tool_specs[action]
            for action in plan.allowed_actions
            if action in self._tool_specs
        )
        request = ModelRequest(
            model=self._config.model,
            messages=(
                ModelMessage(
                    "system",
                    "You are EXECUTOR. Follow only the approved plan. "
                    "Tool calls are proposals only. Do not claim tool/evidence results.",
                ),
                ModelMessage(
                    "user",
                    json.dumps(
                        {
                            "task": user_task,
                            "approved_plan": {
                                "steps": plan.steps,
                                "allowed_actions": plan.allowed_actions,
                            },
                        },
                        sort_keys=True,
                    ),
                ),
            ),
            tools=specs,
            response_schema={
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
                "additionalProperties": False,
            },
            temperature=0.0,
            seed=0,
            context_tokens=self._config.context_tokens,
            max_output_tokens=self._config.max_output_tokens,
            reasoning_effort=self._config.reasoning_effort,
        )
        response = self._provider.chat(
            request, timeout_seconds=self._config.timeout_seconds
        )
        self._record_model_call(job, EngineeringRole.EXECUTOR, response)
        payload = self._json_object(response.content, EngineeringRole.EXECUTOR)
        summary = payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise SemanticValidationError("executor summary must be non-empty")

        proposals = response.tool_calls
        if len(proposals) > self._max_tool_calls:
            raise SemanticValidationError("executor exceeded bounded tool proposal limit")

        executed: list[str] = []
        evidence: list[str] = []
        seen_evidence: set[str] = set()

        for proposal in proposals:
            action = proposal.name
            if action not in plan.allowed_actions or action not in job["requested_actions"]:
                return self._terminal_from_executor(
                    job,
                    plan,
                    response,
                    summary,
                    executed,
                    evidence,
                    f"tool proposal outside approved plan/job: {action}",
                    waiting=False,
                )

            executor = self._tool_executors.get(action)
            if executor is None:
                return self._terminal_from_executor(
                    job,
                    plan,
                    response,
                    summary,
                    executed,
                    evidence,
                    f"no deterministic executor registered for action: {action}",
                    waiting=False,
                )

            proposal_result = self._supervisor.evaluate_tool_proposal(
                job=job,
                action=action,
                tool=lambda _action, executor=executor, args=proposal.arguments: executor(args),
            )
            for event in proposal_result.audit_events:
                self._record(event)
            decision = proposal_result.decision

            if decision.decision is Decision.NEEDS_HUMAN_APPROVAL:
                return self._terminal_from_executor(
                    job,
                    plan,
                    response,
                    summary,
                    executed,
                    evidence,
                    f"human approval required for proposed action: {action}",
                    waiting=True,
                )
            if decision.decision is not Decision.ALLOW:
                return self._terminal_from_executor(
                    job,
                    plan,
                    response,
                    summary,
                    executed,
                    evidence,
                    f"policy denied proposed action: {action}",
                    waiting=False,
                )

            outcome = proposal_result.outcome
            if outcome is None:
                raise RuntimeError("Supervisor ALLOW must produce a ToolOutcome")
            if not outcome.ok:
                return self._terminal_from_executor(
                    job,
                    plan,
                    response,
                    summary,
                    executed,
                    evidence,
                    f"deterministic tool failure: {action}: {outcome.summary}",
                    waiting=False,
                )
            executed.append(action)
            for ref in outcome.evidence_refs:
                if ref not in seen_evidence:
                    evidence.append(ref)
                    seen_evidence.add(ref)

        return ExecutionResult(
            summary=summary,
            proposed_tools=tuple(proposals),
            executed_actions=tuple(executed),
            evidence_refs=tuple(evidence),
            model_response=response,
        )

    def _run_reviewer(
        self,
        *,
        job: dict[str, Any],
        user_task: str,
        plan: PlanResult,
        execution: ExecutionResult,
    ) -> ReviewResult:
        request = ModelRequest(
            model=self._config.model,
            messages=(
                ModelMessage(
                    "system",
                    "You are REVIEWER. Judge only the supplied deterministic evidence. "
                    "You cannot execute tools or change state.",
                ),
                ModelMessage(
                    "user",
                    json.dumps(
                        {
                            "task": user_task,
                            "plan": {
                                "steps": plan.steps,
                                "allowed_actions": plan.allowed_actions,
                            },
                            "execution": {
                                "summary": execution.summary,
                                "executed_actions": execution.executed_actions,
                                "evidence_refs": execution.evidence_refs,
                            },
                        },
                        sort_keys=True,
                    ),
                ),
            ),
            response_schema={
                "type": "object",
                "properties": {
                    "decision": {
                        "type": "string",
                        "enum": [item.value for item in ReviewDecision],
                    },
                    "summary": {"type": "string"},
                },
                "required": ["decision", "summary"],
                "additionalProperties": False,
            },
            temperature=0.0,
            seed=0,
            context_tokens=self._config.context_tokens,
            max_output_tokens=self._config.max_output_tokens,
            reasoning_effort=self._config.reasoning_effort,
        )
        response = self._provider.chat(
            request, timeout_seconds=self._config.timeout_seconds
        )
        self._record_model_call(job, EngineeringRole.REVIEWER, response)
        payload = self._json_object(response.content, EngineeringRole.REVIEWER)
        try:
            decision = ReviewDecision(payload.get("decision"))
        except ValueError as exc:
            raise SemanticValidationError("invalid reviewer decision") from exc
        summary = payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise SemanticValidationError("reviewer summary must be non-empty")
        return ReviewResult(decision=decision, summary=summary, model_response=response)

    def _validate_plan(self, job: dict[str, Any], plan: PlanResult) -> None:
        if not plan.steps:
            raise SemanticValidationError("planner must provide at least one step")
        if len(plan.steps) > self._max_plan_steps:
            raise SemanticValidationError("planner exceeded bounded step limit")
        if len(set(plan.allowed_actions)) != len(plan.allowed_actions):
            raise SemanticValidationError("planner allowed_actions must be unique")
        for action in plan.allowed_actions:
            if action not in job["requested_actions"]:
                raise SemanticValidationError(
                    f"planner requested undeclared action: {action}"
                )
            if action not in self._tool_specs:
                raise SemanticValidationError(
                    f"planner requested action without an exposed tool spec: {action}"
                )

    def _validate_job(self, job: dict[str, Any]) -> None:
        if job["project_id"] != self._policy["project_id"]:
            raise SemanticValidationError("job/policy project_id mismatch")
        if job["project_id"] != self._state["project_id"]:
            raise SemanticValidationError("job/state project_id mismatch")
        if job["retry_limit"] > self._policy["retry_limit"]:
            raise SemanticValidationError(
                "job retry_limit cannot exceed project policy retry_limit"
            )
        if job["status"] in {"PASS", "FAIL", "CANCELLED"}:
            raise SemanticValidationError("terminal job cannot enter role loop")

    def _terminal_from_executor(
        self,
        job: dict[str, Any],
        plan: PlanResult,
        response: ModelResponse,
        summary: str,
        executed: Sequence[str],
        evidence: Sequence[str],
        blocker: str,
        *,
        waiting: bool,
    ) -> RoleLoopResult:
        machine = RoleStateMachine()
        machine.transition(LoopState.PLAN_VALIDATED)
        machine.transition(LoopState.EXECUTE)
        machine.transition(
            LoopState.WAITING_FOR_APPROVAL if waiting else LoopState.FAIL
        )
        execution = ExecutionResult(
            summary=summary,
            proposed_tools=response.tool_calls,
            executed_actions=tuple(executed),
            evidence_refs=tuple(evidence),
            model_response=response,
        )
        return self._finish(
            machine=machine,
            job=job,
            plan=plan,
            execution=execution,
            review=None,
            revision_count=0,
            blocker=blocker,
            status="WAITING_FOR_APPROVAL" if waiting else "FAIL",
        )

    def _finish(
        self,
        *,
        machine: RoleStateMachine,
        job: dict[str, Any],
        plan: PlanResult | None,
        execution: ExecutionResult | None,
        review: ReviewResult | None,
        revision_count: int,
        blocker: str | None,
        status: str,
    ) -> RoleLoopResult:
        job = deepcopy(job)
        job["status"] = status
        job["blocker"] = blocker
        self._state["state_revision"] += 1
        self._state["active_job_id"] = (
            job["job_id"] if status == "WAITING_FOR_APPROVAL" else None
        )
        self._state["next_admissible_action"] = (
            "obtain explicit human approval"
            if status == "WAITING_FOR_APPROVAL"
            else None
        )
        if blocker and blocker not in self._state["blockers"]:
            self._state["blockers"].append(blocker)
        validate_instance("job.schema.json", job)
        validate_instance("project-state.schema.json", self._state)
        self._record_transition(
            job,
            action="role_loop_terminal",
            status=(
                "PASS"
                if status == "PASS"
                else "NEEDS_HUMAN_APPROVAL"
                if status == "WAITING_FOR_APPROVAL"
                else "FAIL"
            ),
            summary=blocker or "Planner / Executor / Reviewer loop completed",
            evidence_refs=list(execution.evidence_refs) if execution else [],
        )
        return RoleLoopResult(
            state=machine.state,
            job=job,
            project_state=deepcopy(self._state),
            plan=plan,
            execution=execution,
            review=review,
            revision_count=revision_count,
            audit_events=tuple(deepcopy(self._audit_events)),
            blocker=blocker,
        )

    def _record_model_call(
        self, job: dict[str, Any], role: EngineeringRole, response: ModelResponse
    ) -> None:
        self._record(
            self._audit.model_event(
                project_id=job["project_id"],
                gate_id=job.get("gate_id"),
                job_id=job["job_id"],
                role=role.value,
                provider=response.provider,
                runtime_version=response.runtime_version,
                model=response.model,
                ok=True,
                summary=f"{role.value} model response received",
                before_ref=self._repository_ref(),
                after_ref=self._repository_ref(),
            )
        )

    def _record_transition(
        self,
        job: dict[str, Any],
        *,
        action: str,
        status: str,
        summary: str,
        evidence_refs: list[str] | None = None,
    ) -> None:
        self._record(
            self._audit.state_event(
                project_id=job["project_id"],
                gate_id=job.get("gate_id"),
                job_id=job["job_id"],
                action=action,
                status=status,
                summary=summary,
                before_ref=self._repository_ref(),
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
        return f"{ref['branch']}@{ref.get('head_sha') or 'unknown'}"

    @staticmethod
    def _json_object(content: str, role: EngineeringRole) -> dict[str, Any]:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise SemanticValidationError(
                f"{role.value} returned invalid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise SemanticValidationError(
                f"{role.value} response must be a JSON object"
            )
        return payload

    @staticmethod
    def _string_tuple(value: Any, field_name: str) -> tuple[str, ...]:
        if not isinstance(value, list) or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            raise SemanticValidationError(
                f"{field_name} must be an array of non-empty strings"
            )
        return tuple(value)
