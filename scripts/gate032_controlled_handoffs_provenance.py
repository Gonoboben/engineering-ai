from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

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
    DisagreementRequest,
    DisagreementState,
    EvidenceDisposition,
    HandoffRequest,
    IndependentReviewFinding,
    ReviewApplication,
    Supervisor,
    TaskBlackboard,
)


ROOT = Path(__file__).resolve().parents[1]


def run_checked(args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr or result.stdout or "no output"
        raise RuntimeError(f"command failed: {args!r}\n{detail}")
    return result


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


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
        "stop_conditions": ["approval boundary reached"],
        "retry_limit": 2,
    }


def state(head_sha: str) -> dict:
    return {
        "schema_version": "1.0",
        "state_revision": 1,
        "project_id": "engineering-ai",
        "current_gate": "032",
        "active_job_id": None,
        "repository_ref": {
            "branch": "gate-032-controlled-handoffs-provenance",
            "head_sha": head_sha,
        },
        "architecture_baseline": "Gate 007 / Gate 010 / Gate 011",
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


def main() -> int:
    for pattern in ("test_blackboard.py", "test_review_escalation.py"):
        run_checked(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                pattern,
            ]
        )

    head = run_checked(["git", "rev-parse", "HEAD"]).stdout.strip()
    require(len(head) == 40, "exact source revision was not resolved")
    source_ref = f"repo:Gonoboben/engineering-ai@{head}"

    board = TaskBlackboard()
    router = DeterministicModelRouter(accepted_registry())
    supervisor = Supervisor(
        policy=policy(),
        state=state(head),
        model_router=router,
        blackboard=board,
    )

    task_id = "gate032-controlled-handoff"
    assignment = supervisor.blackboard_assign_task(
        task_id=task_id,
        objective="review a bounded repository change and hand it to the code specialist",
        requested_task_class=ModelTaskClass.CODE_REPOSITORY.value,
    )
    planner_claim = supervisor.blackboard_record_model_claim(
        task_id=task_id,
        model_id="qwen3.5:9b",
        payload={"claim": "bounded source and test context is sufficient for code review"},
    )
    visible_evidence = supervisor.blackboard_record_evidence(
        task_id=task_id,
        tool_id="read_repository",
        context_keys=("src/example.py", "tests/test_example.py"),
        summary="exact bounded source and test inputs read",
        evidence_refs=(
            f"git:{head}:src/example.py",
            f"git:{head}:tests/test_example.py",
        ),
    )
    hidden_evidence = supervisor.blackboard_record_evidence(
        task_id=task_id,
        tool_id="read_repository",
        context_keys=("hidden-only-context",),
        summary="context intentionally excluded from the target worker view",
        evidence_refs=(f"git:{head}:hidden-only-context",),
    )

    coder_handoff = supervisor.create_model_handoff(
        HandoffRequest(
            task_id=task_id,
            target_task_class=ModelTaskClass.CODE_REPOSITORY,
            originating_role=ModelTaskClass.GENERAL_PLANNING.value,
            originating_model="qwen3.5:9b",
            originating_provider="ollama",
            source_version_refs=(source_ref,),
            required_context_keys=("src/example.py", "tests/test_example.py"),
            visible_record_ids=(
                assignment.record_id,
                planner_claim.record_id,
                visible_evidence.record_id,
            ),
        )
    )
    require(coder_handoff.created, "provenanced planner-to-coder handoff was not created")
    require(coder_handoff.handoff_record is not None, "handoff record missing")
    handoff_record = coder_handoff.handoff_record
    payload = handoff_record.payload
    require(
        handoff_record.authority is BlackboardAuthority.SUPERVISOR,
        "handoff is not Supervisor-authored",
    )
    require(payload["task_id"] == task_id, "task provenance missing")
    require(
        payload["originating_role"] == ModelTaskClass.GENERAL_PLANNING.value,
        "originating role provenance missing",
    )
    require(payload["originating_model"] == "qwen3.5:9b", "originating model missing")
    require(payload["originating_provider"] == "ollama", "originating provider missing")
    require(payload["target_role"] == ModelTaskClass.CODE_REPOSITORY.value, "target role missing")
    require(payload["target_model"] == "qwen2.5-coder:7b-instruct", "target model missing")
    require(payload["target_provider"] == "ollama", "target provider missing")
    require(
        tuple(payload["visible_record_ids"])
        == (
            assignment.record_id,
            planner_claim.record_id,
            visible_evidence.record_id,
        ),
        "visible context record provenance changed",
    )
    require(
        hidden_evidence.record_id not in payload["visible_record_ids"],
        "hidden context leaked into handoff",
    )
    require(
        set(payload["visible_evidence_refs"]) == set(visible_evidence.evidence_refs),
        "visible deterministic evidence references were not preserved",
    )
    require(source_ref in payload["source_version_refs"], "source revision identity missing")
    require(bool(payload["route_evidence_refs"]), "route qualification evidence missing")

    missing_context = supervisor.create_model_handoff(
        HandoffRequest(
            task_id=task_id,
            target_task_class=ModelTaskClass.CODE_REPOSITORY,
            originating_role=ModelTaskClass.GENERAL_PLANNING.value,
            originating_model="qwen3.5:9b",
            originating_provider="ollama",
            source_version_refs=(source_ref,),
            required_context_keys=("hidden-only-context",),
            visible_record_ids=(assignment.record_id, planner_claim.record_id),
        )
    )
    require(not missing_context.created, "missing visible context did not fail closed")
    require(
        missing_context.missing_context_keys == ("hidden-only-context",),
        "missing-context reason was not deterministic",
    )

    other_task_evidence = supervisor.blackboard_record_evidence(
        task_id="gate032-other-task",
        tool_id="read_repository",
        context_keys=("cross-task-context",),
        summary="different task evidence",
        evidence_refs=(f"git:{head}:cross-task-context",),
    )
    cross_task = supervisor.create_model_handoff(
        HandoffRequest(
            task_id=task_id,
            target_task_class=ModelTaskClass.CODE_REPOSITORY,
            originating_role=ModelTaskClass.GENERAL_PLANNING.value,
            originating_model="qwen3.5:9b",
            originating_provider="ollama",
            source_version_refs=(source_ref,),
            required_context_keys=("cross-task-context",),
            visible_record_ids=(assignment.record_id, other_task_evidence.record_id),
        )
    )
    require(not cross_task.created, "cross-task evidence silently satisfied context")
    require(
        cross_task.missing_context_keys == ("cross-task-context",),
        "cross-task context rejection was not explicit",
    )

    coder_native_tool = supervisor.create_model_handoff(
        HandoffRequest(
            task_id=task_id,
            target_task_class=ModelTaskClass.CODE_REPOSITORY,
            originating_role=ModelTaskClass.GENERAL_PLANNING.value,
            originating_model="qwen3.5:9b",
            originating_provider="ollama",
            source_version_refs=(source_ref,),
            visible_record_ids=(assignment.record_id, planner_claim.record_id),
            requires_native_tool_proposals=True,
        )
    )
    require(
        coder_native_tool.route.status is RouteStatus.NO_ROUTE
        and not coder_native_tool.created,
        "unqualified native-tool coder route did not fail closed",
    )

    peer_write_rejected = False
    try:
        board._append_model_record(
            task_id=task_id,
            model_id="qwen3.5:9b",
            kind=BlackboardRecordKind.HANDOFF,
            payload={"target_model": "qwen2.5-coder:7b-instruct"},
        )
    except ValueError:
        peer_write_rejected = True
    require(peer_write_rejected, "model was able to create a peer handoff")

    coder_claim = supervisor.blackboard_record_model_claim(
        task_id=task_id,
        model_id="qwen2.5-coder:7b-instruct",
        payload={"claim": "candidate change satisfies the bounded task"},
    )
    reviewer_evidence = supervisor.blackboard_record_evidence(
        task_id=task_id,
        tool_id="validator",
        context_keys=("validation-result",),
        summary="validator result remains inconclusive for the disputed advisory claim",
        evidence_refs=(f"validator:{head}:gate032",),
    )
    review_plan = supervisor.plan_disagreement_review(
        DisagreementRequest(
            task_id=task_id,
            claim_record_id=coder_claim.record_id,
            originating_model=coder_claim.actor_id,
            evidence_record_ids=(reviewer_evidence.record_id,),
            evidence_disposition=EvidenceDisposition.INCONCLUSIVE,
            source_version_refs=(source_ref,),
        )
    )
    require(review_plan.state is DisagreementState.REVIEW_REQUIRED, "review was not required")
    require(review_plan.review_handoff is not None, "review handoff missing")
    require(review_plan.review_handoff.created, "review handoff not created")
    require(
        review_plan.review_handoff.route.model == "gpt-oss:20b",
        "independent reviewer route changed",
    )
    require(
        review_plan.review_handoff.route.model != coder_claim.actor_id,
        "reviewer was not independent",
    )
    review_handoff_record = review_plan.review_handoff.handoff_record
    require(review_handoff_record is not None, "review provenance record missing")
    review_payload = review_handoff_record.payload
    require(
        review_payload["originating_role"] == ModelTaskClass.CODE_REPOSITORY.value,
        "review handoff lost originating role",
    )
    require(
        review_payload["originating_model"] == "qwen2.5-coder:7b-instruct"
        and review_payload["originating_provider"] == "ollama",
        "review handoff lost originating model/provider",
    )
    require(
        review_payload["target_role"] == ModelTaskClass.BASELINE_REASONING.value
        and review_payload["target_model"] == "gpt-oss:20b"
        and review_payload["target_provider"] == "ollama",
        "review handoff lost target provenance",
    )
    require(source_ref in review_payload["source_version_refs"], "review source revision missing")
    require(
        reviewer_evidence.evidence_refs[0] in review_payload["visible_evidence_refs"],
        "review handoff lost deterministic evidence refs",
    )

    applied = supervisor.apply_disagreement_review(
        ReviewApplication(
            task_id=task_id,
            disagreement_record_id=review_plan.disagreement_record.record_id,
            originating_model=coder_claim.actor_id,
            reviewer_model="gpt-oss:20b",
            finding=IndependentReviewFinding.NO_SUBSTANTIVE_CONFLICT,
            summary="no substantive advisory conflict after bounded independent review",
        )
    )
    require(
        applied.state is DisagreementState.RESOLVED_AFTER_REVIEW,
        "independent review workflow did not resolve as expected",
    )
    require(applied.review_record is not None, "review record missing")
    require(
        applied.review_record.validation_class is BlackboardValidationClass.ADVISORY,
        "model agreement was promoted beyond advisory",
    )
    require(
        applied.review_record.evidence_refs == (),
        "model agreement acquired deterministic evidence refs",
    )
    require(supervisor.audit_events == (), "handoff acceptance unexpectedly executed tools")

    result = {
        "gate": "032",
        "state": "PASS_V1_0_CONTROLLED_HANDOFFS_PROVENANCE",
        "source_revision": head,
        "provenance": {
            "task_id": payload["task_id"],
            "originating_role": payload["originating_role"],
            "originating_model": payload["originating_model"],
            "originating_provider": payload["originating_provider"],
            "target_role": payload["target_role"],
            "target_model": payload["target_model"],
            "target_provider": payload["target_provider"],
            "visible_record_ids": list(payload["visible_record_ids"]),
            "visible_evidence_refs": list(payload["visible_evidence_refs"]),
            "source_version_refs": list(payload["source_version_refs"]),
            "route_evidence_refs": list(payload["route_evidence_refs"]),
        },
        "assertions": {
            "supervisor_mediation": True,
            "direct_peer_to_peer_authority": False,
            "task_identity_preserved": True,
            "originating_role_model_provider_preserved": True,
            "target_role_model_provider_preserved": True,
            "visible_context_ids_preserved": True,
            "deterministic_evidence_refs_preserved": True,
            "source_version_identity_preserved": True,
            "hidden_context_rejected": True,
            "cross_task_context_rejected": True,
            "missing_required_context_fails_closed": True,
            "coder_native_tool_route_without_qualification": False,
            "reviewer_independence_preserved": True,
            "model_agreement_is_evidence": False,
            "new_model_qualification": False,
            "new_tool_authority": False,
            "new_git_authority": False,
            "new_network_authority": False,
            "release_authority": False,
            "fabrication_authority": False,
        },
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
