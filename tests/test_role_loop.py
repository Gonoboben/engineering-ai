from __future__ import annotations

import json
import unittest
from copy import deepcopy

from engineering_ai.models import ModelResponse, ModelToolCall, ModelToolSpec
from engineering_ai.supervisor import (
    LoopState,
    PlannerExecutorReviewerLoop,
    ReviewDecision,
    RoleModelConfig,
    RoleStateMachine,
    ToolOutcome,
)
from engineering_ai.validation import SemanticValidationError


def policy():
    return {
        "schema_version": "1.0",
        "policy_version": "1.0",
        "project_id": "engineering-ai",
        "autonomous_actions": ["read_repository", "run_validator"],
        "approval_required_actions": [
            "architecture_change",
            "physics_change",
            "destructive_action",
            "fabrication_authorization",
            "release_authorization",
            "external_disclosure",
            "scope_expansion",
        ],
        "forbidden_actions": ["validator_weakening"],
        "mandatory_validators": [],
        "stop_conditions": ["approval boundary reached"],
        "retry_limit": 2,
    }


def state():
    return {
        "schema_version": "1.0",
        "state_revision": 1,
        "project_id": "engineering-ai",
        "current_gate": "006",
        "active_job_id": None,
        "repository_ref": {
            "branch": "gate-006-planner-executor-reviewer",
            "head_sha": "6f058aa395c13d169ac322d46b5d6cac6c73d299",
        },
        "architecture_baseline": "Gate 001",
        "effective_permissions": {
            "autonomous": ["read_repository", "run_validator"],
            "approval_required": [
                "architecture_change",
                "physics_change",
                "destructive_action",
                "fabrication_authorization",
                "release_authorization",
                "external_disclosure",
                "scope_expansion",
            ],
            "forbidden": ["validator_weakening"],
        },
        "pending_checks": [],
        "blockers": [],
        "validation_states": [
            {
                "check_id": "physical-validation",
                "validation_class": "PHYSICAL",
                "state": "PHYSICAL_NOT_EXECUTED",
                "evidence_refs": [],
            }
        ],
        "next_admissible_action": None,
    }


def job(actions=None):
    return {
        "schema_version": "1.0",
        "job_id": "gate-006-role-loop-test",
        "project_id": "engineering-ai",
        "gate_id": "006",
        "objective": "Prove deterministic role-loop behavior",
        "scope": ["role loop"],
        "out_of_scope": ["project writes"],
        "requested_actions": actions or ["read_repository"],
        "required_validators": [],
        "retry_limit": 1,
        "attempts": 0,
        "status": "QUEUED",
        "blocker": None,
    }


class FakeProvider:
    provider_name = "fake"

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def runtime_version(self):
        return "fake-1"

    def runtime_diagnostics(self):
        return {"provider": "fake", "runtime_version": "fake-1"}

    def chat(self, request, *, timeout_seconds=300.0):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("unexpected model call")
        item = self.responses.pop(0)
        return ModelResponse(
            provider="fake",
            runtime_version="fake-1",
            model=request.model,
            content=(
                item["raw_content"]
                if "raw_content" in item
                else json.dumps(item.get("content", {}))
            ),
            tool_calls=tuple(item.get("tool_calls", ())),
            done_reason="stop",
        )


READ_SPEC = ModelToolSpec(
    name="read_repository",
    description="read one repository object",
    parameters={"type": "object", "properties": {"path": {"type": "string"}}},
)
ARCH_SPEC = ModelToolSpec(
    name="architecture_change",
    description="architecture change proposal",
    parameters={"type": "object", "properties": {}},
)


def make_loop(provider, *, executors=None, specs=None, max_revisions=1):
    return PlannerExecutorReviewerLoop(
        policy=policy(),
        state=state(),
        provider=provider,
        model_config=RoleModelConfig(model="gpt-oss:20b"),
        tool_specs=specs or {"read_repository": READ_SPEC},
        tool_executors=executors
        or {"read_repository": lambda args: ToolOutcome(True, "read ok", ("ev-read",))},
        max_revisions=max_revisions,
    )


