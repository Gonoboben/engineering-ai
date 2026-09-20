from __future__ import annotations

import itertools
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from engineering_ai.memory import (
    DecisionEvidenceMemory,
    KnowledgeAssessmentState,
    KnowledgeLifecycle,
    KnowledgeLifecycleIntegrityError,
    KnowledgeLifecycleLedger,
    KnowledgeLifecyclePolicyError,
    KnowledgeStage,
    MemoryAuthority,
    MemoryKind,
    MemoryRecordDraft,
    MemoryValidationClass,
    PhysicalValidationState,
)
from engineering_ai.supervisor.core import Supervisor
from engineering_ai.validation import validate_instance


def fixed_clock() -> datetime:
    return datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)


class IdFactory:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.counter = itertools.count(1)

    def __call__(self) -> str:
        return f"{self.prefix}-{next(self.counter):04d}"


class KnowledgeLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.memory_path = root / "memory.sqlite3"
        self.lifecycle_path = root / "knowledge.sqlite3"
        self.memory = DecisionEvidenceMemory(
            self.memory_path,
            clock=fixed_clock,
            record_id_factory=IdFactory("memrec-g18"),
        )
        self.ledger = KnowledgeLifecycleLedger(
            self.lifecycle_path,
            clock=fixed_clock,
            record_id_factory=IdFactory("knowrec-g18"),
        )
        self.lifecycle = KnowledgeLifecycle(
            memory=self.memory,
            ledger=self.ledger,
        )

    def tearDown(self) -> None:
        self.ledger.close()
        self.memory.close()
        self.tmp.cleanup()

    def append_observation(self, *, project_id: str = "engineering-ai"):
        return self.memory.append(
            MemoryRecordDraft(
                project_id=project_id,
                memory_id="obs-visual-001",
                kind=MemoryKind.FAILURE_LESSON,
                authority=MemoryAuthority.MODEL,
                validation_class=MemoryValidationClass.ADVISORY,
                title="Visual observation",
                summary="Model sees a potentially unusual joint.",
                content={"observation": "inspect joint"},
                provenance=("model:qwen3-vl:test",),
            )
        )

    def append_source(
        self,
        *,
        project_id: str = "engineering-ai",
        memory_id: str = "source-spec-001",
        supersedes_record_id: str | None = None,
        summary: str = "Current source revision.",
    ):
        return self.memory.append(
            MemoryRecordDraft(
                project_id=project_id,
                memory_id=memory_id,
                kind=MemoryKind.SOURCE_REFERENCE,
                authority=MemoryAuthority.IMPORTED_SOURCE,
                validation_class=MemoryValidationClass.SOURCE,
                title="Component source",
                summary=summary,
                content={"source": summary},
                provenance=("source:test",),
                source_refs=("docs/component-source.md",),
                physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
            ),
            supersedes_record_id=supersedes_record_id,
        )

    def append_test(
        self,
        *,
        project_id: str = "engineering-ai",
        memory_id: str = "test-result-001",
        supersedes_record_id: str | None = None,
        result: str = "PASS",
    ):
        return self.memory.append(
            MemoryRecordDraft(
                project_id=project_id,
                memory_id=memory_id,
                kind=MemoryKind.TEST_RESULT,
                authority=MemoryAuthority.DETERMINISTIC_TOOL,
                validation_class=MemoryValidationClass.DETERMINISTIC_TEST,
                title="Deterministic validator",
                summary=f"Validator result {result}.",
                content={"result": result},
                provenance=("tool:test",),
                evidence_refs=(f"validator:{result.lower()}",),
            ),
            supersedes_record_id=supersedes_record_id,
        )

    def build_accepted(self):
        observation = self.append_observation()
        source = self.append_source()
        test = self.append_test()
        obs_state = self.lifecycle.record_observation(
            project_id="engineering-ai",
            knowledge_id="knowledge-joint-001",
            claim={"claim": "joint requires inspection"},
            observation_record_ids=(observation.record_id,),
            provenance=("supervisor:gate018",),
        )
        evidence = self.lifecycle.promote_to_evidence(
            project_id="engineering-ai",
            knowledge_id="knowledge-joint-001",
            evidence_record_ids=(source.record_id, test.record_id),
            source_record_ids=(source.record_id,),
            provenance=("supervisor:evidence-qualified",),
        )
        accepted = self.lifecycle.accept(
            project_id="engineering-ai",
            knowledge_id="knowledge-joint-001",
            provenance=("supervisor:accepted-non-control-knowledge",),
        )
        return observation, source, test, obs_state, evidence, accepted

    def test_model_observation_remains_advisory_and_lifecycle_owned_by_supervisor(self):
        observation = self.append_observation()
        record = self.lifecycle.record_observation(
            project_id="engineering-ai",
            knowledge_id="knowledge-observation-001",
            claim={"claim": "inspect"},
            observation_record_ids=(observation.record_id,),
            provenance=("supervisor:record-observation",),
        )
        self.assertEqual(record.stage, KnowledgeStage.OBSERVATION)
        self.assertEqual(record.authority, MemoryAuthority.SUPERVISOR)
        self.assertEqual(
            self.lifecycle.assess(
                project_id="engineering-ai",
                knowledge_id="knowledge-observation-001",
            ).state,
            KnowledgeAssessmentState.OBSERVATION,
        )
        self.assertEqual(observation.validation_class, MemoryValidationClass.ADVISORY)

        with self.assertRaises(KnowledgeLifecyclePolicyError):
            self.lifecycle.record_observation(
                project_id="engineering-ai",
                knowledge_id="knowledge-model-owned",
                claim={"claim": "forbidden"},
                observation_record_ids=(observation.record_id,),
                authority=MemoryAuthority.MODEL,
                provenance=("model:forbidden",),
            )

    def test_non_advisory_record_cannot_enter_observation_stage(self):
        source = self.append_source()
        with self.assertRaises(KnowledgeLifecyclePolicyError):
            self.lifecycle.record_observation(
                project_id="engineering-ai",
                knowledge_id="knowledge-bad-observation",
                claim={"claim": "wrong"},
                observation_record_ids=(source.record_id,),
                provenance=("supervisor:test",),
            )

    def test_evidence_promotion_requires_qualified_current_non_model_records(self):
        observation = self.append_observation()
        self.lifecycle.record_observation(
            project_id="engineering-ai",
            knowledge_id="knowledge-evidence-001",
            claim={"claim": "inspect"},
            observation_record_ids=(observation.record_id,),
            provenance=("supervisor:observation",),
        )
        with self.assertRaises(KnowledgeLifecyclePolicyError):
            self.lifecycle.promote_to_evidence(
                project_id="engineering-ai",
                knowledge_id="knowledge-evidence-001",
                evidence_record_ids=(observation.record_id,),
                provenance=("supervisor:bad-evidence",),
            )

        source = self.append_source()
        test = self.append_test()
        evidence = self.lifecycle.promote_to_evidence(
            project_id="engineering-ai",
            knowledge_id="knowledge-evidence-001",
            evidence_record_ids=(source.record_id, test.record_id),
            source_record_ids=(source.record_id,),
            provenance=("supervisor:qualified",),
        )
        self.assertEqual(evidence.stage, KnowledgeStage.EVIDENCE)
        assessment = self.lifecycle.assess(
            project_id="engineering-ai",
            knowledge_id="knowledge-evidence-001",
        )
        self.assertEqual(assessment.state, KnowledgeAssessmentState.EVIDENCE_CURRENT)
        self.assertFalse(assessment.physical_validation_inferred)

    def test_acceptance_requires_current_evidence(self):
        observation = self.append_observation()
        self.lifecycle.record_observation(
            project_id="engineering-ai",
            knowledge_id="knowledge-accept-001",
            claim={"claim": "inspect"},
            observation_record_ids=(observation.record_id,),
            provenance=("supervisor:observation",),
        )
        with self.assertRaises(KnowledgeLifecyclePolicyError):
            self.lifecycle.accept(
                project_id="engineering-ai",
                knowledge_id="knowledge-accept-001",
                provenance=("supervisor:too-early",),
            )

        source = self.append_source()
        test = self.append_test()
        self.lifecycle.promote_to_evidence(
            project_id="engineering-ai",
            knowledge_id="knowledge-accept-001",
            evidence_record_ids=(source.record_id, test.record_id),
            source_record_ids=(source.record_id,),
            provenance=("supervisor:evidence",),
        )
        accepted = self.lifecycle.accept(
            project_id="engineering-ai",
            knowledge_id="knowledge-accept-001",
            provenance=("supervisor:accept",),
        )
        self.assertEqual(accepted.stage, KnowledgeStage.ACCEPTED)
        assessment = self.lifecycle.assess(
            project_id="engineering-ai",
            knowledge_id="knowledge-accept-001",
        )
        self.assertEqual(assessment.state, KnowledgeAssessmentState.ACCEPTED_CURRENT)
        self.assertFalse(assessment.physical_validation_inferred)

    def test_source_revision_drift_makes_accepted_knowledge_stale(self):
        _, source, _, _, _, _ = self.build_accepted()
        newer = self.append_source(
            supersedes_record_id=source.record_id,
            summary="Revised source revision.",
        )
        self.assertEqual(newer.revision, 2)
        assessment = self.lifecycle.assess(
            project_id="engineering-ai",
            knowledge_id="knowledge-joint-001",
        )
        self.assertEqual(
            assessment.state,
            KnowledgeAssessmentState.STALE_SOURCE_REVISION,
        )
        self.assertEqual(
            assessment.stale_source_record_ids,
            (source.record_id,),
        )

    def test_evidence_revision_drift_is_detected_without_source_drift(self):
        _, _, test, _, _, _ = self.build_accepted()
        self.append_test(
            supersedes_record_id=test.record_id,
            result="FAIL",
        )
        assessment = self.lifecycle.assess(
            project_id="engineering-ai",
            knowledge_id="knowledge-joint-001",
        )
        self.assertEqual(
            assessment.state,
            KnowledgeAssessmentState.STALE_EVIDENCE_REVISION,
        )
        self.assertEqual(
            assessment.stale_evidence_record_ids,
            (test.record_id,),
        )

    def test_stale_knowledge_invalidation_is_append_only(self):
        _, source, _, _, _, _ = self.build_accepted()
        self.append_source(
            supersedes_record_id=source.record_id,
            summary="Revised source.",
        )
        invalidated = self.lifecycle.invalidate_if_stale(
            project_id="engineering-ai",
            knowledge_id="knowledge-joint-001",
            provenance=("supervisor:source-drift",),
        )
        self.assertEqual(invalidated.stage, KnowledgeStage.INVALIDATED)
        history = self.lifecycle.history(
            project_id="engineering-ai",
            knowledge_id="knowledge-joint-001",
        )
        self.assertEqual(
            tuple(record.stage for record in history),
            (
                KnowledgeStage.OBSERVATION,
                KnowledgeStage.EVIDENCE,
                KnowledgeStage.ACCEPTED,
                KnowledgeStage.INVALIDATED,
            ),
        )
        self.assertEqual(
            invalidated.supersedes_lifecycle_record_id,
            history[-2].lifecycle_record_id,
        )
        self.assertEqual(
            self.lifecycle.assess(
                project_id="engineering-ai",
                knowledge_id="knowledge-joint-001",
            ).state,
            KnowledgeAssessmentState.INVALIDATED,
        )
        self.assertTrue(self.ledger.verify_integrity().ok)

    def test_current_accepted_knowledge_cannot_be_invalidated_as_stale(self):
        self.build_accepted()
        with self.assertRaises(KnowledgeLifecyclePolicyError):
            self.lifecycle.invalidate_if_stale(
                project_id="engineering-ai",
                knowledge_id="knowledge-joint-001",
                provenance=("supervisor:wrong",),
            )

    def test_project_isolation_is_fail_closed(self):
        observation = self.append_observation(project_id="buoycalc")
        with self.assertRaises(KeyError):
            self.lifecycle.record_observation(
                project_id="engineering-ai",
                knowledge_id="knowledge-cross-project",
                claim={"claim": "forbidden"},
                observation_record_ids=(observation.record_id,),
                provenance=("supervisor:test",),
            )

    def test_lifecycle_hash_tamper_fails_closed(self):
        self.build_accepted()
        self.ledger.close()
        conn = sqlite3.connect(self.lifecycle_path)
        try:
            conn.execute("DROP TRIGGER knowledge_lifecycle_no_update")
            conn.execute(
                """
                UPDATE knowledge_lifecycle_records
                SET reason='tampered'
                WHERE knowledge_id='knowledge-joint-001' AND revision=3
                """
            )
            conn.commit()
        finally:
            conn.close()

        self.ledger = KnowledgeLifecycleLedger(
            self.lifecycle_path,
            clock=fixed_clock,
            record_id_factory=IdFactory("knowrec-reopen"),
        )
        self.lifecycle = KnowledgeLifecycle(
            memory=self.memory,
            ledger=self.ledger,
        )
        with self.assertRaises(KnowledgeLifecycleIntegrityError):
            self.ledger.latest(
                project_id="engineering-ai",
                knowledge_id="knowledge-joint-001",
            )

    def test_schema_validation_for_record_and_assessment(self):
        self.build_accepted()
        record = self.ledger.latest(
            project_id="engineering-ai",
            knowledge_id="knowledge-joint-001",
        )
        assessment = self.lifecycle.assess(
            project_id="engineering-ai",
            knowledge_id="knowledge-joint-001",
        )
        validate_instance("knowledge-lifecycle-record.schema.json", record.as_dict())
        validate_instance("knowledge-assessment.schema.json", assessment.as_dict())

    def test_supervisor_owns_same_project_lifecycle_boundary(self):
        observation = self.append_observation()
        policy = {
            "schema_version": "1.0",
            "policy_version": "gate018-test",
            "project_id": "engineering-ai",
            "autonomous_actions": ["read_repository"],
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
            "retry_limit": 1,
        }
        state = {
            "schema_version": "1.0",
            "state_revision": 1,
            "project_id": "engineering-ai",
            "current_gate": "018",
            "active_job_id": None,
            "repository_ref": {
                "branch": "gate-018-knowledge-lifecycle",
                "head_sha": "0123456789abcdef0123456789abcdef01234567",
            },
            "architecture_baseline": "Gate 017 accepted retrieval",
            "effective_permissions": {
                "autonomous": ["read_repository"],
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
            "validation_states": [],
            "next_admissible_action": None,
        }
        supervisor = Supervisor(
            policy=policy,
            state=state,
            knowledge_lifecycle=self.lifecycle,
        )
        record = supervisor.record_knowledge_observation(
            knowledge_id="knowledge-supervisor-001",
            claim={"claim": "bounded"},
            observation_record_ids=(observation.record_id,),
            provenance=("supervisor:test",),
        )
        self.assertEqual(record.project_id, "engineering-ai")
        assessment = supervisor.assess_knowledge(
            knowledge_id="knowledge-supervisor-001",
        )
        self.assertEqual(assessment.state, KnowledgeAssessmentState.OBSERVATION)
        self.assertEqual(supervisor.audit_events, ())

    def test_smoke_script(self):
        result = subprocess.run(
            [sys.executable, "scripts/gate018_knowledge_lifecycle_smoke.py"],
            cwd=Path(__file__).resolve().parents[1],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate"], "018")
        self.assertEqual(
            payload["state"],
            "PASS_APPEND_ONLY_KNOWLEDGE_LIFECYCLE",
        )
        self.assertEqual(payload["history_revisions"], [1, 2, 3, 4])
        self.assertEqual(
            payload["stale_state"],
            "STALE_SOURCE_REVISION",
        )
        self.assertEqual(payload["final_state"], "INVALIDATED")
        self.assertFalse(payload["automatic_context_injection"])
        self.assertFalse(payload["physical_validation_inferred"])


if __name__ == "__main__":
    unittest.main()
