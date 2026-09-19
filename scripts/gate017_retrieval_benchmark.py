from __future__ import annotations

import itertools
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from engineering_ai.memory import (
    DecisionEvidenceMemory,
    DecisionStatus,
    MemoryAuthority,
    MemoryKind,
    MemoryRecordDraft,
    MemoryValidationClass,
    PhysicalValidationState,
)
from engineering_ai.memory.benchmark import (
    RetrievalBenchmarkCase,
    run_retrieval_benchmark,
)


class IdFactory:
    def __init__(self) -> None:
        self._counter = itertools.count(1)

    def __call__(self) -> str:
        return f"memrec-gate017-{next(self._counter):04d}"


def clock() -> datetime:
    return datetime(2026, 9, 19, 19, 10, 0, tzinfo=timezone.utc)


def populate(memory: DecisionEvidenceMemory) -> None:
    memory.append(
        MemoryRecordDraft(
            project_id="engineering-ai",
            memory_id="adr-append-memory",
            kind=MemoryKind.ADR,
            authority=MemoryAuthority.HUMAN,
            validation_class=MemoryValidationClass.CONTROL,
            title="Use append-only local SQLite decision evidence memory",
            summary="Historical engineering memory uses immutable revisions.",
            content={"decision": "append-only SQLite memory"},
            provenance=("Gate016:ADR-0015",),
            decision_status=DecisionStatus.ACCEPTED,
            physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
        )
    )
    memory.append(
        MemoryRecordDraft(
            project_id="engineering-ai",
            memory_id="lesson-windows-cleanup",
            kind=MemoryKind.FAILURE_LESSON,
            authority=MemoryAuthority.SUPERVISOR,
            validation_class=MemoryValidationClass.SOURCE,
            title="Windows worktree cleanup recovery",
            summary="Guard cleanup by exact base SHA and tracked state.",
            content={"lesson": "retry prune exact identity"},
            provenance=("Gate015:cleanup-recovery",),
            source_refs=("docs/evidence/gate015/controlled-loop.md",),
        )
    )
    memory.append(
        MemoryRecordDraft(
            project_id="engineering-ai",
            memory_id="test-buoycalc-shape",
            kind=MemoryKind.TEST_RESULT,
            authority=MemoryAuthority.DETERMINISTIC_TOOL,
            validation_class=MemoryValidationClass.DETERMINISTIC_TEST,
            title="BuoyCalc selected shape consumer validation",
            summary="Selected shape consumer scan completed successfully.",
            content={"validator": "Selected Shape Consumer Scan", "result": "PASS"},
            provenance=("Gate015:validation",),
            evidence_refs=("ci:selected-shape-consumer-scan",),
        )
    )
    memory.append(
        MemoryRecordDraft(
            project_id="engineering-ai",
            memory_id="source-berteaux",
            kind=MemoryKind.SOURCE_REFERENCE,
            authority=MemoryAuthority.IMPORTED_SOURCE,
            validation_class=MemoryValidationClass.SOURCE,
            title="Berteaux buoy engineering reference",
            summary="Primary source reference for buoy engineering calculations.",
            content={"author": "H. O. Berteaux", "topic": "buoy engineering"},
            provenance=("source-import",),
            source_refs=("searchable_ocr.pdf",),
            physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
        )
    )
    memory.append(
        MemoryRecordDraft(
            project_id="engineering-ai",
            memory_id="model-magic-anchor",
            kind=MemoryKind.FAILURE_LESSON,
            authority=MemoryAuthority.MODEL,
            validation_class=MemoryValidationClass.ADVISORY,
            title="Unverified magic anchor hypothesis",
            summary="Model-only hypothesis with no engineering evidence.",
            content={"hypothesis": "magic anchor"},
            provenance=("model:qwen3.5:9b",),
        )
    )
    memory.append(
        MemoryRecordDraft(
            project_id="engineering-ai",
            memory_id="adr-vector-experiment",
            kind=MemoryKind.ADR,
            authority=MemoryAuthority.HUMAN,
            validation_class=MemoryValidationClass.CONTROL,
            title="Experimental semantic vector backend",
            summary="Proposed only; no benchmark qualification exists.",
            content={"decision": "evaluate later"},
            provenance=("Gate017:proposal",),
            decision_status=DecisionStatus.PROPOSED,
            physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
        )
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="engineering-ai-gate017-retrieval-") as tmp:
        db = Path(tmp) / "benchmark.sqlite3"
        with DecisionEvidenceMemory(
            db,
            clock=clock,
            record_id_factory=IdFactory(),
        ) as memory:
            populate(memory)
            cases = (
                RetrievalBenchmarkCase(
                    case_id="append-memory-noncontiguous",
                    query_text="sqlite memory append only",
                    expected_memory_ids=("adr-append-memory",),
                ),
                RetrievalBenchmarkCase(
                    case_id="windows-cleanup-reordered",
                    query_text="cleanup windows recovery",
                    expected_memory_ids=("lesson-windows-cleanup",),
                ),
                RetrievalBenchmarkCase(
                    case_id="shape-validation-gap",
                    query_text="selected shape validation",
                    expected_memory_ids=("test-buoycalc-shape",),
                ),
                RetrievalBenchmarkCase(
                    case_id="source-contiguous-baseline",
                    query_text="buoy engineering",
                    expected_memory_ids=("source-berteaux",),
                ),
                RetrievalBenchmarkCase(
                    case_id="advisory-safety",
                    query_text="magic anchor",
                    expected_memory_ids=(),
                    forbidden_memory_ids=("model-magic-anchor",),
                ),
                RetrievalBenchmarkCase(
                    case_id="proposed-adr-safety",
                    query_text="semantic vector backend",
                    expected_memory_ids=(),
                    forbidden_memory_ids=("adr-vector-experiment",),
                ),
            )
            result = run_retrieval_benchmark(
                memory,
                project_id="engineering-ai",
                cases=cases,
                k=3,
            )

        payload = {
            "gate": "017",
            "state": (
                "PASS_DETERMINISTIC_RETRIEVAL_BENCHMARK"
                if result.passed
                else "FAIL_DETERMINISTIC_RETRIEVAL_BENCHMARK"
            ),
            "k": result.k,
            "baseline_mean_recall_at_k": result.baseline_mean_recall_at_k,
            "retrieval_mean_recall_at_k": result.retrieval_mean_recall_at_k,
            "improved_case_count": result.improved_case_count,
            "safety_pass": result.safety_pass,
            "retrieval_not_worse_all_relevant_cases": (
                result.retrieval_not_worse_all_relevant_cases
            ),
            "semantic_vector_backend": result.semantic_vector_backend,
            "cases": [
                {
                    "case_id": case.case_id,
                    "baseline_memory_ids": list(case.baseline_memory_ids),
                    "retrieval_memory_ids": list(case.retrieval_memory_ids),
                    "baseline_recall_at_k": case.baseline_recall_at_k,
                    "retrieval_recall_at_k": case.retrieval_recall_at_k,
                    "safety_pass": case.safety_pass,
                    "retrieval_not_worse": case.retrieval_not_worse,
                    "improved": case.improved,
                }
                for case in result.cases
            ],
            "automatic_context_injection": False,
            "physical_validation": "PHYSICAL_NOT_EXECUTED",
            "temporary_database_removed_on_exit": True,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