class RoleLoopTests(unittest.TestCase):
    def test_accept_requires_deterministic_evidence_and_records_role_identity(self):
        provider = FakeProvider(
            [
                {"content": {"steps": ["inspect"], "allowed_actions": ["read_repository"]}},
                {
                    "content": {"summary": "propose inspection"},
                    "tool_calls": [ModelToolCall("read_repository", {"path": "STATUS.md"})],
                },
                {"content": {"decision": "ACCEPT", "summary": "evidence is sufficient"}},
            ]
        )
        result = make_loop(provider).run(job=job(), user_task="Inspect STATUS.md")

        self.assertEqual(result.state, LoopState.COMPLETE)
        self.assertEqual(result.job["status"], "PASS")
        self.assertEqual(result.execution.evidence_refs, ("ev-read",))
        model_events = [e for e in result.audit_events if e["event_type"] == "MODEL_CALL"]
        self.assertEqual(len(model_events), 3)
        self.assertEqual(
            [e["actor"]["id"].split(":")[0] for e in model_events],
            ["PLANNER", "EXECUTOR", "REVIEWER"],
        )
        self.assertTrue(all(e["actor"]["kind"] == "model" for e in model_events))
        self.assertEqual(
            [request.messages[0].content.split(".")[0] for request in provider.requests],
            ["You are PLANNER", "You are EXECUTOR", "You are REVIEWER"],
        )

    def test_tool_only_executor_response_is_valid_and_remains_supervisor_gated(self):
        provider = FakeProvider(
            [
                {"content": {"steps": ["inspect"], "allowed_actions": ["read_repository"]}},
                {
                    "raw_content": "",
                    "tool_calls": [ModelToolCall("read_repository", {"path": "STATUS.md"})],
                },
                {"content": {"decision": "ACCEPT", "summary": "evidence is sufficient"}},
            ]
        )
        result = make_loop(provider).run(job=job(), user_task="Inspect STATUS.md")
        self.assertEqual(result.state, LoopState.COMPLETE)
        self.assertEqual(result.job["status"], "PASS")
        self.assertEqual(result.execution.executed_actions, ("read_repository",))
        self.assertEqual(result.execution.evidence_refs, ("ev-read",))
        self.assertEqual(result.execution.summary, "executor proposed 1 tool call")

    def test_missing_evidence_cannot_be_promoted_to_pass(self):
        provider = FakeProvider(
            [
                {"content": {"steps": ["inspect"], "allowed_actions": []}},
                {"content": {"summary": "no deterministic action"}},
            ]
        )
        result = make_loop(provider).run(job=job(), user_task="Inspect without tools")
        self.assertEqual(result.state, LoopState.FAIL)
        self.assertEqual(result.job["status"], "FAIL")
        self.assertIn("missing deterministic evidence", result.blocker)

    def test_reviewer_revision_is_bounded(self):
        provider = FakeProvider(
            [
                {"content": {"steps": ["inspect"], "allowed_actions": ["read_repository"]}},
                {
                    "content": {"summary": "first"},
                    "tool_calls": [ModelToolCall("read_repository", {"path": "STATUS.md"})],
                },
                {"content": {"decision": "REVISE", "summary": "inspect again"}},
                {"content": {"steps": ["inspect again"], "allowed_actions": ["read_repository"]}},
                {
                    "content": {"summary": "second"},
                    "tool_calls": [ModelToolCall("read_repository", {"path": "STATUS.md"})],
                },
                {"content": {"decision": "REVISE", "summary": "again"}},
            ]
        )
        result = make_loop(provider, max_revisions=1).run(
            job=job(), user_task="Bound revisions"
        )
        self.assertEqual(result.state, LoopState.FAIL)
        self.assertEqual(result.revision_count, 1)
        self.assertIn("revision limit", result.blocker)

    def test_approval_required_tool_proposal_stops_before_execution(self):
        provider = FakeProvider(
            [
                {"content": {"steps": ["change architecture"], "allowed_actions": ["architecture_change"]}},
                {
                    "content": {"summary": "proposal only"},
                    "tool_calls": [ModelToolCall("architecture_change", {})],
                },
            ]
        )
        called = []
        loop = make_loop(
            provider,
            specs={"architecture_change": ARCH_SPEC},
            executors={"architecture_change": lambda args: called.append(args)},
        )
        result = loop.run(
            job=job(["architecture_change"]), user_task="Change architecture"
        )
        self.assertEqual(result.state, LoopState.WAITING_FOR_APPROVAL)
        self.assertEqual(result.job["status"], "WAITING_FOR_APPROVAL")
        self.assertEqual(called, [])

    def test_executor_cannot_escape_approved_plan(self):
        provider = FakeProvider(
            [
                {"content": {"steps": ["inspect"], "allowed_actions": ["read_repository"]}},
                {
                    "content": {"summary": "attempt escape"},
                    "tool_calls": [ModelToolCall("run_validator", {})],
                },
            ]
        )
        loop = PlannerExecutorReviewerLoop(
            policy=policy(),
            state=state(),
            provider=provider,
            model_config=RoleModelConfig(model="gpt-oss:20b"),
            tool_specs={
                "read_repository": READ_SPEC,
                "run_validator": ModelToolSpec(
                    "run_validator", "validator", {"type": "object", "properties": {}}
                ),
            },
            tool_executors={
                "read_repository": lambda args: ToolOutcome(True, "ok", ("ev",)),
                "run_validator": lambda args: ToolOutcome(True, "must not run", ("ev2",)),
            },
        )
        result = loop.run(
            job=job(["read_repository", "run_validator"]), user_task="Stay in plan"
        )
        self.assertEqual(result.state, LoopState.FAIL)
        self.assertIn("outside approved plan", result.blocker)

    def test_reviewer_reject_is_terminal_fail(self):
        provider = FakeProvider(
            [
                {"content": {"steps": ["inspect"], "allowed_actions": ["read_repository"]}},
                {
                    "content": {"summary": "inspection complete"},
                    "tool_calls": [ModelToolCall("read_repository", {"path": "STATUS.md"})],
                },
                {"content": {"decision": "REJECT", "summary": "evidence disproves result"}},
            ]
        )
        result = make_loop(provider).run(job=job(), user_task="Reject on evidence")
        self.assertEqual(result.state, LoopState.FAIL)
        self.assertEqual(result.review.decision, ReviewDecision.REJECT)
        self.assertIn("reviewer rejected", result.blocker)

    def test_illegal_transition_is_rejected(self):
        machine = RoleStateMachine()
        with self.assertRaises(SemanticValidationError):
            machine.transition(LoopState.REVIEW)


if __name__ == "__main__":
    unittest.main()
