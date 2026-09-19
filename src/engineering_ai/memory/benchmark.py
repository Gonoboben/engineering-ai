"""Deterministic retrieval benchmark primitives for Gate 017."""

from __future__ import annotations

from dataclasses import dataclass

from engineering_ai.memory.retrieval import (
    PolicyControlledMemoryRetriever,
    RetrievalRequest,
)
from engineering_ai.memory.store import (
    DecisionEvidenceMemory,
    DecisionStatus,
    MemoryAuthority,
    MemoryKind,
    MemorySearchQuery,
    MemoryValidationClass,
)


_SAFE_VALIDATION_CLASSES = tuple(
    item
    for item in MemoryValidationClass
    if item is not MemoryValidationClass.ADVISORY
)
_SAFE_AUTHORITIES = tuple(
    item for item in MemoryAuthority if item is not MemoryAuthority.MODEL
)


@dataclass(frozen=True)
class RetrievalBenchmarkCase:
    case_id: str
    query_text: str
    expected_memory_ids: tuple[str, ...]
    forbidden_memory_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalBenchmarkCaseResult:
    case_id: str
    baseline_memory_ids: tuple[str, ...]
    retrieval_memory_ids: tuple[str, ...]
    baseline_recall_at_k: float | None
    retrieval_recall_at_k: float | None
    safety_pass: bool
    retrieval_not_worse: bool
    improved: bool


@dataclass(frozen=True)
class RetrievalBenchmarkResult:
    k: int
    cases: tuple[RetrievalBenchmarkCaseResult, ...]
    baseline_mean_recall_at_k: float
    retrieval_mean_recall_at_k: float
    safety_pass: bool
    retrieval_not_worse_all_relevant_cases: bool
    improved_case_count: int
    semantic_vector_backend: str = "DEFERRED_NOT_JUSTIFIED"

    @property
    def passed(self) -> bool:
        return (
            self.safety_pass
            and self.retrieval_not_worse_all_relevant_cases
            and self.improved_case_count > 0
            and self.retrieval_mean_recall_at_k
            > self.baseline_mean_recall_at_k
        )


def _recall(
    retrieved: tuple[str, ...],
    expected: tuple[str, ...],
) -> float | None:
    if not expected:
        return None
    expected_set = set(expected)
    return len(expected_set & set(retrieved)) / len(expected_set)


def _safe_exact_substring_baseline(
    memory: DecisionEvidenceMemory,
    *,
    project_id: str,
    query_text: str,
    k: int,
) -> tuple[str, ...]:
    records = memory.search(
        MemorySearchQuery(
            project_id=project_id,
            text=query_text,
            authorities=_SAFE_AUTHORITIES,
            validation_classes=_SAFE_VALIDATION_CLASSES,
            latest_only=True,
            limit=k,
        )
    )
    return tuple(
        record.memory_id
        for record in records
        if not (
            record.kind is MemoryKind.ADR
            and record.decision_status is DecisionStatus.PROPOSED
        )
    )


def run_retrieval_benchmark(
    memory: DecisionEvidenceMemory,
    *,
    project_id: str,
    cases: tuple[RetrievalBenchmarkCase, ...],
    k: int = 3,
) -> RetrievalBenchmarkResult:
    if not cases:
        raise ValueError("benchmark cases must be non-empty")
    if not 1 <= k <= 10:
        raise ValueError("benchmark k must be between 1 and 10")

    retriever = PolicyControlledMemoryRetriever(memory)
    results: list[RetrievalBenchmarkCaseResult] = []
    baseline_recalls: list[float] = []
    retrieval_recalls: list[float] = []

    for case in cases:
        baseline_ids = _safe_exact_substring_baseline(
            memory,
            project_id=project_id,
            query_text=case.query_text,
            k=k,
        )
        package = retriever.retrieve(
            RetrievalRequest(
                project_id=project_id,
                query_text=case.query_text,
                max_results=k,
                candidate_limit=100,
                max_context_chars=50_000,
            )
        )
        retrieval_ids = tuple(item.memory_id for item in package.items)
        baseline_recall = _recall(baseline_ids, case.expected_memory_ids)
        retrieval_recall = _recall(retrieval_ids, case.expected_memory_ids)

        forbidden = set(case.forbidden_memory_ids)
        safety_pass = not (
            forbidden & set(baseline_ids)
            or forbidden & set(retrieval_ids)
        )

        if baseline_recall is None or retrieval_recall is None:
            not_worse = True
            improved = False
        else:
            baseline_recalls.append(baseline_recall)
            retrieval_recalls.append(retrieval_recall)
            not_worse = retrieval_recall >= baseline_recall
            improved = retrieval_recall > baseline_recall

        results.append(
            RetrievalBenchmarkCaseResult(
                case_id=case.case_id,
                baseline_memory_ids=baseline_ids,
                retrieval_memory_ids=retrieval_ids,
                baseline_recall_at_k=baseline_recall,
                retrieval_recall_at_k=retrieval_recall,
                safety_pass=safety_pass,
                retrieval_not_worse=not_worse,
                improved=improved,
            )
        )

    if not baseline_recalls:
        raise ValueError("benchmark must include at least one relevant case")

    return RetrievalBenchmarkResult(
        k=k,
        cases=tuple(results),
        baseline_mean_recall_at_k=sum(baseline_recalls) / len(baseline_recalls),
        retrieval_mean_recall_at_k=sum(retrieval_recalls) / len(retrieval_recalls),
        safety_pass=all(item.safety_pass for item in results),
        retrieval_not_worse_all_relevant_cases=all(
            item.retrieval_not_worse for item in results
        ),
        improved_case_count=sum(1 for item in results if item.improved),
    )
