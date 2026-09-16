from __future__ import annotations

import json
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from itertools import count
from pathlib import Path

from engineering_ai.supervisor import (
    AuditEmitter,
    Decision,
    StubTool,
    Supervisor,
    ToolOutcome,
)
from engineering_ai.supervisor.policy import PolicyEngine
from engineering_ai.validation import SemanticValidationError, validate_instance


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def load_fixture(name: str) -> dict:
    with (FIXTURES / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def make_policy() -> dict:
    return load_fixture("valid_policy.json")


def make_state() -> dict:
    state = load_fixture("valid_state.json")
    state["current_gate"] = "003"
    state["active_job_id"] = None
    state["repository_ref"] = {
        "branch": "gate-003-deterministic-supervisor",
        "head_sha": "90df86ceebfb3ee6166a959fcf84172e989c646a",
    }
    state["pending_checks"] = []
    state["blockers"] = []
    state["next_admissible_action"] = None
    return state


def make_job(action: str = "read_repository", retry_limit: int = 2) -> dict:
    job = load_fixture("valid_job.json")
    job["job_id"] = "gate-003-supervisor-test"
    job["gate_id"] = "003"
    job["objective"] = "Exercise deterministic Supervisor behavior"
    job["scope"] = ["deterministic supervisor"]
    job["out_of_scope"] = ["LLM integration"]
    job["requested_actions"] = [action]
    job["required_validators"] = []
    job["retry_limit"] = retry_limit
    job["attempts"] = 0
    job["status"] = "QUEUED"
    job["blocker"] = None
    return job


def make_audit_emitter() -> AuditEmitter:
    ids = count(1)
    fixed = datetime(2026, 9, 16, 19, 45, tzinfo=timezone.utc)
    return AuditEmitter(
        clock=lambda: fixed,
        event_id_factory=lambda: f"evt-{next(ids):03d}",
        supervisor_id="test-supervisor",
    )


class SupervisorTests(unittest.TestCase):
    def test_autonomous_action_executes_and_emits_valid_audit(self) -> None:
        tool = StubTool(ToolOutcome(True, "repository inspected", ("ev-read-1",)))
        supervisor = Supervisor(
            policy=make_policy(), state=make_state(), audit_emitter=make_audit_emitter()
        )

        result = supervisor.execute(
            job=make_job("read_repository"), action="read_repository", tool=tool
        )

        self.assertEqual(result.decision.decision, Decision.ALLOW)
        self.assertTrue(result.tool_called)
        self.assertEqual(tool.calls, ["read_repository"])
        self.assertEqual(result.job["status"], "PASS")
        self.assertIsNone(result.state["active_job_id"])
        self.assertEqual(len(result.audit_events), 3)
        for event in result.audit_events:
            validate_instance("audit-event.schema.json", event)

    def test_forbidden_action_is_blocked_before_tool_call(self) -> None:
        tool = StubTool(ToolOutcome(True, "must never execute"))
        supervisor = Supervisor(
            policy=make_policy(), state=make_state(), audit_emitter=make_audit_emitter()
        )

        result = supervisor.execute(
            job=make_job("validator_weakening"),
            action="validator_weakening",
            tool=tool,
        )

        self.assertEqual(result.decision.decision, Decision.DENY)
        self.assertFalse(result.tool_called)
        self.assertEqual(tool.calls, [])
        self.assertEqual(result.job["status"], "BLOCKED")
        self.assertEqual(len(result.audit_events), 2)

    def test_approval_required_action_waits_then_executes_with_named_approval(self) -> None:
        state = make_state()
        state["blockers"] = ["external project blocker"]
        tool = StubTool(ToolOutcome(True, "approved architecture action executed"))
        supervisor = Supervisor(
            policy=make_policy(), state=state, audit_emitter=make_audit_emitter()
        )
        job = make_job("architecture_change")

        waiting = supervisor.execute(job=job, action="architecture_change", tool=tool)
        self.assertEqual(waiting.decision.decision, Decision.NEEDS_HUMAN_APPROVAL)
        self.assertEqual(waiting.job["status"], "WAITING_FOR_APPROVAL")
        self.assertFalse(waiting.tool_called)
        self.assertEqual(tool.calls, [])
        self.assertTrue(
            any(
                blocker.startswith("human approval required")
                for blocker in waiting.state["blockers"]
            )
        )

        approved = supervisor.execute(
            job=waiting.job,
            action="architecture_change",
            tool=tool,
            approval_obtained=True,
            approver="human-owner",
        )
        self.assertEqual(approved.decision.decision, Decision.ALLOW)
        self.assertEqual(approved.job["status"], "PASS")
        self.assertEqual(tool.calls, ["architecture_change"])
        self.assertIn("external project blocker", approved.state["blockers"])
        self.assertFalse(
            any(
                blocker.startswith("human approval required")
                for blocker in approved.state["blockers"]
            )
        )

    def test_asserted_approval_without_approver_identity_does_not_execute(self) -> None:
        tool = StubTool(ToolOutcome(True, "must not execute"))
        supervisor = Supervisor(
            policy=make_policy(), state=make_state(), audit_emitter=make_audit_emitter()
        )

        result = supervisor.execute(
            job=make_job("physics_change"),
            action="physics_change",
            tool=tool,
            approval_obtained=True,
            approver=None,
        )

        self.assertEqual(result.decision.decision, Decision.NEEDS_HUMAN_APPROVAL)
        self.assertFalse(result.tool_called)
        self.assertEqual(tool.calls, [])

    def test_action_not_declared_by_job_is_denied(self) -> None:
        tool = StubTool(ToolOutcome(True, "must not execute"))
        supervisor = Supervisor(
            policy=make_policy(), state=make_state(), audit_emitter=make_audit_emitter()
        )

        result = supervisor.execute(
            job=make_job("read_repository"), action="run_validator", tool=tool
        )

        self.assertEqual(result.decision.decision, Decision.DENY)
        self.assertFalse(result.tool_called)
        self.assertEqual(tool.calls, [])

    def test_retry_exhaustion_reaches_fail_without_unbounded_loop(self) -> None:
        tool = StubTool(ToolOutcome(False, "synthetic stub failure", ("ev-fail",)))
        supervisor = Supervisor(
            policy=make_policy(), state=make_state(), audit_emitter=make_audit_emitter()
        )
        job = make_job("read_repository", retry_limit=2)

        first = supervisor.execute(job=job, action="read_repository", tool=tool)
        self.assertEqual(first.job["status"], "QUEUED")
        self.assertEqual(first.job["attempts"], 1)

        second = supervisor.execute(
            job=first.job, action="read_repository", tool=tool
        )
        self.assertEqual(second.job["status"], "QUEUED")
        self.assertEqual(second.job["attempts"], 2)

        third = supervisor.execute(
            job=second.job, action="read_repository", tool=tool
        )
        self.assertEqual(third.job["status"], "FAIL")
        self.assertEqual(third.job["attempts"], 2)
        self.assertEqual(len(tool.calls), 3)

    def test_effective_state_cannot_relax_policy_forbidden_action(self) -> None:
        state = make_state()
        state["effective_permissions"]["forbidden"].remove("validator_weakening")
        state["effective_permissions"]["approval_required"].append(
            "validator_weakening"
        )

        with self.assertRaises(SemanticValidationError):
            PolicyEngine(make_policy(), state)

    def test_job_retry_limit_cannot_exceed_project_policy(self) -> None:
        supervisor = Supervisor(
            policy=make_policy(), state=make_state(), audit_emitter=make_audit_emitter()
        )
        tool = StubTool(ToolOutcome(True, "ok"))
        job = make_job("read_repository", retry_limit=4)

        with self.assertRaises(SemanticValidationError):
            supervisor.execute(job=job, action="read_repository", tool=tool)

    def test_state_snapshot_cannot_mutate_supervisor_authoritative_state(self) -> None:
        supervisor = Supervisor(
            policy=make_policy(), state=make_state(), audit_emitter=make_audit_emitter()
        )
        snapshot = supervisor.state
        snapshot["effective_permissions"]["autonomous"].append("architecture_change")
        snapshot["blockers"].append("injected blocker")

        authoritative = supervisor.state
        self.assertNotIn(
            "architecture_change", authoritative["effective_permissions"]["autonomous"]
        )
        self.assertNotIn("injected blocker", authoritative["blockers"])

    def test_identical_inputs_produce_identical_results_with_fixed_audit_sources(self) -> None:
        def run_once():
            supervisor = Supervisor(
                policy=deepcopy(make_policy()),
                state=deepcopy(make_state()),
                audit_emitter=make_audit_emitter(),
            )
            tool = StubTool(ToolOutcome(True, "deterministic", ("ev-deterministic",)))
            return supervisor.execute(
                job=make_job("read_repository"),
                action="read_repository",
                tool=tool,
            )

        first = run_once()
        second = run_once()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
