from __future__ import annotations

import unittest

from engineering_ai.models import (
    DeterministicModelRouter,
    ModelTaskClass,
    accepted_registry,
)
from engineering_ai.supervisor import (
    BlackboardValidationClass,
    DisagreementRequest,
    DisagreementState,
    EvidenceDisposition,
    IndependentReviewFinding,
    ReviewApplication,
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
        "current_gate": "011",
        "active_job_id": None,
        "repository_ref": {
            "branch": "gate-011-independent-review-escalation",
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


def make_supervisor():
    board = TaskBlackboard()
    router = DeterministicModelRouter(accepted_registry())
    supervisor = Supervisor(
        policy=policy(),
        state=state(),
        model_router=router,
        blackboard=board,
    )
    return supervisor, board


class IndependentReviewTests(unittest.TestCase):
    def _claim(self, supervisor, model="qwen2.5-coder:7b-instruct"):
        return supervisor.blackboard_record_model_claim(
            task_id="task-1",
            model_id=model,
            payload={"claim": "candidate result is correct"},
        )

    def _evidence(self, supervisor):
        return supervisor.blackboard_record_evidence(
            task_id="task-1",
            tool_id="validator",
            context_keys=("validation-result",),
            summary="deterministic validator result",
            evidence_refs=("validator:task-1:001",),
        )

    def test_supporting_evidence_resolves_without_model_review(self) -> None:
        supervisor, _ = make_supervisor()
        claim = self._claim(supervisor)
        evidence = self._evidence(supervisor)
        decision = supervisor.plan_disagreement_review(
            DisagreementRequest(
                task_id="task-1",
                claim_record_id=claim.record_id,
                originating_model=claim.actor_id,
                evidence_record_ids=(evidence.record_id,),
                evidence_disposition=EvidenceDisposition.SUPPORTS_CLAIM,
            )
        )
        self.assertEqual(decision.state, DisagreementState.RESOLVED_BY_EVIDENCE)
        self.assertEqual(
            decision.claim_outcome, "SUPPORTED_BY_DETERMINISTIC_EVIDENCE"
        )
        self.assertIsNone(decision.review_handoff)

    def test_contradicting_evidence_rejects_claim_without_vote(self) -> None:
        supervisor, _ = make_supervisor()
        claim = self._claim(supervisor)
        evidence = self._evidence(supervisor)
        decision = supervisor.plan_disagreement_review(
            DisagreementRequest(
                task_id="task-1",
                claim_record_id=claim.record_id,
                originating_model=claim.actor_id,
                evidence_record_ids=(evidence.record_id,),
                evidence_disposition=EvidenceDisposition.CONTRADICTS_CLAIM,
            )
        )
        self.assertEqual(decision.state, DisagreementState.RESOLVED_BY_EVIDENCE)
        self.assertEqual(
            decision.claim_outcome, "REJECTED_BY_DETERMINISTIC_EVIDENCE"
        )
        self.assertIsNone(decision.review_handoff)

    def test_qwen_claim_with_inconclusive_evidence_routes_to_gpt_oss(self) -> None:
        supervisor, _ = make_supervisor()
        claim = self._claim(supervisor, "qwen3.5:9b")
        evidence = self._evidence(supervisor)
        decision = supervisor.plan_disagreement_review(
            DisagreementRequest(
                task_id="task-1",
                claim_record_id=claim.record_id,
                originating_model=claim.actor_id,
                evidence_record_ids=(evidence.record_id,),
                evidence_disposition=EvidenceDisposition.INCONCLUSIVE,
            )
        )
        self.assertEqual(decision.state, DisagreementState.REVIEW_REQUIRED)
        self.assertIsNotNone(decision.review_handoff)
        assert decision.review_handoff is not None
        self.assertTrue(decision.review_handoff.created)
        self.assertEqual(decision.review_handoff.route.model, "gpt-oss:20b")
        self.assertNotEqual(decision.review_handoff.route.model, claim.actor_id)

    def test_qwen_claim_without_evidence_can_route_to_gpt_oss_review(self) -> None:
        supervisor, _ = make_supervisor()
        claim = self._claim(supervisor)
        decision = supervisor.plan_disagreement_review(
            DisagreementRequest(
                task_id="task-1",
                claim_record_id=claim.record_id,
                originating_model=claim.actor_id,
                evidence_record_ids=(),
                evidence_disposition=EvidenceDisposition.NOT_AVAILABLE,
            )
        )
        self.assertEqual(decision.state, DisagreementState.REVIEW_REQUIRED)
        assert decision.review_handoff is not None
        self.assertEqual(decision.review_handoff.route.model, "gpt-oss:20b")

    def test_gpt_oss_origin_cannot_self_review_and_escalates_human(self) -> None:
        supervisor, _ = make_supervisor()
        claim = self._claim(supervisor, "gpt-oss:20b")
        decision = supervisor.plan_disagreement_review(
            DisagreementRequest(
                task_id="task-1",
                claim_record_id=claim.record_id,
                originating_model=claim.actor_id,
                evidence_record_ids=(),
                evidence_disposition=EvidenceDisposition.NOT_AVAILABLE,
            )
        )
        self.assertEqual(
            decision.state, DisagreementState.NEEDS_HUMAN_APPROVAL
        )
        self.assertIsNone(decision.review_handoff)
        self.assertIn("cannot independently review itself", decision.reason)

    def test_review_no_substantive_conflict_resolves_workflow_not_evidence(self) -> None:
        supervisor, _ = make_supervisor()
        claim = self._claim(supervisor)
        planned = supervisor.plan_disagreement_review(
            DisagreementRequest(
                task_id="task-1",
                claim_record_id=claim.record_id,
                originating_model=claim.actor_id,
                evidence_record_ids=(),
                evidence_disposition=EvidenceDisposition.NOT_AVAILABLE,
            )
        )
        applied = supervisor.apply_disagreement_review(
            ReviewApplication(
                task_id="task-1",
                disagreement_record_id=planned.disagreement_record.record_id,
                originating_model=claim.actor_id,
                reviewer_model="gpt-oss:20b",
                finding=IndependentReviewFinding.NO_SUBSTANTIVE_CONFLICT,
                summary="the two statements are semantically compatible",
            )
        )
        self.assertEqual(
            applied.state, DisagreementState.RESOLVED_AFTER_REVIEW
        )
        assert applied.review_record is not None
        self.assertEqual(
            applied.review_record.validation_class,
            BlackboardValidationClass.ADVISORY,
        )
        self.assertEqual(applied.review_record.evidence_refs, ())

    def test_first_revision_request_is_bounded_to_one(self) -> None:
        supervisor, _ = make_supervisor()
        claim = self._claim(supervisor)
        planned = supervisor.plan_disagreement_review(
            DisagreementRequest(
                task_id="task-1",
                claim_record_id=claim.record_id,
                originating_model=claim.actor_id,
                evidence_record_ids=(),
                evidence_disposition=EvidenceDisposition.NOT_AVAILABLE,
            )
        )
        applied = supervisor.apply_disagreement_review(
            ReviewApplication(
                task_id="task-1",
                disagreement_record_id=planned.disagreement_record.record_id,
                originating_model=claim.actor_id,
                reviewer_model="gpt-oss:20b",
                finding=IndependentReviewFinding.REVISION_REQUIRED,
                summary="revise the claim against the stated constraints",
                revision_count=0,
            )
        )
        self.assertEqual(applied.state, DisagreementState.REVISION_REQUIRED)
        self.assertEqual(applied.next_revision_count, 1)

    def test_second_revision_request_escalates_human(self) -> None:
        supervisor, _ = make_supervisor()
        claim = self._claim(supervisor)
        planned = supervisor.plan_disagreement_review(
            DisagreementRequest(
                task_id="task-1",
                claim_record_id=claim.record_id,
                originating_model=claim.actor_id,
                evidence_record_ids=(),
                evidence_disposition=EvidenceDisposition.NOT_AVAILABLE,
                revision_count=1,
            )
        )
        applied = supervisor.apply_disagreement_review(
            ReviewApplication(
                task_id="task-1",
                disagreement_record_id=planned.disagreement_record.record_id,
                originating_model=claim.actor_id,
                reviewer_model="gpt-oss:20b",
                finding=IndependentReviewFinding.REVISION_REQUIRED,
                summary="another revision would be required",
                revision_count=1,
            )
        )
        self.assertEqual(
            applied.state, DisagreementState.NEEDS_HUMAN_APPROVAL
        )
        self.assertIn("revision bound exhausted", applied.reason)

    def test_inconclusive_review_escalates_human(self) -> None:
        supervisor, _ = make_supervisor()
        claim = self._claim(supervisor)
        planned = supervisor.plan_disagreement_review(
            DisagreementRequest(
                task_id="task-1",
                claim_record_id=claim.record_id,
                originating_model=claim.actor_id,
                evidence_record_ids=(),
                evidence_disposition=EvidenceDisposition.NOT_AVAILABLE,
            )
        )
        applied = supervisor.apply_disagreement_review(
            ReviewApplication(
                task_id="task-1",
                disagreement_record_id=planned.disagreement_record.record_id,
                originating_model=claim.actor_id,
                reviewer_model="gpt-oss:20b",
                finding=IndependentReviewFinding.INCONCLUSIVE,
                summary="available context does not resolve the claim",
            )
        )
        self.assertEqual(
            applied.state, DisagreementState.NEEDS_HUMAN_APPROVAL
        )

    def test_same_model_review_application_is_rejected(self) -> None:
        supervisor, _ = make_supervisor()
        claim = self._claim(supervisor)
        planned = supervisor.plan_disagreement_review(
            DisagreementRequest(
                task_id="task-1",
                claim_record_id=claim.record_id,
                originating_model=claim.actor_id,
                evidence_record_ids=(),
                evidence_disposition=EvidenceDisposition.NOT_AVAILABLE,
            )
        )
        with self.assertRaises(ValueError):
            supervisor.apply_disagreement_review(
                ReviewApplication(
                    task_id="task-1",
                    disagreement_record_id=planned.disagreement_record.record_id,
                    originating_model=claim.actor_id,
                    reviewer_model=claim.actor_id,
                    finding=IndependentReviewFinding.INCONCLUSIVE,
                    summary="self review is not independent",
                )
            )

    def test_non_evidence_record_cannot_be_declared_deterministic_evidence(self) -> None:
        supervisor, _ = make_supervisor()
        claim = self._claim(supervisor)
        other_claim = supervisor.blackboard_record_model_claim(
            task_id="task-1",
            model_id="qwen3.5:9b",
            payload={"claim": "second advisory claim"},
        )
        with self.assertRaises(ValueError):
            supervisor.plan_disagreement_review(
                DisagreementRequest(
                    task_id="task-1",
                    claim_record_id=claim.record_id,
                    originating_model=claim.actor_id,
                    evidence_record_ids=(other_claim.record_id,),
                    evidence_disposition=EvidenceDisposition.INCONCLUSIVE,
                )
            )

    def test_no_new_electronics_or_kicad_review_role_exists(self) -> None:
        names = {item.value for item in ModelTaskClass}
        self.assertNotIn("ELECTRONICS", names)
        self.assertNotIn("PCB", names)
        self.assertNotIn("KICAD", names)
        self.assertNotIn("VISION", names)


if __name__ == "__main__":
    unittest.main()
