from __future__ import annotations

import itertools
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from engineering_ai.memory import (
    DecisionEvidenceMemory,
    DecisionStatus,
    MemoryAuthority,
    MemoryKind,
    MemoryPolicyError,
    MemoryRecordDraft,
    MemoryValidationClass,
    PhysicalValidationState,
    PolicyControlledMemoryRetriever,
    RetrievalPolicyError,
    RetrievalRequest,
    RetrievalStatus,
)
from engineering_ai.supervisor import Supervisor
from engineering_ai.validation import validate_instance


ROOT = Path(__file__).resolve().parents[1]


class IdFactory:
    def __init__(self) -> None:
        self._counter = itertools.count(1)

    def __call__(self) -> str:
        return f"memrec-retrieval-{next(self._counter):04d}"


def clock() -> datetime:
    return datetime(2026, 9, 19, 19, 15, 0, tzinfo=timezone.utc)


class RetrievalLayerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "memory.sqlite3"
        self.memory = DecisionEvidenceMemory(
            self.db,
            clock=clock,
            record_id_factory=IdFactory(),
        )
        self.retriever = PolicyControlledMemoryRetriever(self.memory)

    def tearDown(self) -> None:
        self.memory.close()
        self.tmp.cleanup()

    def append_source(
        self,
        memory_id: str,
        title: str,
        summary: str,
        *,
        project_id: str = "engineering-ai",
    ):
        return self.memory.append(
            MemoryRecordDraft(
                project_id=project_id,
                memory_id=memory_id,
                kind=MemoryKind.SOURCE_REFERENCE,
                authority=MemoryAuthority.IMPORTED_SOURCE,
                validation_class=MemoryValidationClass.SOURCE,
                title=title,
                summary=summary,
                content={"topic": title},
                provenance=("test:source",),
                source_refs=(f"docs/{memory_id}.md",),
                physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
            )
        )

    def test_default_retrieval_excludes_model_advisory(self) -> None:
        self.memory.append(
            MemoryRecordDraft(
                project_id="engineering-ai",
                memory_id="model-secret",
                kind=MemoryKind.FAILURE_LESSON,
                authority=MemoryAuthority.MODEL,
                validation_class=MemoryValidationClass.ADVISORY,
                title="Anchor drag hypothesis",
                summary="Model speculation only.",
                content={"anchor": "drag"},
                provenance=("model:qwen",),
            )
        )
        self.append_source(
            "source-anchor",
            "Anchor drag source",
            "Measured source discussion.",
        )

        package = self.retriever.retrieve(
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="anchor drag",
            )
        )
        ids = tuple(item.memory_id for item in package.items)
        self.assertIn("source-anchor", ids)
        self.assertNotIn("model-secret", ids)
        self.assertFalse(package.include_advisory)

    def test_explicit_advisory_opt_in_preserves_labels(self) -> None:
        model = self.memory.append(
            MemoryRecordDraft(
                project_id="engineering-ai",
                memory_id="model-hypothesis",
                kind=MemoryKind.FAILURE_LESSON,
                authority=MemoryAuthority.MODEL,
                validation_class=MemoryValidationClass.ADVISORY,
                title="Unverified anchor hypothesis",
                summary="Advisory only.",
                content={"anchor": "hypothesis"},
                provenance=("model:qwen",),
            )
        )
        package = self.retriever.retrieve(
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="anchor hypothesis",
                include_advisory=True,
            )
        )
        item = next(x for x in package.items if x.record_id == model.record_id)
        self.assertEqual(item.authority, MemoryAuthority.MODEL)
        self.assertEqual(
            item.validation_class,
            MemoryValidationClass.ADVISORY,
        )

    def test_advisory_filter_requires_explicit_opt_in(self) -> None:
        with self.assertRaises(RetrievalPolicyError):
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="anything",
                authorities=(MemoryAuthority.MODEL,),
            )
        with self.assertRaises(RetrievalPolicyError):
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="anything",
                validation_classes=(MemoryValidationClass.ADVISORY,),
            )

    def test_proposed_adr_excluded_by_default_and_explicitly_visible(self) -> None:
        proposed = self.memory.append(
            MemoryRecordDraft(
                project_id="engineering-ai",
                memory_id="ADR-PROPOSED-017",
                kind=MemoryKind.ADR,
                authority=MemoryAuthority.HUMAN,
                validation_class=MemoryValidationClass.CONTROL,
                title="Experimental vector backend",
                summary="Proposal only.",
                content={"decision": "evaluate vector later"},
                provenance=("gate017:test",),
                decision_status=DecisionStatus.PROPOSED,
                physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
            )
        )
        default = self.retriever.retrieve(
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="vector backend",
            )
        )
        self.assertNotIn(
            proposed.record_id,
            tuple(item.record_id for item in default.items),
        )

        explicit = self.retriever.retrieve(
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="vector backend",
                include_proposed_adrs=True,
            )
        )
        item = next(x for x in explicit.items if x.record_id == proposed.record_id)
        self.assertEqual(item.decision_status, DecisionStatus.PROPOSED)

    def test_latest_only_default_and_history_opt_in(self) -> None:
        first = self.append_source(
            "revisioned-source",
            "Old mooring source note",
            "Old drag coefficient note.",
        )
        second = self.memory.append(
            MemoryRecordDraft(
                project_id="engineering-ai",
                memory_id="revisioned-source",
                kind=MemoryKind.SOURCE_REFERENCE,
                authority=MemoryAuthority.IMPORTED_SOURCE,
                validation_class=MemoryValidationClass.SOURCE,
                title="Current mooring source note",
                summary="Current drag coefficient note.",
                content={"topic": "mooring current drag"},
                provenance=("test:source-v2",),
                source_refs=("docs/current.md",),
                physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
            ),
            supersedes_record_id=first.record_id,
        )

        default = self.retriever.retrieve(
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="mooring source note",
            )
        )
        self.assertEqual(
            tuple(item.record_id for item in default.items),
            (second.record_id,),
        )
        self.assertTrue(default.items[0].is_latest_revision)

        history = self.retriever.retrieve(
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="mooring source note",
                include_history=True,
            )
        )
        self.assertEqual(
            {item.record_id for item in history.items},
            {first.record_id, second.record_id},
        )
        flags = {item.record_id: item.is_latest_revision for item in history.items}
        self.assertFalse(flags[first.record_id])
        self.assertTrue(flags[second.record_id])

    def test_lexical_ranking_handles_noncontiguous_reordered_terms(self) -> None:
        good = self.append_source(
            "cleanup-source",
            "Windows worktree cleanup recovery",
            "Guard exact identity and base SHA.",
        )
        self.append_source(
            "other-source",
            "Linux package recovery",
            "Unrelated cleanup note.",
        )

        package = self.retriever.retrieve(
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="cleanup windows recovery",
                max_results=2,
            )
        )
        self.assertEqual(package.items[0].record_id, good.record_id)
        self.assertEqual(
            set(package.items[0].matched_terms),
            {"cleanup", "windows", "recovery"},
        )

    def test_stable_tie_break_uses_memory_id(self) -> None:
        self.append_source("zzz-source", "Alpha beta", "same")
        self.append_source("aaa-source", "Alpha beta", "same")
        package = self.retriever.retrieve(
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="alpha beta",
                max_results=2,
            )
        )
        self.assertEqual(
            tuple(item.memory_id for item in package.items),
            ("aaa-source", "zzz-source"),
        )

    def test_context_budget_never_truncates_record(self) -> None:
        self.append_source(
            "large-source",
            "Large engineering source",
            "X" * 1500,
        )
        package = self.retriever.retrieve(
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="large engineering source",
                max_context_chars=256,
            )
        )
        self.assertEqual(package.status, RetrievalStatus.BUDGET_EXHAUSTED)
        self.assertEqual(package.items, ())
        self.assertEqual(package.omitted_due_to_context_budget, 1)
        self.assertEqual(package.total_context_chars, 0)

    def test_result_limit_and_context_metadata_are_explicit(self) -> None:
        for idx in range(3):
            self.append_source(
                f"source-{idx}",
                f"Mooring validation source {idx}",
                "Mooring validation reference.",
            )
        package = self.retriever.retrieve(
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="mooring validation",
                max_results=2,
            )
        )
        self.assertEqual(len(package.items), 2)
        self.assertEqual(package.relevant_count, 3)
        self.assertEqual(package.omitted_due_to_result_limit, 1)
        self.assertGreater(package.total_context_chars, 0)

    def test_provenance_evidence_source_hash_and_physical_state_preserved(self) -> None:
        record = self.memory.append(
            MemoryRecordDraft(
                project_id="engineering-ai",
                memory_id="validator-result",
                kind=MemoryKind.TEST_RESULT,
                authority=MemoryAuthority.DETERMINISTIC_TOOL,
                validation_class=MemoryValidationClass.DETERMINISTIC_TEST,
                title="Repository integrity validator",
                summary="Deterministic validator passed.",
                content={"result": "PASS"},
                provenance=("ci:run-123",),
                evidence_refs=("ci:run-123", "sha256:log:abc"),
                source_refs=("workflow:integrity",),
            )
        )
        package = self.retriever.retrieve(
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="repository integrity validator",
            )
        )
        item = package.items[0]
        self.assertEqual(item.record_id, record.record_id)
        self.assertEqual(item.provenance, record.provenance)
        self.assertEqual(item.evidence_refs, record.evidence_refs)
        self.assertEqual(item.source_refs, record.source_refs)
        self.assertEqual(item.content_sha256, record.content_sha256)
        self.assertEqual(
            item.physical_validation_state,
            "PHYSICAL_NOT_EXECUTED",
        )

    def test_project_isolation(self) -> None:
        self.append_source(
            "shared-engineering-ai",
            "Shared keyword source",
            "Engineering AI.",
            project_id="engineering-ai",
        )
        self.append_source(
            "shared-buoycalc",
            "Shared keyword source",
            "BuoyCalc.",
            project_id="buoycalc",
        )
        package = self.retriever.retrieve(
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="shared keyword",
            )
        )
        self.assertEqual(
            {item.memory_id for item in package.items},
            {"shared-engineering-ai"},
        )

    def test_integrity_failure_from_memory_fails_closed(self) -> None:
        record = self.append_source(
            "tamper-source",
            "Tamper test source",
            "Integrity must fail closed.",
        )
        self.memory.close()

        import sqlite3

        conn = sqlite3.connect(self.db)
        try:
            conn.execute("DROP TRIGGER memory_records_no_update")
            conn.execute(
                "UPDATE memory_records SET summary='tampered' WHERE record_id=?",
                (record.record_id,),
            )
            conn.commit()
        finally:
            conn.close()

        self.memory = DecisionEvidenceMemory(
            self.db,
            clock=clock,
            record_id_factory=IdFactory(),
        )
        self.retriever = PolicyControlledMemoryRetriever(self.memory)
        with self.assertRaises(Exception) as ctx:
            self.retriever.retrieve(
                RetrievalRequest(
                    project_id="engineering-ai",
                    query_text="tamper test",
                )
            )
        self.assertEqual(type(ctx.exception).__name__, "MemoryIntegrityError")

    def test_context_package_schema_and_no_automatic_injection(self) -> None:
        self.append_source(
            "schema-source",
            "Schema retrieval source",
            "Schema package.",
        )
        package = self.retriever.retrieve(
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="schema retrieval",
            )
        )
        data = package.as_dict()
        validate_instance("retrieval-context.schema.json", data)
        self.assertFalse(data["automatic_context_injection"])
        self.assertEqual(
            data["semantic_vector_backend"],
            "DEFERRED_NOT_JUSTIFIED",
        )

    def test_supervisor_owned_retrieval_same_project_only(self) -> None:
        policy = {
            "schema_version": "1.0",
            "policy_version": "gate017-test",
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
            "current_gate": "017",
            "active_job_id": None,
            "repository_ref": {
                "branch": "gate-017-retrieval-layer",
                "head_sha": "0123456789abcdef0123456789abcdef01234567",
            },
            "architecture_baseline": "Gate 016 accepted memory",
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
        self.append_source(
            "supervisor-source",
            "Supervisor retrieval source",
            "Bounded same-project context.",
        )
        supervisor = Supervisor(
            policy=policy,
            state=state,
            memory_retriever=self.retriever,
        )
        package = supervisor.retrieve_memory_context(
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="supervisor retrieval",
            )
        )
        self.assertEqual(package.status, RetrievalStatus.READY)
        self.assertEqual(
            tuple(item.memory_id for item in package.items),
            ("supervisor-source",),
        )
        self.assertEqual(supervisor.audit_events, ())

        with self.assertRaises(RetrievalPolicyError):
            supervisor.retrieve_memory_context(
                RetrievalRequest(
                    project_id="buoycalc",
                    query_text="supervisor retrieval",
                )
            )

    def test_supervisor_retrieval_does_not_create_blackboard_or_handoff(self) -> None:
        policy = {
            "schema_version": "1.0",
            "policy_version": "gate017-test-no-injection",
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
            "current_gate": "017",
            "active_job_id": None,
            "repository_ref": {
                "branch": "gate-017-retrieval-layer",
                "head_sha": "0123456789abcdef0123456789abcdef01234567",
            },
            "architecture_baseline": "Gate 016 accepted memory",
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
        self.append_source(
            "no-injection-source",
            "No injection source",
            "Retrieval remains detached from model context.",
        )
        supervisor = Supervisor(
            policy=policy,
            state=state,
            memory_retriever=self.retriever,
        )
        package = supervisor.retrieve_memory_context(
            RetrievalRequest(
                project_id="engineering-ai",
                query_text="no injection",
            )
        )
        self.assertEqual(package.status, RetrievalStatus.READY)
        with self.assertRaises(RuntimeError):
            supervisor.blackboard_view(task_id="task-1")

    def test_read_only_surface_exposes_no_write_vector_or_injection_api(self) -> None:
        self.retriever.assert_read_only_surface(self.retriever)
        for name in (
            "append",
            "update",
            "delete",
            "execute_sql",
            "inject_context",
            "write_blackboard",
            "promote_evidence",
            "semantic_search",
            "vector_search",
        ):
            self.assertFalse(hasattr(self.retriever, name))

    def test_benchmark_smoke_improves_recall_and_preserves_safety(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/gate017_retrieval_benchmark.py"),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["state"],
            "PASS_DETERMINISTIC_RETRIEVAL_BENCHMARK",
        )
        self.assertGreater(
            payload["retrieval_mean_recall_at_k"],
            payload["baseline_mean_recall_at_k"],
        )
        self.assertGreater(payload["improved_case_count"], 0)
        self.assertTrue(payload["safety_pass"])
        self.assertTrue(payload["retrieval_not_worse_all_relevant_cases"])
        self.assertEqual(
            payload["semantic_vector_backend"],
            "DEFERRED_NOT_JUSTIFIED",
        )
        self.assertFalse(payload["automatic_context_injection"])


if __name__ == "__main__":
    unittest.main()
