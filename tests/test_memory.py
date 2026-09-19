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
    DecisionStatus,
    MemoryAuthority,
    MemoryConflictError,
    MemoryIntegrityError,
    MemoryKind,
    MemoryPolicyError,
    MemoryRecordDraft,
    MemorySchemaError,
    MemorySearchQuery,
    MemoryValidationClass,
    PhysicalValidationState,
)
from engineering_ai.validation import validate_instance


def fixed_clock() -> datetime:
    return datetime(2026, 9, 19, 18, 40, 0, tzinfo=timezone.utc)


class IdFactory:
    def __init__(self) -> None:
        self._counter = itertools.count(1)

    def __call__(self) -> str:
        return f"memrec-test-{next(self._counter):04d}"


def make_store(path: Path, *, max_scan_records: int = 10_000) -> DecisionEvidenceMemory:
    return DecisionEvidenceMemory(
        path,
        clock=fixed_clock,
        record_id_factory=IdFactory(),
        max_scan_records=max_scan_records,
    )


def accepted_adr(
    *,
    project_id: str = "engineering-ai",
    memory_id: str = "ADR-TEST-001",
    title: str = "Use append-only memory",
) -> MemoryRecordDraft:
    return MemoryRecordDraft(
        project_id=project_id,
        memory_id=memory_id,
        kind=MemoryKind.ADR,
        authority=MemoryAuthority.HUMAN,
        validation_class=MemoryValidationClass.CONTROL,
        title=title,
        summary="Human accepted the memory architecture.",
        content={"decision": "append-only SQLite"},
        provenance=("human-approval:gate016",),
        decision_status=DecisionStatus.ACCEPTED,
        physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
    )


class DecisionEvidenceMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "memory.sqlite3"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_append_reopen_and_schema_validation(self) -> None:
        with make_store(self.path) as store:
            record = store.append(accepted_adr())
            self.assertEqual(record.revision, 1)
            self.assertIsNone(record.supersedes_record_id)
            validate_instance("memory-record.schema.json", record.as_dict())
            self.assertTrue(store.verify_integrity().ok)

        with make_store(self.path) as reopened:
            loaded = reopened.get_record(
                project_id="engineering-ai",
                record_id=record.record_id,
            )
            self.assertEqual(loaded.record_id, record.record_id)
            self.assertEqual(loaded.content_sha256, record.content_sha256)
            self.assertEqual(
                reopened.latest(
                    project_id="engineering-ai",
                    memory_id="ADR-TEST-001",
                ).record_id,
                record.record_id,
            )
            self.assertEqual(reopened.verify_integrity().records_checked, 1)

    def test_supersession_requires_exact_latest_record_and_next_revision(self) -> None:
        with make_store(self.path) as store:
            first = store.append(
                MemoryRecordDraft(
                    project_id="engineering-ai",
                    memory_id="lesson-cleanup",
                    kind=MemoryKind.FAILURE_LESSON,
                    authority=MemoryAuthority.SUPERVISOR,
                    validation_class=MemoryValidationClass.SOURCE,
                    title="Windows worktree cleanup",
                    summary="Permission denied can leave residual filesystem state.",
                    content={"lesson": "guard cleanup by tracked state"},
                    provenance=("gate015:smoke-attempt-3",),
                    source_refs=("docs/evidence/gate015/controlled-loop.md",),
                )
            )

            with self.assertRaises(MemoryConflictError):
                store.append(
                    MemoryRecordDraft(
                        project_id="engineering-ai",
                        memory_id="lesson-cleanup",
                        kind=MemoryKind.FAILURE_LESSON,
                        authority=MemoryAuthority.SUPERVISOR,
                        validation_class=MemoryValidationClass.SOURCE,
                        title="Wrong revision",
                        summary="Must name exact prior record.",
                        content={"wrong": True},
                        provenance=("gate016:test",),
                    )
                )

            second = store.append(
                MemoryRecordDraft(
                    project_id="engineering-ai",
                    memory_id="lesson-cleanup",
                    kind=MemoryKind.FAILURE_LESSON,
                    authority=MemoryAuthority.SUPERVISOR,
                    validation_class=MemoryValidationClass.SOURCE,
                    title="Windows worktree cleanup",
                    summary="Use guarded retry plus exact-identity recovery.",
                    content={"lesson": "retry, verify, prune, exact identity"},
                    provenance=("gate015:final-recovery",),
                    source_refs=("docs/evidence/gate015/controlled-loop.md",),
                ),
                supersedes_record_id=first.record_id,
            )
            self.assertEqual(second.revision, 2)
            self.assertEqual(second.supersedes_record_id, first.record_id)
            history = store.history(
                project_id="engineering-ai",
                memory_id="lesson-cleanup",
            )
            self.assertEqual(tuple(item.revision for item in history), (1, 2))

            with self.assertRaises(MemoryConflictError):
                store.append(
                    MemoryRecordDraft(
                        project_id="engineering-ai",
                        memory_id="lesson-cleanup",
                        kind=MemoryKind.FAILURE_LESSON,
                        authority=MemoryAuthority.SUPERVISOR,
                        validation_class=MemoryValidationClass.SOURCE,
                        title="Stale branch",
                        summary="Cannot fork from revision one.",
                        content={"wrong": "branch"},
                        provenance=("gate016:test",),
                    ),
                    supersedes_record_id=first.record_id,
                )

    def test_model_records_must_remain_advisory(self) -> None:
        with self.assertRaises(MemoryPolicyError):
            MemoryRecordDraft(
                project_id="engineering-ai",
                memory_id="model-claim-001",
                kind=MemoryKind.FAILURE_LESSON,
                authority=MemoryAuthority.MODEL,
                validation_class=MemoryValidationClass.DETERMINISTIC_TEST,
                title="Model claim",
                summary="A model cannot promote itself to evidence.",
                content={"claim": "validated"},
                provenance=("model:qwen3.5:9b",),
                evidence_refs=("fake-validator",),
            )

        draft = MemoryRecordDraft(
            project_id="engineering-ai",
            memory_id="model-claim-002",
            kind=MemoryKind.FAILURE_LESSON,
            authority=MemoryAuthority.MODEL,
            validation_class=MemoryValidationClass.ADVISORY,
            title="Model hypothesis",
            summary="May be stored only as advisory.",
            content={"hypothesis": "inspect cleanup"},
            provenance=("model:qwen3.5:9b",),
        )
        self.assertEqual(draft.validation_class, MemoryValidationClass.ADVISORY)

    def test_accepted_adr_requires_human_control_authority(self) -> None:
        with self.assertRaises(MemoryPolicyError):
            MemoryRecordDraft(
                project_id="engineering-ai",
                memory_id="ADR-BAD-001",
                kind=MemoryKind.ADR,
                authority=MemoryAuthority.SUPERVISOR,
                validation_class=MemoryValidationClass.CONTROL,
                title="Autonomous accepted decision",
                summary="Supervisor cannot autonomously accept an ADR.",
                content={"decision": "forbidden"},
                provenance=("supervisor",),
                decision_status=DecisionStatus.ACCEPTED,
                physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
            )

        with self.assertRaises(MemoryPolicyError):
            MemoryRecordDraft(
                project_id="engineering-ai",
                memory_id="ADR-BAD-002",
                kind=MemoryKind.ADR,
                authority=MemoryAuthority.HUMAN,
                validation_class=MemoryValidationClass.SOURCE,
                title="Wrong validation class",
                summary="Accepted ADR is control state, not source evidence.",
                content={"decision": "forbidden"},
                provenance=("human",),
                decision_status=DecisionStatus.ACCEPTED,
                physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
            )

    def test_deterministic_and_physical_evidence_boundaries(self) -> None:
        with self.assertRaises(MemoryPolicyError):
            MemoryRecordDraft(
                project_id="buoycalc",
                memory_id="test-no-evidence",
                kind=MemoryKind.TEST_RESULT,
                authority=MemoryAuthority.DETERMINISTIC_TOOL,
                validation_class=MemoryValidationClass.DETERMINISTIC_TEST,
                title="Validator result",
                summary="Evidence refs are mandatory.",
                content={"state": "PASS"},
                provenance=("gate015",),
            )

        physical = MemoryRecordDraft(
            project_id="platavm",
            memory_id="physical-measurement-001",
            kind=MemoryKind.TEST_RESULT,
            authority=MemoryAuthority.HUMAN,
            validation_class=MemoryValidationClass.PHYSICAL,
            title="Physical measurement",
            summary="Explicit real physical measurement.",
            content={"measurement": "fixture"},
            provenance=("lab:test-run-001",),
            evidence_refs=("lab-record:test-run-001",),
            physical_validation_state=PhysicalValidationState.PHYSICAL_PASS,
        )
        self.assertEqual(
            physical.physical_validation_state,
            PhysicalValidationState.PHYSICAL_PASS,
        )

        with self.assertRaises(MemoryPolicyError):
            MemoryRecordDraft(
                project_id="buoycalc",
                memory_id="software-cannot-be-physical",
                kind=MemoryKind.TEST_RESULT,
                authority=MemoryAuthority.DETERMINISTIC_TOOL,
                validation_class=MemoryValidationClass.DETERMINISTIC_TEST,
                title="Software validator",
                summary="Cannot claim physical PASS.",
                content={"state": "PASS"},
                provenance=("ci:123",),
                evidence_refs=("ci:123",),
                physical_validation_state=PhysicalValidationState.PHYSICAL_PASS,
            )

    def test_source_reference_requires_source_validation_and_reference(self) -> None:
        with self.assertRaises(MemoryPolicyError):
            MemoryRecordDraft(
                project_id="engineering-ai",
                memory_id="source-001",
                kind=MemoryKind.SOURCE_REFERENCE,
                authority=MemoryAuthority.IMPORTED_SOURCE,
                validation_class=MemoryValidationClass.SOURCE,
                title="Source",
                summary="Missing source ref.",
                content={"name": "doc"},
                provenance=("import",),
            )

    def test_project_isolation_for_get_history_and_search(self) -> None:
        with make_store(self.path) as store:
            one = store.append(
                accepted_adr(
                    project_id="engineering-ai",
                    memory_id="shared-id",
                    title="Engineering AI decision",
                )
            )
            two = store.append(
                accepted_adr(
                    project_id="buoycalc",
                    memory_id="shared-id",
                    title="BuoyCalc decision",
                )
            )

            self.assertEqual(
                store.latest(
                    project_id="engineering-ai",
                    memory_id="shared-id",
                ).record_id,
                one.record_id,
            )
            self.assertEqual(
                store.latest(
                    project_id="buoycalc",
                    memory_id="shared-id",
                ).record_id,
                two.record_id,
            )
            with self.assertRaises(KeyError):
                store.get_record(
                    project_id="engineering-ai",
                    record_id=two.record_id,
                )
            results = store.search(
                MemorySearchQuery(project_id="engineering-ai", text="decision")
            )
            self.assertEqual(tuple(item.project_id for item in results), ("engineering-ai",))

    def test_search_is_casefolded_filtered_bounded_and_latest_only(self) -> None:
        with make_store(self.path) as store:
            first = store.append(
                MemoryRecordDraft(
                    project_id="engineering-ai",
                    memory_id="calc-001",
                    kind=MemoryKind.CALCULATION,
                    authority=MemoryAuthority.DETERMINISTIC_TOOL,
                    validation_class=MemoryValidationClass.CALCULATION,
                    title="Mooring LOAD Estimate",
                    summary="First calculation.",
                    content={"result": "OLD"},
                    provenance=("calc-run:1",),
                    evidence_refs=("calc-run:1",),
                )
            )
            second = store.append(
                MemoryRecordDraft(
                    project_id="engineering-ai",
                    memory_id="calc-001",
                    kind=MemoryKind.CALCULATION,
                    authority=MemoryAuthority.DETERMINISTIC_TOOL,
                    validation_class=MemoryValidationClass.CALCULATION,
                    title="Mooring load estimate",
                    summary="Updated calculation.",
                    content={"result": "NEW"},
                    provenance=("calc-run:2",),
                    evidence_refs=("calc-run:2",),
                ),
                supersedes_record_id=first.record_id,
            )
            store.append(
                MemoryRecordDraft(
                    project_id="engineering-ai",
                    memory_id="source-002",
                    kind=MemoryKind.SOURCE_REFERENCE,
                    authority=MemoryAuthority.IMPORTED_SOURCE,
                    validation_class=MemoryValidationClass.SOURCE,
                    title="Other source",
                    summary="Unrelated.",
                    content={"topic": "electronics"},
                    provenance=("import",),
                    source_refs=("docs/other.md",),
                )
            )

            latest = store.search(
                MemorySearchQuery(
                    project_id="engineering-ai",
                    text="MOORING LOAD",
                    kinds=(MemoryKind.CALCULATION,),
                    latest_only=True,
                    limit=10,
                )
            )
            self.assertEqual(tuple(item.record_id for item in latest), (second.record_id,))

            history = store.search(
                MemorySearchQuery(
                    project_id="engineering-ai",
                    text="mooring",
                    kinds=(MemoryKind.CALCULATION,),
                    latest_only=False,
                    limit=10,
                )
            )
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0].revision, 2)
            self.assertEqual(history[1].revision, 1)

    def test_candidate_scan_limit_is_enforced(self) -> None:
        with make_store(self.path, max_scan_records=1) as store:
            store.append(accepted_adr(memory_id="ADR-LIMIT-001"))
            store.append(accepted_adr(memory_id="ADR-LIMIT-002"))
            with self.assertRaises(MemoryPolicyError):
                store.search(
                    MemorySearchQuery(
                        project_id="engineering-ai",
                        latest_only=True,
                    )
                )

    def test_sqlite_triggers_prohibit_update_and_delete(self) -> None:
        with make_store(self.path) as store:
            record = store.append(accepted_adr())

        conn = sqlite3.connect(self.path)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "UPDATE memory_records SET title = 'tampered' WHERE record_id = ?",
                    (record.record_id,),
                )
            conn.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "DELETE FROM memory_records WHERE record_id = ?",
                    (record.record_id,),
                )
            conn.rollback()
        finally:
            conn.close()

    def test_corrupted_stored_content_is_never_silently_returned(self) -> None:
        with make_store(self.path) as store:
            record = store.append(accepted_adr())

        conn = sqlite3.connect(self.path)
        try:
            conn.execute("DROP TRIGGER memory_records_no_update")
            conn.execute(
                "UPDATE memory_records SET summary = 'tampered' WHERE record_id = ?",
                (record.record_id,),
            )
            conn.commit()
        finally:
            conn.close()

        with make_store(self.path) as reopened:
            with self.assertRaises(MemoryIntegrityError):
                reopened.get_record(
                    project_id="engineering-ai",
                    record_id=record.record_id,
                )
            with self.assertRaises(MemoryIntegrityError):
                reopened.verify_integrity()

    def test_schema_version_mismatch_blocks_open(self) -> None:
        with make_store(self.path):
            pass

        conn = sqlite3.connect(self.path)
        try:
            conn.execute(
                "UPDATE memory_meta SET value = '999' WHERE key = 'schema_version'"
            )
            conn.commit()
        finally:
            conn.close()

        with self.assertRaises(MemorySchemaError):
            make_store(self.path)

    def test_local_persistent_reopen_smoke_harness(self) -> None:
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                sys.executable,
                str(root / "scripts/gate016_memory_smoke.py"),
                "--project-id",
                "engineering-ai",
            ],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["state"],
            "PASS_LOCAL_PERSISTENT_REOPEN_MEMORY",
        )
        self.assertTrue(payload["database_reopened"])
        self.assertTrue(payload["loaded_record_hash_preserved"])
        self.assertEqual(payload["supersession"]["history_revisions"], [1, 2])
        self.assertFalse(payload["model_truth_promotion"])
        self.assertFalse(payload["automatic_context_injection"])
        self.assertFalse(payload["vector_search"])
        self.assertEqual(
            payload["physical_validation"],
            "PHYSICAL_NOT_EXECUTED",
        )

    def test_no_update_delete_or_generic_sql_api_is_exposed(self) -> None:
        with make_store(self.path) as store:
            for name in (
                "update",
                "delete",
                "execute",
                "execute_sql",
                "query_sql",
                "vacuum_records",
                "semantic_search",
                "vector_search",
                "inject_context",
            ):
                self.assertFalse(hasattr(store, name))


if __name__ == "__main__":
    unittest.main()
