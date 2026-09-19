from __future__ import annotations

import argparse
import itertools
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from engineering_ai.memory import (
    DecisionEvidenceMemory,
    MemoryAuthority,
    MemoryKind,
    MemoryRecordDraft,
    MemorySearchQuery,
    MemoryValidationClass,
    PhysicalValidationState,
)
from engineering_ai.validation import validate_instance


class SmokeIds:
    def __init__(self) -> None:
        self._counter = itertools.count(1)

    def __call__(self) -> str:
        return f"memrec-gate016-{next(self._counter):04d}"


def smoke_clock() -> datetime:
    return datetime(2026, 9, 19, 18, 50, 0, tzinfo=timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gate 016 local persistent/reopen decision-evidence memory smoke"
    )
    parser.add_argument(
        "--project-id",
        default="engineering-ai",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="engineering-ai-gate016-memory-") as tmp:
        db_path = Path(tmp) / "gate016-memory.sqlite3"
        ids = SmokeIds()

        with DecisionEvidenceMemory(
            db_path,
            clock=smoke_clock,
            record_id_factory=ids,
        ) as store:
            source = store.append(
                MemoryRecordDraft(
                    project_id=args.project_id,
                    memory_id="gate016-source-adr0009",
                    kind=MemoryKind.SOURCE_REFERENCE,
                    authority=MemoryAuthority.IMPORTED_SOURCE,
                    validation_class=MemoryValidationClass.SOURCE,
                    title="ADR-0009 evidence and provenance",
                    summary="Repository decision source for first-class provenance.",
                    content={"source_kind": "repository-document"},
                    provenance=("gate016-smoke:repository-source",),
                    source_refs=("DECISIONS.md#ADR-0009",),
                    physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
                )
            )
            test = store.append(
                MemoryRecordDraft(
                    project_id=args.project_id,
                    memory_id="gate016-smoke-test",
                    kind=MemoryKind.TEST_RESULT,
                    authority=MemoryAuthority.DETERMINISTIC_TOOL,
                    validation_class=MemoryValidationClass.DETERMINISTIC_TEST,
                    title="Gate 016 local SQLite smoke",
                    summary="Append/reopen/integrity/search smoke executed.",
                    content={"database": "sqlite", "phase": "initial"},
                    provenance=("script:gate016_memory_smoke.py",),
                    evidence_refs=("gate016-smoke:initial-write",),
                )
            )
            lesson1 = store.append(
                MemoryRecordDraft(
                    project_id=args.project_id,
                    memory_id="gate016-lesson-append-only",
                    kind=MemoryKind.FAILURE_LESSON,
                    authority=MemoryAuthority.SUPERVISOR,
                    validation_class=MemoryValidationClass.SOURCE,
                    title="Append-only memory lesson",
                    summary="Historical engineering memory is never rewritten in place.",
                    content={"lesson": "use supersession instead of UPDATE"},
                    provenance=("Gate016 acceptance criteria",),
                    source_refs=("issue:31",),
                )
            )
            for record in (source, test, lesson1):
                validate_instance("memory-record.schema.json", record.as_dict())
            initial_integrity = store.verify_integrity(project_id=args.project_id)

        with DecisionEvidenceMemory(
            db_path,
            clock=smoke_clock,
            record_id_factory=ids,
        ) as reopened:
            reopen_integrity = reopened.verify_integrity(project_id=args.project_id)
            loaded_test = reopened.get_record(
                project_id=args.project_id,
                record_id=test.record_id,
            )
            lesson2 = reopened.append(
                MemoryRecordDraft(
                    project_id=args.project_id,
                    memory_id="gate016-lesson-append-only",
                    kind=MemoryKind.FAILURE_LESSON,
                    authority=MemoryAuthority.SUPERVISOR,
                    validation_class=MemoryValidationClass.SOURCE,
                    title="Append-only memory lesson",
                    summary="Supersession creates the next exact revision.",
                    content={
                        "lesson": "append new revision",
                        "database": "SQLite",
                    },
                    provenance=("gate016-smoke:reopen",),
                    source_refs=("issue:31",),
                ),
                supersedes_record_id=lesson1.record_id,
            )
            validate_instance("memory-record.schema.json", lesson2.as_dict())
            latest_search = reopened.search(
                MemorySearchQuery(
                    project_id=args.project_id,
                    text="sqlite",
                    latest_only=True,
                    limit=10,
                )
            )
            history = reopened.history(
                project_id=args.project_id,
                memory_id="gate016-lesson-append-only",
            )
            final_integrity = reopened.verify_integrity(project_id=args.project_id)

        payload = {
            "gate": "016",
            "state": "PASS_LOCAL_PERSISTENT_REOPEN_MEMORY",
            "database_created": True,
            "database_reopened": True,
            "initial_records_checked": initial_integrity.records_checked,
            "reopen_records_checked": reopen_integrity.records_checked,
            "final_records_checked": final_integrity.records_checked,
            "loaded_record_hash_preserved": (
                loaded_test.content_sha256 == test.content_sha256
            ),
            "supersession": {
                "memory_id": lesson2.memory_id,
                "revision": lesson2.revision,
                "supersedes_record_id": lesson2.supersedes_record_id,
                "history_revisions": [item.revision for item in history],
            },
            "search_result_ids": [item.record_id for item in latest_search],
            "model_truth_promotion": False,
            "automatic_context_injection": False,
            "vector_search": False,
            "physical_validation": "PHYSICAL_NOT_EXECUTED",
            "temporary_database_removed_on_exit": True,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))

        ok = (
            initial_integrity.ok
            and reopen_integrity.ok
            and final_integrity.ok
            and initial_integrity.records_checked == 3
            and reopen_integrity.records_checked == 3
            and final_integrity.records_checked == 4
            and payload["loaded_record_hash_preserved"]
            and lesson2.revision == 2
            and lesson2.supersedes_record_id == lesson1.record_id
            and [item.revision for item in history] == [1, 2]
            and test.record_id in payload["search_result_ids"]
            and lesson2.record_id in payload["search_result_ids"]
        )
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
