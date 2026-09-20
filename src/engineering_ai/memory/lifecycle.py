"""Deterministic append-only knowledge lifecycle over engineering memory."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping
from uuid import uuid4

from engineering_ai.memory.store import (
    DecisionEvidenceMemory,
    MemoryAuthority,
    MemoryKind,
    MemoryRecord,
    MemoryValidationClass,
)

LIFECYCLE_SCHEMA_VERSION = "1.0"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,95}$")
_PROJECT_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")


class KnowledgeLifecycleError(RuntimeError):
    """Base error for deterministic knowledge lifecycle operations."""


class KnowledgeLifecycleConflictError(KnowledgeLifecycleError):
    pass


class KnowledgeLifecycleIntegrityError(KnowledgeLifecycleError):
    pass


class KnowledgeLifecyclePolicyError(KnowledgeLifecycleError):
    pass


class KnowledgeStage(str, Enum):
    OBSERVATION = "OBSERVATION"
    EVIDENCE = "EVIDENCE"
    ACCEPTED = "ACCEPTED"
    INVALIDATED = "INVALIDATED"


class KnowledgeAssessmentState(str, Enum):
    OBSERVATION = "OBSERVATION"
    EVIDENCE_CURRENT = "EVIDENCE_CURRENT"
    ACCEPTED_CURRENT = "ACCEPTED_CURRENT"
    STALE_SOURCE_REVISION = "STALE_SOURCE_REVISION"
    STALE_EVIDENCE_REVISION = "STALE_EVIDENCE_REVISION"
    INVALIDATED = "INVALIDATED"


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_freeze(item) for item in value), key=repr))
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _thaw(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_canonical(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _default_record_id() -> str:
    return f"knowrec-{uuid4().hex}"


@dataclass(frozen=True)
class KnowledgeBinding:
    memory_id: str
    record_id: str
    revision: int
    content_sha256: str
    kind: MemoryKind
    authority: MemoryAuthority
    validation_class: MemoryValidationClass

    @classmethod
    def from_record(cls, record: MemoryRecord) -> "KnowledgeBinding":
        return cls(
            memory_id=record.memory_id,
            record_id=record.record_id,
            revision=record.revision,
            content_sha256=record.content_sha256,
            kind=record.kind,
            authority=record.authority,
            validation_class=record.validation_class,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "record_id": self.record_id,
            "revision": self.revision,
            "content_sha256": self.content_sha256,
            "kind": self.kind.value,
            "authority": self.authority.value,
            "validation_class": self.validation_class.value,
        }


@dataclass(frozen=True)
class KnowledgeLifecycleRecord:
    lifecycle_record_id: str
    project_id: str
    knowledge_id: str
    revision: int
    stage: KnowledgeStage
    authority: MemoryAuthority
    claim: Mapping[str, Any]
    observation_record_ids: tuple[str, ...]
    evidence_bindings: tuple[KnowledgeBinding, ...]
    source_bindings: tuple[KnowledgeBinding, ...]
    provenance: tuple[str, ...]
    reason: str | None
    supersedes_lifecycle_record_id: str | None
    created_at: str
    content_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim", _freeze(dict(self.claim)))
        object.__setattr__(
            self, "observation_record_ids", tuple(self.observation_record_ids)
        )
        object.__setattr__(self, "evidence_bindings", tuple(self.evidence_bindings))
        object.__setattr__(self, "source_bindings", tuple(self.source_bindings))
        object.__setattr__(self, "provenance", tuple(self.provenance))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": LIFECYCLE_SCHEMA_VERSION,
            **_record_hash_payload(self),
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class KnowledgeAssessment:
    project_id: str
    knowledge_id: str
    lifecycle_record_id: str
    lifecycle_revision: int
    stage: KnowledgeStage
    state: KnowledgeAssessmentState
    stale_evidence_record_ids: tuple[str, ...] = ()
    stale_source_record_ids: tuple[str, ...] = ()
    physical_validation_inferred: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": LIFECYCLE_SCHEMA_VERSION,
            "project_id": self.project_id,
            "knowledge_id": self.knowledge_id,
            "lifecycle_record_id": self.lifecycle_record_id,
            "lifecycle_revision": self.lifecycle_revision,
            "stage": self.stage.value,
            "state": self.state.value,
            "stale_evidence_record_ids": list(self.stale_evidence_record_ids),
            "stale_source_record_ids": list(self.stale_source_record_ids),
            "physical_validation_inferred": self.physical_validation_inferred,
        }


@dataclass(frozen=True)
class KnowledgeLifecycleIntegrityReport:
    records_checked: int
    ok: bool


def _record_hash_payload(record: KnowledgeLifecycleRecord) -> dict[str, Any]:
    return {
        "schema_version": LIFECYCLE_SCHEMA_VERSION,
        "lifecycle_record_id": record.lifecycle_record_id,
        "project_id": record.project_id,
        "knowledge_id": record.knowledge_id,
        "revision": record.revision,
        "stage": record.stage.value,
        "authority": record.authority.value,
        "claim": _thaw(record.claim),
        "observation_record_ids": list(record.observation_record_ids),
        "evidence_bindings": [item.as_dict() for item in record.evidence_bindings],
        "source_bindings": [item.as_dict() for item in record.source_bindings],
        "provenance": list(record.provenance),
        "reason": record.reason,
        "supersedes_lifecycle_record_id": record.supersedes_lifecycle_record_id,
        "created_at": record.created_at,
    }


class KnowledgeLifecycleLedger:
    """Append-only local SQLite lifecycle ledger.

    It is intentionally separate from the Gate 016 memory database so Gate 018
    does not mutate or migrate accepted memory records.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        clock: Callable[[], datetime] = _default_clock,
        record_id_factory: Callable[[], str] = _default_record_id,
    ) -> None:
        raw = Path(database_path)
        if raw.exists() and raw.is_symlink():
            raise KnowledgeLifecyclePolicyError(
                "knowledge lifecycle database path must not be a symlink"
            )
        raw.parent.mkdir(parents=True, exist_ok=True)
        self._path = raw.resolve(strict=False)
        self._clock = clock
        self._record_id_factory = record_id_factory
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._initialize()

    @property
    def database_path(self) -> Path:
        return self._path

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "KnowledgeLifecycleLedger":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def latest(
        self,
        *,
        project_id: str,
        knowledge_id: str,
    ) -> KnowledgeLifecycleRecord:
        self._validate_project(project_id)
        row = self._conn.execute(
            """
            SELECT * FROM knowledge_lifecycle_records
            WHERE project_id = ? AND knowledge_id = ?
            ORDER BY revision DESC
            LIMIT 1
            """,
            (project_id, knowledge_id),
        ).fetchone()
        if row is None:
            raise KeyError(knowledge_id)
        return self._row_to_record(row)

    def history(
        self,
        *,
        project_id: str,
        knowledge_id: str,
    ) -> tuple[KnowledgeLifecycleRecord, ...]:
        self._validate_project(project_id)
        rows = self._conn.execute(
            """
            SELECT * FROM knowledge_lifecycle_records
            WHERE project_id = ? AND knowledge_id = ?
            ORDER BY revision ASC
            """,
            (project_id, knowledge_id),
        ).fetchall()
        return tuple(self._row_to_record(row) for row in rows)

    def verify_integrity(
        self,
        *,
        project_id: str | None = None,
    ) -> KnowledgeLifecycleIntegrityReport:
        if project_id is None:
            rows = self._conn.execute(
                "SELECT * FROM knowledge_lifecycle_records ORDER BY row_id ASC"
            ).fetchall()
        else:
            self._validate_project(project_id)
            rows = self._conn.execute(
                """
                SELECT * FROM knowledge_lifecycle_records
                WHERE project_id = ?
                ORDER BY row_id ASC
                """,
                (project_id,),
            ).fetchall()
        for row in rows:
            self._row_to_record(row)
        return KnowledgeLifecycleIntegrityReport(
            records_checked=len(rows),
            ok=True,
        )

    def _append(
        self,
        *,
        project_id: str,
        knowledge_id: str,
        stage: KnowledgeStage,
        authority: MemoryAuthority,
        claim: Mapping[str, Any],
        observation_record_ids: tuple[str, ...],
        evidence_bindings: tuple[KnowledgeBinding, ...],
        source_bindings: tuple[KnowledgeBinding, ...],
        provenance: tuple[str, ...],
        reason: str | None,
        supersedes_lifecycle_record_id: str | None,
    ) -> KnowledgeLifecycleRecord:
        self._validate_project(project_id)
        if not _ID_RE.fullmatch(knowledge_id):
            raise ValueError(f"invalid knowledge_id: {knowledge_id!r}")
        if authority not in {MemoryAuthority.HUMAN, MemoryAuthority.SUPERVISOR}:
            raise KnowledgeLifecyclePolicyError(
                "knowledge lifecycle transitions require HUMAN or SUPERVISOR authority"
            )
        if not provenance or any(not item.strip() for item in provenance):
            raise ValueError("provenance must contain non-empty entries")
        if stage is KnowledgeStage.OBSERVATION and not observation_record_ids:
            raise KnowledgeLifecyclePolicyError(
                "OBSERVATION requires at least one observation record"
            )
        if stage in {KnowledgeStage.EVIDENCE, KnowledgeStage.ACCEPTED} and not evidence_bindings:
            raise KnowledgeLifecyclePolicyError(
                f"{stage.value} requires evidence bindings"
            )
        if stage is KnowledgeStage.INVALIDATED and (reason is None or not reason.strip()):
            raise KnowledgeLifecyclePolicyError(
                "INVALIDATED requires a non-empty reason"
            )

        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("knowledge lifecycle clock must be timezone-aware")
        created_at = (
            now.astimezone(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
        lifecycle_record_id = self._record_id_factory()
        if not _ID_RE.fullmatch(lifecycle_record_id):
            raise ValueError(
                f"invalid lifecycle_record_id from factory: {lifecycle_record_id!r}"
            )

        self._conn.execute("BEGIN IMMEDIATE")
        try:
            latest_row = self._conn.execute(
                """
                SELECT * FROM knowledge_lifecycle_records
                WHERE project_id = ? AND knowledge_id = ?
                ORDER BY revision DESC
                LIMIT 1
                """,
                (project_id, knowledge_id),
            ).fetchone()

            if latest_row is None:
                if supersedes_lifecycle_record_id is not None:
                    raise KnowledgeLifecycleConflictError(
                        "new knowledge_id cannot supersede a lifecycle record"
                    )
                revision = 1
                exact_supersedes = None
            else:
                latest = self._row_to_record(latest_row)
                if supersedes_lifecycle_record_id is None:
                    raise KnowledgeLifecycleConflictError(
                        "existing knowledge_id requires exact lifecycle supersession"
                    )
                if supersedes_lifecycle_record_id != latest.lifecycle_record_id:
                    raise KnowledgeLifecycleConflictError(
                        "supersedes_lifecycle_record_id must reference latest exact revision"
                    )
                revision = latest.revision + 1
                exact_supersedes = latest.lifecycle_record_id

            record = KnowledgeLifecycleRecord(
                lifecycle_record_id=lifecycle_record_id,
                project_id=project_id,
                knowledge_id=knowledge_id,
                revision=revision,
                stage=stage,
                authority=authority,
                claim=claim,
                observation_record_ids=observation_record_ids,
                evidence_bindings=evidence_bindings,
                source_bindings=source_bindings,
                provenance=provenance,
                reason=reason.strip() if reason is not None else None,
                supersedes_lifecycle_record_id=exact_supersedes,
                created_at=created_at,
                content_sha256="",
            )
            record = KnowledgeLifecycleRecord(
                **{
                    **record.__dict__,
                    "content_sha256": _sha256_canonical(
                        _record_hash_payload(record)
                    ),
                }
            )
            self._insert_record(record)
            self._conn.commit()
            return record
        except Exception:
            self._conn.rollback()
            raise

    def _initialize(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS knowledge_lifecycle_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_lifecycle_records (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                lifecycle_record_id TEXT NOT NULL UNIQUE,
                project_id TEXT NOT NULL,
                knowledge_id TEXT NOT NULL,
                revision INTEGER NOT NULL CHECK (revision > 0),
                stage TEXT NOT NULL,
                authority TEXT NOT NULL,
                claim_json TEXT NOT NULL,
                observation_record_ids_json TEXT NOT NULL,
                evidence_bindings_json TEXT NOT NULL,
                source_bindings_json TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                reason TEXT,
                supersedes_lifecycle_record_id TEXT UNIQUE,
                created_at TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                UNIQUE(project_id, knowledge_id, revision),
                FOREIGN KEY(supersedes_lifecycle_record_id)
                    REFERENCES knowledge_lifecycle_records(lifecycle_record_id)
                    ON DELETE RESTRICT
            );

            CREATE INDEX IF NOT EXISTS idx_knowledge_lifecycle_project_id
                ON knowledge_lifecycle_records(project_id, knowledge_id, revision DESC);

            CREATE TRIGGER IF NOT EXISTS knowledge_lifecycle_no_update
            BEFORE UPDATE ON knowledge_lifecycle_records
            BEGIN
                SELECT RAISE(ABORT, 'append-only lifecycle: UPDATE prohibited');
            END;

            CREATE TRIGGER IF NOT EXISTS knowledge_lifecycle_no_delete
            BEFORE DELETE ON knowledge_lifecycle_records
            BEGIN
                SELECT RAISE(ABORT, 'append-only lifecycle: DELETE prohibited');
            END;
            """
        )
        row = self._conn.execute(
            "SELECT value FROM knowledge_lifecycle_meta WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            self._conn.execute(
                """
                INSERT INTO knowledge_lifecycle_meta(key, value)
                VALUES('schema_version', ?)
                """,
                (LIFECYCLE_SCHEMA_VERSION,),
            )
            self._conn.commit()
        elif row["value"] != LIFECYCLE_SCHEMA_VERSION:
            raise KnowledgeLifecyclePolicyError(
                f"unsupported lifecycle schema version: {row['value']!r}"
            )

    def _insert_record(self, record: KnowledgeLifecycleRecord) -> None:
        try:
            self._conn.execute(
                """
                INSERT INTO knowledge_lifecycle_records (
                    lifecycle_record_id,
                    project_id,
                    knowledge_id,
                    revision,
                    stage,
                    authority,
                    claim_json,
                    observation_record_ids_json,
                    evidence_bindings_json,
                    source_bindings_json,
                    provenance_json,
                    reason,
                    supersedes_lifecycle_record_id,
                    created_at,
                    content_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.lifecycle_record_id,
                    record.project_id,
                    record.knowledge_id,
                    record.revision,
                    record.stage.value,
                    record.authority.value,
                    _canonical_json(record.claim),
                    _canonical_json(record.observation_record_ids),
                    _canonical_json(
                        tuple(item.as_dict() for item in record.evidence_bindings)
                    ),
                    _canonical_json(
                        tuple(item.as_dict() for item in record.source_bindings)
                    ),
                    _canonical_json(record.provenance),
                    record.reason,
                    record.supersedes_lifecycle_record_id,
                    record.created_at,
                    record.content_sha256,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise KnowledgeLifecycleConflictError(str(exc)) from exc

    def _row_to_record(self, row: sqlite3.Row) -> KnowledgeLifecycleRecord:
        try:
            evidence_bindings = tuple(
                self._binding_from_dict(item)
                for item in json.loads(row["evidence_bindings_json"])
            )
            source_bindings = tuple(
                self._binding_from_dict(item)
                for item in json.loads(row["source_bindings_json"])
            )
            record = KnowledgeLifecycleRecord(
                lifecycle_record_id=row["lifecycle_record_id"],
                project_id=row["project_id"],
                knowledge_id=row["knowledge_id"],
                revision=int(row["revision"]),
                stage=KnowledgeStage(row["stage"]),
                authority=MemoryAuthority(row["authority"]),
                claim=json.loads(row["claim_json"]),
                observation_record_ids=tuple(
                    json.loads(row["observation_record_ids_json"])
                ),
                evidence_bindings=evidence_bindings,
                source_bindings=source_bindings,
                provenance=tuple(json.loads(row["provenance_json"])),
                reason=row["reason"],
                supersedes_lifecycle_record_id=row[
                    "supersedes_lifecycle_record_id"
                ],
                created_at=row["created_at"],
                content_sha256=row["content_sha256"],
            )
        except (ValueError, TypeError, json.JSONDecodeError, KeyError) as exc:
            raise KnowledgeLifecycleIntegrityError(
                f"invalid lifecycle record: {row['lifecycle_record_id']!r}"
            ) from exc

        if record.authority not in {
            MemoryAuthority.HUMAN,
            MemoryAuthority.SUPERVISOR,
        }:
            raise KnowledgeLifecycleIntegrityError(
                "stored lifecycle authority is not policy-qualified"
            )
        expected = _sha256_canonical(_record_hash_payload(record))
        if not hmac.compare_digest(expected, record.content_sha256):
            raise KnowledgeLifecycleIntegrityError(
                f"knowledge lifecycle hash mismatch for {record.lifecycle_record_id}"
            )
        return record

    @staticmethod
    def _binding_from_dict(data: Mapping[str, Any]) -> KnowledgeBinding:
        return KnowledgeBinding(
            memory_id=str(data["memory_id"]),
            record_id=str(data["record_id"]),
            revision=int(data["revision"]),
            content_sha256=str(data["content_sha256"]),
            kind=MemoryKind(data["kind"]),
            authority=MemoryAuthority(data["authority"]),
            validation_class=MemoryValidationClass(data["validation_class"]),
        )

    @staticmethod
    def _validate_project(project_id: str) -> None:
        if not _PROJECT_RE.fullmatch(project_id):
            raise ValueError(f"invalid project_id: {project_id!r}")


class KnowledgeLifecycle:
    """Deterministic controller for observation -> evidence -> accepted knowledge."""

    _EVIDENCE_CLASSES = {
        MemoryValidationClass.SOURCE,
        MemoryValidationClass.CALCULATION,
        MemoryValidationClass.SIMULATION,
        MemoryValidationClass.DETERMINISTIC_TEST,
        MemoryValidationClass.PHYSICAL,
    }

    def __init__(
        self,
        *,
        memory: DecisionEvidenceMemory,
        ledger: KnowledgeLifecycleLedger,
    ) -> None:
        self._memory = memory
        self._ledger = ledger

    @property
    def ledger(self) -> KnowledgeLifecycleLedger:
        return self._ledger

    def record_observation(
        self,
        *,
        project_id: str,
        knowledge_id: str,
        claim: Mapping[str, Any],
        observation_record_ids: tuple[str, ...],
        authority: MemoryAuthority = MemoryAuthority.SUPERVISOR,
        provenance: tuple[str, ...],
    ) -> KnowledgeLifecycleRecord:
        self._require_transition_authority(authority)
        if len(set(observation_record_ids)) != len(observation_record_ids):
            raise ValueError("observation_record_ids must be unique")
        records = self._require_current_records(
            project_id=project_id,
            record_ids=observation_record_ids,
        )
        for record in records:
            if record.validation_class is not MemoryValidationClass.ADVISORY:
                raise KnowledgeLifecyclePolicyError(
                    "observation records must remain ADVISORY"
                )
        return self._ledger._append(
            project_id=project_id,
            knowledge_id=knowledge_id,
            stage=KnowledgeStage.OBSERVATION,
            authority=authority,
            claim=claim,
            observation_record_ids=observation_record_ids,
            evidence_bindings=(),
            source_bindings=(),
            provenance=provenance,
            reason=None,
            supersedes_lifecycle_record_id=None,
        )

    def promote_to_evidence(
        self,
        *,
        project_id: str,
        knowledge_id: str,
        evidence_record_ids: tuple[str, ...],
        source_record_ids: tuple[str, ...] = (),
        authority: MemoryAuthority = MemoryAuthority.SUPERVISOR,
        provenance: tuple[str, ...],
    ) -> KnowledgeLifecycleRecord:
        self._require_transition_authority(authority)
        latest = self._ledger.latest(
            project_id=project_id,
            knowledge_id=knowledge_id,
        )
        if latest.stage is not KnowledgeStage.OBSERVATION:
            raise KnowledgeLifecyclePolicyError(
                "evidence promotion requires latest OBSERVATION stage"
            )
        if len(set(evidence_record_ids)) != len(evidence_record_ids):
            raise ValueError("evidence_record_ids must be unique")
        if len(set(source_record_ids)) != len(source_record_ids):
            raise ValueError("source_record_ids must be unique")
        if not set(source_record_ids).issubset(set(evidence_record_ids)):
            raise KnowledgeLifecyclePolicyError(
                "source_record_ids must be included in evidence_record_ids"
            )

        evidence_records = self._require_current_records(
            project_id=project_id,
            record_ids=evidence_record_ids,
        )
        by_id = {record.record_id: record for record in evidence_records}
        for record in evidence_records:
            self._validate_evidence_record(record)

        source_records = tuple(by_id[record_id] for record_id in source_record_ids)
        for record in source_records:
            if record.kind is not MemoryKind.SOURCE_REFERENCE:
                raise KnowledgeLifecyclePolicyError(
                    "source bindings require SOURCE_REFERENCE records"
                )

        return self._ledger._append(
            project_id=project_id,
            knowledge_id=knowledge_id,
            stage=KnowledgeStage.EVIDENCE,
            authority=authority,
            claim=latest.claim,
            observation_record_ids=latest.observation_record_ids,
            evidence_bindings=tuple(
                KnowledgeBinding.from_record(record)
                for record in evidence_records
            ),
            source_bindings=tuple(
                KnowledgeBinding.from_record(record)
                for record in source_records
            ),
            provenance=provenance,
            reason=None,
            supersedes_lifecycle_record_id=latest.lifecycle_record_id,
        )

    def accept(
        self,
        *,
        project_id: str,
        knowledge_id: str,
        authority: MemoryAuthority = MemoryAuthority.SUPERVISOR,
        provenance: tuple[str, ...],
    ) -> KnowledgeLifecycleRecord:
        self._require_transition_authority(authority)
        latest = self._ledger.latest(
            project_id=project_id,
            knowledge_id=knowledge_id,
        )
        if latest.stage is not KnowledgeStage.EVIDENCE:
            raise KnowledgeLifecyclePolicyError(
                "acceptance requires latest EVIDENCE stage"
            )
        assessment = self.assess(
            project_id=project_id,
            knowledge_id=knowledge_id,
        )
        if assessment.state is not KnowledgeAssessmentState.EVIDENCE_CURRENT:
            raise KnowledgeLifecyclePolicyError(
                f"cannot accept non-current evidence: {assessment.state.value}"
            )
        return self._ledger._append(
            project_id=project_id,
            knowledge_id=knowledge_id,
            stage=KnowledgeStage.ACCEPTED,
            authority=authority,
            claim=latest.claim,
            observation_record_ids=latest.observation_record_ids,
            evidence_bindings=latest.evidence_bindings,
            source_bindings=latest.source_bindings,
            provenance=provenance,
            reason=None,
            supersedes_lifecycle_record_id=latest.lifecycle_record_id,
        )

    def assess(
        self,
        *,
        project_id: str,
        knowledge_id: str,
    ) -> KnowledgeAssessment:
        latest = self._ledger.latest(
            project_id=project_id,
            knowledge_id=knowledge_id,
        )
        if latest.stage is KnowledgeStage.INVALIDATED:
            return self._assessment(
                latest,
                KnowledgeAssessmentState.INVALIDATED,
            )
        if latest.stage is KnowledgeStage.OBSERVATION:
            return self._assessment(
                latest,
                KnowledgeAssessmentState.OBSERVATION,
            )

        stale_evidence = tuple(
            binding.record_id
            for binding in latest.evidence_bindings
            if not self._binding_is_current(project_id, binding)
        )
        stale_source = tuple(
            binding.record_id
            for binding in latest.source_bindings
            if not self._binding_is_current(project_id, binding)
        )

        if stale_source:
            return self._assessment(
                latest,
                KnowledgeAssessmentState.STALE_SOURCE_REVISION,
                stale_evidence=stale_evidence,
                stale_source=stale_source,
            )
        if stale_evidence:
            return self._assessment(
                latest,
                KnowledgeAssessmentState.STALE_EVIDENCE_REVISION,
                stale_evidence=stale_evidence,
            )
        if latest.stage is KnowledgeStage.EVIDENCE:
            return self._assessment(
                latest,
                KnowledgeAssessmentState.EVIDENCE_CURRENT,
            )
        return self._assessment(
            latest,
            KnowledgeAssessmentState.ACCEPTED_CURRENT,
        )

    def invalidate_if_stale(
        self,
        *,
        project_id: str,
        knowledge_id: str,
        authority: MemoryAuthority = MemoryAuthority.SUPERVISOR,
        provenance: tuple[str, ...],
    ) -> KnowledgeLifecycleRecord:
        self._require_transition_authority(authority)
        latest = self._ledger.latest(
            project_id=project_id,
            knowledge_id=knowledge_id,
        )
        assessment = self.assess(
            project_id=project_id,
            knowledge_id=knowledge_id,
        )
        if assessment.state not in {
            KnowledgeAssessmentState.STALE_SOURCE_REVISION,
            KnowledgeAssessmentState.STALE_EVIDENCE_REVISION,
        }:
            raise KnowledgeLifecyclePolicyError(
                f"invalidation requires stale dependencies, got {assessment.state.value}"
            )
        reason = (
            f"{assessment.state.value}; "
            f"stale_evidence={','.join(assessment.stale_evidence_record_ids) or '-'}; "
            f"stale_source={','.join(assessment.stale_source_record_ids) or '-'}"
        )
        return self._ledger._append(
            project_id=project_id,
            knowledge_id=knowledge_id,
            stage=KnowledgeStage.INVALIDATED,
            authority=authority,
            claim=latest.claim,
            observation_record_ids=latest.observation_record_ids,
            evidence_bindings=latest.evidence_bindings,
            source_bindings=latest.source_bindings,
            provenance=provenance,
            reason=reason,
            supersedes_lifecycle_record_id=latest.lifecycle_record_id,
        )

    def history(
        self,
        *,
        project_id: str,
        knowledge_id: str,
    ) -> tuple[KnowledgeLifecycleRecord, ...]:
        return self._ledger.history(
            project_id=project_id,
            knowledge_id=knowledge_id,
        )

    @staticmethod
    def _require_transition_authority(authority: MemoryAuthority) -> None:
        if authority not in {MemoryAuthority.HUMAN, MemoryAuthority.SUPERVISOR}:
            raise KnowledgeLifecyclePolicyError(
                "MODEL/DETERMINISTIC_TOOL/IMPORTED_SOURCE cannot own lifecycle transitions"
            )

    def _require_current_records(
        self,
        *,
        project_id: str,
        record_ids: tuple[str, ...],
    ) -> tuple[MemoryRecord, ...]:
        if not record_ids:
            raise KnowledgeLifecyclePolicyError(
                "at least one memory record is required"
            )
        records: list[MemoryRecord] = []
        for record_id in record_ids:
            record = self._memory.get_record(
                project_id=project_id,
                record_id=record_id,
            )
            latest = self._memory.latest(
                project_id=project_id,
                memory_id=record.memory_id,
            )
            if latest.record_id != record.record_id:
                raise KnowledgeLifecyclePolicyError(
                    f"memory record is not latest revision: {record.record_id}"
                )
            records.append(record)
        return tuple(records)

    def _validate_evidence_record(self, record: MemoryRecord) -> None:
        if record.authority is MemoryAuthority.MODEL:
            raise KnowledgeLifecyclePolicyError(
                "model-authored records cannot be promoted to evidence"
            )
        if record.validation_class not in self._EVIDENCE_CLASSES:
            raise KnowledgeLifecyclePolicyError(
                f"validation class is not evidence-qualified: {record.validation_class.value}"
            )
        if record.validation_class is MemoryValidationClass.SOURCE:
            if not record.source_refs:
                raise KnowledgeLifecyclePolicyError(
                    "SOURCE evidence requires source_refs"
                )
        elif not record.evidence_refs:
            raise KnowledgeLifecyclePolicyError(
                f"{record.validation_class.value} evidence requires evidence_refs"
            )

    def _binding_is_current(
        self,
        project_id: str,
        binding: KnowledgeBinding,
    ) -> bool:
        bound = self._memory.get_record(
            project_id=project_id,
            record_id=binding.record_id,
        )
        if (
            bound.memory_id != binding.memory_id
            or bound.revision != binding.revision
            or not hmac.compare_digest(
                bound.content_sha256,
                binding.content_sha256,
            )
        ):
            raise KnowledgeLifecycleIntegrityError(
                f"bound memory identity mismatch: {binding.record_id}"
            )
        latest = self._memory.latest(
            project_id=project_id,
            memory_id=binding.memory_id,
        )
        return latest.record_id == binding.record_id

    @staticmethod
    def _assessment(
        record: KnowledgeLifecycleRecord,
        state: KnowledgeAssessmentState,
        *,
        stale_evidence: tuple[str, ...] = (),
        stale_source: tuple[str, ...] = (),
    ) -> KnowledgeAssessment:
        return KnowledgeAssessment(
            project_id=record.project_id,
            knowledge_id=record.knowledge_id,
            lifecycle_record_id=record.lifecycle_record_id,
            lifecycle_revision=record.revision,
            stage=record.stage,
            state=state,
            stale_evidence_record_ids=stale_evidence,
            stale_source_record_ids=stale_source,
            physical_validation_inferred=False,
        )
