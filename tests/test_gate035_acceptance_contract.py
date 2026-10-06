from __future__ import annotations

import json
import unittest

from engineering_ai.models import ModelResponse, ModelToolCall, ModelToolSpec
from engineering_ai.supervisor import (
    LoopState,
    PlannerExecutorReviewerLoop,
    RoleModelConfig,
    Supervisor,
    ToolOutcome,
    ValidatorOutcome,
)
from engineering_ai.validation import SemanticValidationError


HEAD = "6db84082e45f3e00a555f5af79f66c1fc6b48ea6"
OTHER_HEAD = "1" * 40


def policy() -> dict:
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
        "stop_conditions": [
            "approval boundary reached",
            "required validator failure",
        ],
        "retry_limit": 2,
    }


def state() -> dict:
    return {
        "schema_version": "1.0",
        "state_revision": 1,
        "project_id": "engineering-ai",
        "current_gate": "035",
        "active_job_id": None,
        "repository_ref": {
            "branch": "gate-035-deterministic-acceptance-contract-conformance",
            "head_sha": HEAD,
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


def job(*, required: tuple[str, ...] = ("schema-suite",)) -> dict:
    return {
        "schema_version": "1.0",
        "job_id": "gate-035-acceptance-contract",
        "project_id": "engineering-ai",
        "gate_id": "035",
        "objective": "Prove deterministic acceptance-contract conformance",
        "scope": ["generic Supervisor completion"],
        "out_of_scope": ["project-specific validator semantics"],
        "requested_actions": ["read_repository", "run_validator"],
        "required_validators": list(required),
        "retry_limit": 1,
        "attempts": 0,
        "status": "QUEUED",
        "blocker": None,
    }


def validator(
    *,
    state_value: str = "PASS",
    evidence: tuple[str, ...] = ("ev-schema-suite",),
    sha: str | None = HEAD,
    timed_out: bool = False,
) -> ValidatorOutcome:
    return ValidatorOutcome(
        validator_id="schema-suite",
        state=state_value,
        evidence_refs=evidence,
        repository_head_sha=sha,
        timed_out=timed_out,
    )


class FakeProvider:
    provider_name = "fake"

    def __init__(self, responses):
        self.responses = list(responses)

    def runtime_version(self):
        return "fake-1"

    def runtime_diagnostics(self):
        return {"provider": "fake", "runtime_version": "fake-1"}

    def chat(self, request, *, timeout_seconds=300.0):
        if not self.responses:
            raise AssertionError("unexpected model call")
        item = self.responses.pop(0)
        return ModelResponse(
            provider="fake",
            runtime_version="fake-1",
            model=request.model,
            content=json.dumps(item.get("content", {})),
            tool_calls=tuple(item.get("tool_calls", ())),
            done_reason="stop",
        )


READ_SPEC = ModelToolSpec(
    name="read_repository",
    description="read one repository object",
    parameters={"type": "object", "properties": {"path": {"type": "string"}}},
)


def accepted_provider() -> FakeProvider:
    return FakeProvider(
        [
            {
                "content": {
                    "steps": ["inspect"],
                    "allowed_actions": ["read_repository"],
                }
            },
            {
                "content": {"summary": "inspection complete"},
                "tool_calls": [
                    ModelToolCall("read_repository", {"path": "STATUS.md"})
                ],
            },
            {
                "content": {
                    "decision": "ACCEPT",
                    "summary": "supplied evidence is acceptable",
                }
            },
        ]
    )


class Gate035AcceptanceContractTests(unittest.TestCase):
    def test_tool_success_without_required_validator_is_blocked(self) -> None:
        supervisor = Supervisor(policy=policy(), state=state())
        result = supervisor.execute(
            job=job(),
            action="read_repository",
            tool=lambda action: ToolOutcome(True, "read ok", ("ev-read",)),
        )
        self.assertEqual(result.job["status"], "BLOCKED")
        self.assertIn("schema-suite=MISSING", result.job["blocker"])

    def test_required_validator_failure_is_fail(self) -> None:
        supervisor = Supervisor(policy=policy(), state=state())
        result = supervisor.execute(
            job=job(),
            action="run_validator",
            tool=lambda action: ToolOutcome(
                True,
                "validator completed",
                validator_results=(validator(state_value="FAIL"),),
            ),
        )
        self.assertEqual(result.job["status"], "FAIL")
        self.assertIn("schema-suite=FAIL", result.job["blocker"])

    def test_timed_out_validator_cannot_close_job(self) -> None:
        supervisor = Supervisor(policy=policy(), state=state())
        result = supervisor.execute(
            job=job(),
            action="run_validator",
            tool=lambda action: ToolOutcome(
                True,
                "validator timed out",
                validator_results=(
                    validator(
                        state_value="NOT_RUN",
                        evidence=(),
                        timed_out=True,
                    ),
                ),
            ),
        )
        self.assertEqual(result.job["status"], "BLOCKED")
        self.assertIn("schema-suite=TIMEOUT", result.job["blocker"])

    def test_pass_from_other_revision_cannot_close_job(self) -> None:
        supervisor = Supervisor(policy=policy(), state=state())
        result = supervisor.execute(
            job=job(),
            action="run_validator",
            tool=lambda action: ToolOutcome(
                True,
                "validator pass from wrong revision",
                validator_results=(validator(sha=OTHER_HEAD),),
            ),
        )
        self.assertEqual(result.job["status"], "BLOCKED")
        self.assertIn("REVISION_MISMATCH", result.job["blocker"])

    def test_fail_from_other_revision_cannot_fail_current_job(self) -> None:
        supervisor = Supervisor(policy=policy(), state=state())
        result = supervisor.execute(
            job=job(),
            action="run_validator",
            tool=lambda action: ToolOutcome(
                True,
                "stale validator failure",
                validator_results=(
                    validator(state_value="FAIL", sha=OTHER_HEAD),
                ),
            ),
        )
        self.assertEqual(result.job["status"], "BLOCKED")
        self.assertIn("REVISION_MISMATCH", result.job["blocker"])

    def test_fail_without_evidence_cannot_fail_current_job(self) -> None:
        supervisor = Supervisor(policy=policy(), state=state())
        result = supervisor.execute(
            job=job(),
            action="run_validator",
            tool=lambda action: ToolOutcome(
                True,
                "validator failure without evidence",
                validator_results=(
                    validator(state_value="FAIL", evidence=()),
                ),
            ),
        )
        self.assertEqual(result.job["status"], "BLOCKED")
        self.assertIn("FAIL_WITHOUT_EVIDENCE", result.job["blocker"])

    def test_pass_without_evidence_cannot_close_job(self) -> None:
        supervisor = Supervisor(policy=policy(), state=state())
        result = supervisor.execute(
            job=job(),
            action="run_validator",
            tool=lambda action: ToolOutcome(
                True,
                "validator claims pass without evidence",
                validator_results=(validator(evidence=()),),
            ),
        )
        self.assertEqual(result.job["status"], "BLOCKED")
        self.assertIn("PASS_WITHOUT_EVIDENCE", result.job["blocker"])

    def test_exact_revision_evidence_closes_required_validator(self) -> None:
        supervisor = Supervisor(policy=policy(), state=state())
        blocked = supervisor.execute(
            job=job(),
            action="read_repository",
            tool=lambda action: ToolOutcome(True, "read ok", ("ev-read",)),
        )
        self.assertEqual(blocked.job["status"], "BLOCKED")

        passed = supervisor.execute(
            job=blocked.job,
            action="run_validator",
            tool=lambda action: ToolOutcome(
                True,
                "validator pass",
                validator_results=(validator(),),
            ),
        )
        self.assertEqual(passed.job["status"], "PASS")
        schema_state = next(
            item
            for item in passed.state["validation_states"]
            if item["check_id"] == "schema-suite"
        )
        self.assertEqual(schema_state["state"], "PASS")
        self.assertEqual(schema_state["repository_head_sha"], HEAD)
        self.assertEqual(schema_state["evidence_refs"], ["ev-schema-suite"])
        self.assertNotIn("schema-suite", passed.state["pending_checks"])

    def test_no_required_validator_path_remains_valid(self) -> None:
        supervisor = Supervisor(policy=policy(), state=state())
        result = supervisor.execute(
            job=job(required=()),
            action="read_repository",
            tool=lambda action: ToolOutcome(True, "read ok", ("ev-read",)),
        )
        self.assertEqual(result.job["status"], "PASS")

    def test_undeclared_validator_result_is_rejected(self) -> None:
        supervisor = Supervisor(policy=policy(), state=state())
        foreign = ValidatorOutcome(
            validator_id="foreign-validator",
            state="PASS",
            evidence_refs=("ev-foreign",),
            repository_head_sha=HEAD,
        )
        with self.assertRaises(SemanticValidationError):
            supervisor.execute(
                job=job(),
                action="run_validator",
                tool=lambda action: ToolOutcome(
                    True,
                    "foreign validator",
                    validator_results=(foreign,),
                ),
            )

    def test_reviewer_accept_cannot_bypass_missing_required_validator(self) -> None:
        loop = PlannerExecutorReviewerLoop(
            policy=policy(),
            state=state(),
            provider=accepted_provider(),
            model_config=RoleModelConfig(model="test-model"),
            tool_specs={"read_repository": READ_SPEC},
            tool_executors={
                "read_repository": lambda args: ToolOutcome(
                    True,
                    "read ok",
                    ("ev-read",),
                )
            },
        )
        result = loop.run(job=job(), user_task="Inspect STATUS.md")
        self.assertEqual(result.state, LoopState.FAIL)
        self.assertEqual(result.job["status"], "BLOCKED")
        self.assertIn("schema-suite=MISSING", result.blocker)

    def test_reviewer_accept_with_exact_validator_evidence_can_pass(self) -> None:
        loop = PlannerExecutorReviewerLoop(
            policy=policy(),
            state=state(),
            provider=accepted_provider(),
            model_config=RoleModelConfig(model="test-model"),
            tool_specs={"read_repository": READ_SPEC},
            tool_executors={
                "read_repository": lambda args: ToolOutcome(
                    True,
                    "read and validate",
                    ("ev-read",),
                    validator_results=(validator(),),
                )
            },
        )
        result = loop.run(job=job(), user_task="Inspect STATUS.md")
        self.assertEqual(result.state, LoopState.COMPLETE)
        self.assertEqual(result.job["status"], "PASS")
        self.assertEqual(
            result.execution.validator_results[0].validator_id,
            "schema-suite",
        )
        schema_state = next(
            item
            for item in result.project_state["validation_states"]
            if item["check_id"] == "schema-suite"
        )
        self.assertEqual(schema_state["repository_head_sha"], HEAD)
        self.assertEqual(schema_state["state"], "PASS")


if __name__ == "__main__":
    unittest.main()
