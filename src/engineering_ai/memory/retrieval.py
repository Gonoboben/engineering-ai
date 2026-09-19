"""Policy-controlled provenance-preserving retrieval over Gate 016 memory."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from engineering_ai.memory.store import (
    DecisionEvidenceMemory,
    DecisionStatus,
    MemoryAuthority,
    MemoryKind,
    MemoryRecord,
    MemorySearchQuery,
    MemoryValidationClass,
)


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


class RetrievalPolicyError(RuntimeError):
    pass


class RetrievalStatus(str, Enum):
    READY = "READY"
    NO_RELEVANT_CONTEXT = "NO_RELEVANT_CONTEXT"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


_DEFAULT_VALIDATION_CLASSES = tuple(
    item
    for item in MemoryValidationClass
    if item is not MemoryValidationClass.ADVISORY
)
_DEFAULT_AUTHORITIES = tuple(
    item for item in MemoryAuthority if item is not MemoryAuthority.MODEL
)


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_TOKEN_RE.findall(value.casefold())))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    return value


def _stable_json(value: Any) -> str:
    return json.dumps(
        _jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


@dataclass(frozen=True)
class RetrievalRequest:
    project_id: str
    query_text: str
    kinds: tuple[MemoryKind, ...] = ()
    authorities: tuple[MemoryAuthority, ...] = ()
    validation_classes: tuple[MemoryValidationClass, ...] = ()
    include_advisory: bool = False
    include_proposed_adrs: bool = False
    include_history: bool = False
    candidate_limit: int = 100
    max_results: int = 8
    max_context_chars: int = 12_000

    def __post_init__(self) -> None:
        if not self.project_id.strip():
            raise ValueError("project_id must be non-empty")
        if not self.query_text.strip():
            raise ValueError("query_text must be non-empty")
        if not _tokens(self.query_text):
            raise ValueError("query_text must contain at least one word token")
        if not 1 <= self.candidate_limit <= 100:
            raise ValueError("candidate_limit must be between 1 and 100")
        if not 1 <= self.max_results <= self.candidate_limit:
            raise ValueError("max_results must be between 1 and candidate_limit")
        if not 256 <= self.max_context_chars <= 100_000:
            raise ValueError("max_context_chars must be between 256 and 100000")
        if len(set(self.kinds)) != len(self.kinds):
            raise ValueError("kinds must be unique")
        if len(set(self.authorities)) != len(self.authorities):
            raise ValueError("authorities must be unique")
        if len(set(self.validation_classes)) != len(self.validation_classes):
            raise ValueError("validation_classes must be unique")
        if not self.include_advisory:
            if MemoryAuthority.MODEL in self.authorities:
                raise RetrievalPolicyError(
                    "MODEL authority requires include_advisory=True"
                )
            if MemoryValidationClass.ADVISORY in self.validation_classes:
                raise RetrievalPolicyError(
                    "ADVISORY class requires include_advisory=True"
                )


@dataclass(frozen=True)
class RetrievedMemoryItem:
    record_id: str
    memory_id: str
    revision: int
    kind: MemoryKind
    authority: MemoryAuthority
    validation_class: MemoryValidationClass
    decision_status: DecisionStatus | None
    physical_validation_state: str
    title: str
    summary: str
    content: Mapping[str, Any]
    provenance: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    content_sha256: str
    relevance_score: int
    matched_terms: tuple[str, ...]
    is_latest_revision: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "content",
            MappingProxyType(dict(self.content)),
        )
        object.__setattr__(self, "provenance", tuple(self.provenance))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "source_refs", tuple(self.source_refs))
        object.__setattr__(self, "matched_terms", tuple(self.matched_terms))

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "memory_id": self.memory_id,
            "revision": self.revision,
            "kind": self.kind.value,
            "authority": self.authority.value,
            "validation_class": self.validation_class.value,
            "decision_status": (
                self.decision_status.value
                if self.decision_status is not None
                else None
            ),
            "physical_validation_state": self.physical_validation_state,
            "title": self.title,
            "summary": self.summary,
            "content": _jsonable(self.content),
            "provenance": list(self.provenance),
            "evidence_refs": list(self.evidence_refs),
            "source_refs": list(self.source_refs),
            "content_sha256": self.content_sha256,
            "relevance_score": self.relevance_score,
            "matched_terms": list(self.matched_terms),
            "is_latest_revision": self.is_latest_revision,
        }

    @property
    def serialized_chars(self) -> int:
        return len(_stable_json(self.as_dict()))


@dataclass(frozen=True)
class RetrievalContextPackage:
    project_id: str
    query_text: str
    items: tuple[RetrievedMemoryItem, ...]
    status: RetrievalStatus
    candidate_count: int
    relevant_count: int
    omitted_due_to_result_limit: int
    omitted_due_to_context_budget: int
    total_context_chars: int
    include_advisory: bool
    include_proposed_adrs: bool
    include_history: bool
    semantic_vector_backend: str = "DEFERRED_NOT_JUSTIFIED"

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "query_text": self.query_text,
            "status": self.status.value,
            "candidate_count": self.candidate_count,
            "relevant_count": self.relevant_count,
            "items": [item.as_dict() for item in self.items],
            "omitted_due_to_result_limit": self.omitted_due_to_result_limit,
            "omitted_due_to_context_budget": self.omitted_due_to_context_budget,
            "total_context_chars": self.total_context_chars,
            "include_advisory": self.include_advisory,
            "include_proposed_adrs": self.include_proposed_adrs,
            "include_history": self.include_history,
            "semantic_vector_backend": self.semantic_vector_backend,
            "automatic_context_injection": False,
        }


class PolicyControlledMemoryRetriever:
    """Read-only retrieval layer.

    The retriever preserves record validation/provenance metadata. It does not
    write memory, promote evidence, inject context into models/Blackboard, or
    invoke semantic/vector backends.
    """

    def __init__(self, memory: DecisionEvidenceMemory) -> None:
        self._memory = memory

    def retrieve(self, request: RetrievalRequest) -> RetrievalContextPackage:
        validation_classes = (
            request.validation_classes
            if request.validation_classes
            else (
                tuple(MemoryValidationClass)
                if request.include_advisory
                else _DEFAULT_VALIDATION_CLASSES
            )
        )
        authorities = (
            request.authorities
            if request.authorities
            else (
                tuple(MemoryAuthority)
                if request.include_advisory
                else _DEFAULT_AUTHORITIES
            )
        )

        candidates = self._memory.search(
            MemorySearchQuery(
                project_id=request.project_id,
                kinds=request.kinds,
                authorities=authorities,
                validation_classes=validation_classes,
                latest_only=not request.include_history,
                limit=request.candidate_limit,
            )
        )

        query_tokens = _tokens(request.query_text)
        ranked: list[tuple[int, tuple[str, ...], MemoryRecord]] = []
        for record in candidates:
            if not request.include_advisory and (
                record.authority is MemoryAuthority.MODEL
                or record.validation_class is MemoryValidationClass.ADVISORY
            ):
                continue
            if (
                record.kind is MemoryKind.ADR
                and record.decision_status is DecisionStatus.PROPOSED
                and not request.include_proposed_adrs
            ):
                continue

            score, matched = self._score(record, request.query_text, query_tokens)
            if score <= 0:
                continue
            ranked.append((score, matched, record))

        ranked.sort(
            key=lambda item: (
                -item[0],
                item[2].memory_id,
                -item[2].revision,
                item[2].record_id,
            )
        )

        relevant_count = len(ranked)
        omitted_due_to_result_limit = max(0, relevant_count - request.max_results)
        selected_ranked = ranked[: request.max_results]

        items: list[RetrievedMemoryItem] = []
        total_chars = 0
        budget_omitted = 0
        for score, matched, record in selected_ranked:
            latest = self._memory.latest(
                project_id=request.project_id,
                memory_id=record.memory_id,
            )
            item = self._to_item(
                record=record,
                score=score,
                matched=matched,
                is_latest=(latest.record_id == record.record_id),
            )
            size = item.serialized_chars
            if total_chars + size > request.max_context_chars:
                budget_omitted += 1
                continue
            items.append(item)
            total_chars += size

        if items:
            status = RetrievalStatus.READY
        elif relevant_count > 0 and budget_omitted > 0:
            status = RetrievalStatus.BUDGET_EXHAUSTED
        else:
            status = RetrievalStatus.NO_RELEVANT_CONTEXT

        return RetrievalContextPackage(
            project_id=request.project_id,
            query_text=request.query_text,
            items=tuple(items),
            status=status,
            candidate_count=len(candidates),
            relevant_count=relevant_count,
            omitted_due_to_result_limit=omitted_due_to_result_limit,
            omitted_due_to_context_budget=budget_omitted,
            total_context_chars=total_chars,
            include_advisory=request.include_advisory,
            include_proposed_adrs=request.include_proposed_adrs,
            include_history=request.include_history,
        )

    @staticmethod
    def _score(
        record: MemoryRecord,
        raw_query: str,
        query_tokens: tuple[str, ...],
    ) -> tuple[int, tuple[str, ...]]:
        title = record.title.casefold()
        summary = record.summary.casefold()
        content = _stable_json(record.content).casefold()
        phrase = raw_query.strip().casefold()

        score = 0
        if phrase in title:
            score += 18
        if phrase in summary:
            score += 12
        if phrase in content:
            score += 6

        matched: list[str] = []
        title_tokens = set(_tokens(title))
        summary_tokens = set(_tokens(summary))
        content_tokens = set(_tokens(content))

        for token in query_tokens:
            token_score = 0
            if token in title_tokens:
                token_score += 7
            if token in summary_tokens:
                token_score += 4
            if token in content_tokens:
                token_score += 2
            if token_score:
                matched.append(token)
                score += token_score

        if query_tokens and len(matched) == len(query_tokens):
            score += 10

        return score, tuple(matched)

    @staticmethod
    def _to_item(
        *,
        record: MemoryRecord,
        score: int,
        matched: tuple[str, ...],
        is_latest: bool,
    ) -> RetrievedMemoryItem:
        return RetrievedMemoryItem(
            record_id=record.record_id,
            memory_id=record.memory_id,
            revision=record.revision,
            kind=record.kind,
            authority=record.authority,
            validation_class=record.validation_class,
            decision_status=record.decision_status,
            physical_validation_state=record.physical_validation_state.value,
            title=record.title,
            summary=record.summary,
            content=record.content,
            provenance=record.provenance,
            evidence_refs=record.evidence_refs,
            source_refs=record.source_refs,
            content_sha256=record.content_sha256,
            relevance_score=score,
            matched_terms=matched,
            is_latest_revision=is_latest,
        )

    @staticmethod
    def assert_read_only_surface(instance: object) -> None:
        for name in (
            "append",
            "update",
            "delete",
            "execute",
            "execute_sql",
            "inject_context",
            "write_blackboard",
            "promote_evidence",
            "semantic_search",
            "vector_search",
        ):
            if hasattr(instance, name):
                raise RetrievalPolicyError(
                    f"forbidden Gate 017 retrieval API exposed: {name}"
                )
