from __future__ import annotations

import unittest

from engineering_ai.models import (
    DeterministicModelRouter,
    ModelTaskClass,
    RouteStatus,
    accepted_registry,
)
from engineering_ai.supervisor import (
    BlackboardAuthority,
    BlackboardRecordKind,
    BlackboardValidationClass,
    ContextResolutionMode,
    HandoffRequest,
    Supervisor,
    TaskBlackboard,
)


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
        "current_gate": "010",
        "active_job_id": None,
        "repository_ref": {
            "branch": "gate-010-task-blackboard-handoffs",
            "head_sha": "0123456789abcdef0123456789abcdef01234567",
        },
        "architecture_baseline": "Gate 007",
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


def make_supervisor(*, max_records=1000):
    board = TaskBlackboard(max_records=max_records)
    router = DeterministicModelRouter(accepted_registry())
    supervisor = Supervisor(
        policy=policy(),
        state=state(),
        model_router=router,
        blackboard=board,
    )
    return supervisor, board


class TaskBlackboardTests(unittest.TestCase):
    def test_model_claim_is_advisory_not_evidence(self) -> None:
        supervisor, _ = make_supervisor()
        record = supervisor.blackboard_record_model_claim(
            task_id="task-1",
            model_id="qwen2.5-coder:7b-instruct",
            payload={"claim": "the patch is correct"},
        )
        self.assertEqual(record.authority, BlackboardAuthority.MODEL)
        self.assertEqual(
            record.validation_class, BlackboardValidationClass.ADVISORY
        )
        self.assertEqual(record.evidence_refs, ())

    def test_model_cannot_create_control_or_evidence_record(self) -> None:
        _, board = make_supervisor()
        with self.assertRaises(ValueError):
            board._append_model_record(
                task_id="task-1",
                model_id="worker-a",
                kind=BlackboardRecordKind.HANDOFF,
                payload={"target": "worker-b"},
            )
        with self.assertRaises(ValueError):
            board._append(
                task_id="task-1",
                kind=BlackboardRecordKind.DETERMINISTIC_EVIDENCE,
                authority=BlackboardAuthority.MODEL,
                actor_id="worker-a",
                validation_class=BlackboardValidationClass.DETERMINISTIC_EVIDENCE,
                payload={"context_keys": ("STATUS.md",)},
                evidence_refs=("ev-fake",),
            )

    def test_evidence_requires_tool_authority_and_reference(self) -> None:
        _, board = make_supervisor()
        with self.assertRaises(ValueError):
            board._append_evidence(
                task_id="task-1",
                tool_id="read_repository",
                context_keys=("STATUS.md",),
                summary="read completed",
                evidence_refs=(),
            )

    def test_blackboard_payload_is_immutable_to_worker_view(self) -> None:
        supervisor, _ = make_supervisor()
        record = supervisor.blackboard_record_model_claim(
            task_id="task-1",
            model_id="qwen3.5:9b",
            payload={"nested": {"value": "original"}},
        )
        view = supervisor.blackboard_view(task_id="task-1")
        self.assertEqual(view.records, (record,))
        with self.assertRaises(TypeError):
            view.records[0].payload["new"] = "mutation"  # type: ignore[index]
        with self.assertRaises(TypeError):
            view.records[0].payload["nested"]["value"] = "mutation"  # type: ignore[index]

    def test_blackboard_record_count_is_bounded(self) -> None:
        supervisor, _ = make_supervisor(max_records=1)
        supervisor.blackboard_assign_task(
            task_id="task-1",
            objective="inspect",
            requested_task_class=ModelTaskClass.GENERAL_PLANNING.value,
        )
        with self.assertRaises(RuntimeError):
            supervisor.blackboard_record_context_requirement(
                task_id="task-1",
                required_context_keys=("STATUS.md",),
            )

    def test_explicit_missing_context_prefers_deterministic_acquisition(self) -> None:
        supervisor, _ = make_supervisor()
        decision = supervisor.resolve_blackboard_context(
            task_id="task-1",
            required_context_keys=("STATUS.md", "src/foo.py"),
            requirements_are_explicit=True,
        )
        self.assertEqual(
            decision.mode, ContextResolutionMode.DETERMINISTIC_ACQUISITION
        )
        self.assertEqual(
            decision.missing_context_keys, ("STATUS.md", "src/foo.py")
        )
        self.assertIsNone(decision.route)

    def test_unknown_missing_context_routes_to_qwen35_tool_planner(self) -> None:
        supervisor, _ = make_supervisor()
        decision = supervisor.resolve_blackboard_context(
            task_id="task-1",
            required_context_keys=("repository-context",),
            requirements_are_explicit=False,
        )
        self.assertEqual(decision.mode, ContextResolutionMode.TOOL_PLANNER)
        self.assertIsNotNone(decision.route)
        assert decision.route is not None
        self.assertEqual(decision.route.status, RouteStatus.ROUTE)
        self.assertEqual(decision.route.model, "qwen3.5:9b")

    def test_ambiguous_tool_choice_routes_to_gpt_oss_escalation(self) -> None:
        supervisor, _ = make_supervisor()
        decision = supervisor.resolve_blackboard_context(
            task_id="task-1",
            required_context_keys=("unknown-engineering-context",),
            requirements_are_explicit=False,
            ambiguous_tool_choice=True,
        )
        self.assertEqual(decision.mode, ContextResolutionMode.DEEP_ESCALATION)
        self.assertIsNotNone(decision.route)
        assert decision.route is not None
        self.assertEqual(decision.route.status, RouteStatus.ROUTE)
        self.assertEqual(decision.route.model, "gpt-oss:20b")
        self.assertEqual(decision.route.reasoning_effort, "medium")

    def test_context_ready_needs_no_model_route(self) -> None:
        supervisor, _ = make_supervisor()
        supervisor.blackboard_record_evidence(
            task_id="task-1",
            tool_id="read_repository",
            context_keys=("STATUS.md",),
            summary="STATUS.md read",
            evidence_refs=("sha256:STATUS.md:abc",),
        )
        decision = supervisor.resolve_blackboard_context(
            task_id="task-1",
            required_context_keys=("STATUS.md",),
            requirements_are_explicit=True,
        )
        self.assertEqual(decision.mode, ContextResolutionMode.CONTEXT_READY)
        self.assertEqual(decision.missing_context_keys, ())
        self.assertIsNone(decision.route)

    def test_coder_handoff_rejected_when_required_context_missing(self) -> None:
        supervisor, _ = make_supervisor()
        decision = supervisor.create_model_handoff(
            HandoffRequest(
                task_id="task-1",
                target_task_class=ModelTaskClass.CODE_REPOSITORY,
                required_context_keys=("src/foo.py",),
                visible_record_ids=(),
            )
        )
        self.assertFalse(decision.created)
        self.assertEqual(decision.route.model, "qwen2.5-coder:7b-instruct")
        self.assertEqual(decision.missing_context_keys, ("src/foo.py",))

    def test_context_existing_but_not_visible_does_not_leak_into_handoff(self) -> None:
        supervisor, _ = make_supervisor()
        evidence = supervisor.blackboard_record_evidence(
            task_id="task-1",
            tool_id="read_repository",
            context_keys=("src/foo.py",),
            summary="source read",
            evidence_refs=("sha256:src/foo.py:abc",),
        )
        self.assertGreater(evidence.record_id, 0)
        decision = supervisor.create_model_handoff(
            HandoffRequest(
                task_id="task-1",
                target_task_class=ModelTaskClass.CODE_REPOSITORY,
                required_context_keys=("src/foo.py",),
                visible_record_ids=(),
            )
        )
        self.assertFalse(decision.created)
        self.assertEqual(decision.missing_context_keys, ("src/foo.py",))
        self.assertIsNotNone(decision.visible_view)
        assert decision.visible_view is not None
        self.assertEqual(decision.visible_view.records, ())

    def test_coder_handoff_created_only_with_explicit_visible_evidence(self) -> None:
        supervisor, _ = make_supervisor()
        task = supervisor.blackboard_assign_task(
            task_id="task-1",
            objective="repair foo",
            requested_task_class=ModelTaskClass.CODE_REPOSITORY.value,
        )
        evidence = supervisor.blackboard_record_evidence(
            task_id="task-1",
            tool_id="read_repository",
            context_keys=("src/foo.py", "tests/test_foo.py"),
            summary="required files read",
            evidence_refs=(
                "sha256:src/foo.py:abc",
                "sha256:tests/test_foo.py:def",
            ),
        )
        decision = supervisor.create_model_handoff(
            HandoffRequest(
                task_id="task-1",
                target_task_class=ModelTaskClass.CODE_REPOSITORY,
                required_context_keys=("src/foo.py", "tests/test_foo.py"),
                visible_record_ids=(task.record_id, evidence.record_id),
            )
        )
        self.assertTrue(decision.created)
        self.assertEqual(decision.route.model, "qwen2.5-coder:7b-instruct")
        self.assertEqual(decision.missing_context_keys, ())
        assert decision.handoff_record is not None
        self.assertEqual(
            decision.handoff_record.kind, BlackboardRecordKind.HANDOFF
        )
        self.assertEqual(
            decision.handoff_record.authority, BlackboardAuthority.SUPERVISOR
        )
        assert decision.visible_view is not None
        self.assertEqual(
            tuple(r.record_id for r in decision.visible_view.records),
            (task.record_id, evidence.record_id),
        )

    def test_coder_native_tool_handoff_is_no_route(self) -> None:
        supervisor, _ = make_supervisor()
        decision = supervisor.create_model_handoff(
            HandoffRequest(
                task_id="task-1",
                target_task_class=ModelTaskClass.CODE_REPOSITORY,
                requires_native_tool_proposals=True,
            )
        )
        self.assertFalse(decision.created)
        self.assertEqual(decision.route.status, RouteStatus.NO_ROUTE)
        self.assertIsNone(decision.route.model)

    def test_tool_proposal_written_by_model_stays_advisory_and_unexecuted(self) -> None:
        supervisor, _ = make_supervisor()
        record = supervisor.blackboard_record_tool_proposal(
            task_id="task-1",
            model_id="qwen3.5:9b",
            payload={
                "tool": "read_repository",
                "arguments": {"path": "STATUS.md"},
            },
        )
        self.assertEqual(record.kind, BlackboardRecordKind.TOOL_PROPOSAL)
        self.assertEqual(
            record.validation_class, BlackboardValidationClass.ADVISORY
        )
        self.assertEqual(supervisor.audit_events, ())

    def test_visible_records_cannot_cross_task_boundary(self) -> None:
        supervisor, _ = make_supervisor()
        other = supervisor.blackboard_record_evidence(
            task_id="task-other",
            tool_id="read_repository",
            context_keys=("src/foo.py",),
            summary="other task data",
            evidence_refs=("sha256:other:abc",),
        )
        decision = supervisor.create_model_handoff(
            HandoffRequest(
                task_id="task-1",
                target_task_class=ModelTaskClass.CODE_REPOSITORY,
                required_context_keys=("src/foo.py",),
                visible_record_ids=(other.record_id,),
            )
        )
        self.assertFalse(decision.created)
        self.assertEqual(decision.missing_context_keys, ("src/foo.py",))
        assert decision.visible_view is not None
        self.assertEqual(decision.visible_view.records, ())

    def test_electronics_kicad_roles_are_still_absent(self) -> None:
        names = {item.value for item in ModelTaskClass}
        self.assertNotIn("ELECTRONICS", names)
        self.assertNotIn("PCB", names)
        self.assertNotIn("KICAD", names)
        self.assertNotIn("VISION", names)


if __name__ == "__main__":
    unittest.main()
