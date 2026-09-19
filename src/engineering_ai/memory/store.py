"""Append-only local decision/evidence memory backed by SQLite."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping
from uuid import uuid4


SCHEMA_VERSION = "1.0"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,95}$")
_PROJECT_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")


class MemoryErrorBase(RuntimeError):
    """Base error for deterministic memory operations."""


class MemorySchemaError(MemoryErrorBase):
    pass


class MemoryConflictError(MemoryErrorBase):
    pass


class MemoryIntegrityError(MemoryErrorBase):
    pass


class MemoryPolicyError(MemoryErrorBase):
    pass


class MemoryKind(str, Enum):
    ADR = "ADR"
    CALCULATION = "CALCULATION"
    TEST_RESULT = "TEST_RESULT"
    FAILURE_LESSON = "FAILURE_LESSON"
    SOURCE_REFERENCE = "SOURCE_REFERENCE"


class MemoryAuthority(str, Enum):
    HUMAN = "HUMAN"
    SUPERVISOR = "SUPERVISOR"
    MODEL = "MODEL"
    DETERMINISTIC_TOOL = "DETERMINISTIC_TOOL"
    IMPORTED_SOURCE = "IMPORTED_SOURCE"


class MemoryValidationClass(str, Enum):
    CONTROL = "CONTROL"
    ADVISORY = "ADVISORY"
    SOURCE = "SOURCE"
    CALCULATION = "CALCULATION"
    SIMULATION = "SIMULATION"
    DETERMINISTIC_TEST = "DETERMINISTIC_TEST"
    PHYSICAL = "PHYSICAL"


class DecisionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"


class PhysicalValidationState(str, Enum):
    PHYSICAL_NOT_EXECUTED = "PHYSICAL_NOT_EXECUTED"
    PHYSICAL_PASS = "PHYSICAL_PASS"
    PHYSICAL_FAIL = "PHYSICAL_FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


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
    return f"memrec-{uuid4().hex}"


@dataclass(frozen=True)
class MemoryRecordDraft:
    project_id: str
    memory_id: str
    kind: MemoryKind
    authority: MemoryAuthority
    validation_class: MemoryValidationClass
    title: str
    summary: str
    content: Mapping[str, Any]
    provenance: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    decision_status: DecisionStatus | None = None
    physical_validation_state: PhysicalValidationState = (
        PhysicalValidationState.PHYSICAL_NOT_EXECUTED
    )

    def __post_init__(self) -> None:
        if not _PROJECT_RE.fullmatch(self.project_id):
            raise ValueError(f"invalid project_id: {self.project_id!r}")
        if not _ID_RE.fullmatch(self.memory_id):
            raise ValueError(f"invalid memory_id: {self.memory_id!r}")
        if not self.title.strip():
            raise ValueError("title must be non-empty")
        if not self.summary.strip():
            raise ValueError("summary must be non-empty")
        if not self.provenance:
            raise ValueError("provenance must be non-empty")
        if any(not item.strip() for item in self.provenance):
            raise ValueError("provenance entries must be non-empty")
        if any(not item.strip() for item in self.evidence_refs):
            raise ValueError("evidence_refs entries must be non-empty")
        if any(not item.strip() for item in self.source_refs):
            raise ValueError("source_refs entries must be non-empty")

        object.__setattr__(self, "content", _freeze(dict(self.content)))
        object.__setattr__(self, "provenance", tuple(self.provenance))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "source_refs", tuple(self.source_refs))
        _validate_semantics(self)


@dataclass(frozen=True)
class MemoryRecord:
    record_id: str
    project_id: str
    memory_id: str
    revision: int
    kind: MemoryKind
    authority: MemoryAuthority
    validation_class: MemoryValidationClass
    title: str
    summary: str
    content: Mapping[str, Any]
    provenance: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    decision_status: DecisionStatus | None
    physical_validation_state: PhysicalValidationState
    supersedes_record_id: str | None
    created_at: str
    content_sha256: str

    def __post_init__(self) -> None:
        if self.revision <= 0:
            raise ValueError("revision must be positive")
        object.__setattr__(self, "content", _freeze(dict(self.content)))
        object.__setattr__(self, "provenance", tuple(self.provenance))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "source_refs", tuple(self.source_refs))


@dataclass(frozen=True)
class MemorySearchQuery:
    project_id: str
    text: str | None = None
    kinds: tuple[MemoryKind, ...] = ()
    authorities: tuple[MemoryAuthority, ...] = ()
    validation_classes: tuple[MemoryValidationClass, ...] = ()
    latest_only: bool = True
    limit: int = 50

    def __post_init__(self) -> None:
        if not _PROJECT_RE.fullmatch(self.project_id):
            raise ValueError(f"invalid project_id: {self.project_id!r}")
        if not 1 <= self.limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if self.text is not None and not self.text.strip():
            raise ValueError("text search must be non-empty when provided")
        if len(set(self.kinds)) != len(self.kinds):
            raise ValueError("kinds must be unique")
        if len(set(self.authorities)) != len(self.authorities):
            raise ValueError("authorities must be unique")
        if len(set(self.validation_classes)) != len(self.validation_classes):
            raise ValueError("validation_classes must be unique")


@dataclass(frozen=True)
class MemoryIntegrityReport:
    records_checked: int
    ok: bool


def _validate_semantics(draft: MemoryRecordDraft) -> None:
    if draft.authority is MemoryAuthority.MODEL:
        if draft.validation_class is not MemoryValidationClass.ADVISORY:
            raise MemoryPolicyError("model-authored memory must remain ADVISORY")
        if draft.physical_validation_state not in {
            PhysicalValidationState.PHYSICAL_NOT_EXECUTED,
            PhysicalValidationState.NOT_APPLICABLE,
        }:
            raise MemoryPolicyError(
                "model-authored memory cannot claim physical PASS/FAIL"
            )

    if draft.kind is MemoryKind.ADR:
        if draft.decision_status is None:
            raise MemoryPolicyError("ADR records require decision_status")
        if draft.decision_status is DecisionStatus.ACCEPTED:
            if draft.authority is not MemoryAuthority.HUMAN:
                raise MemoryPolicyError("ACCEPTED ADR requires HUMAN authority")
            if draft.validation_class is not MemoryValidationClass.CONTROL:
                raise MemoryPolicyError(
                    "ACCEPTED ADR requires CONTROL validation class"
                )
    elif draft.decision_status is not None:
        raise MemoryPolicyError("decision_status is valid only for ADR records")

    if draft.kind is MemoryKind.SOURCE_REFERENCE:
        if draft.validation_class is not MemoryValidationClass.SOURCE:
            raise MemoryPolicyError(
                "SOURCE_REFERENCE requires SOURCE validation class"
            )
        if not draft.source_refs:
            raise MemoryPolicyError("SOURCE_REFERENCE requires source_refs")

    if draft.validation_class is MemoryValidationClass.DETERMINISTIC_TEST:
        if draft.authority is MemoryAuthority.MODEL:
            raise MemoryPolicyError(
                "DETERMINISTIC_TEST cannot have MODEL authority"
            )
        if not draft.evidence_refs:
            raise MemoryPolicyError(
                "DETERMINISTIC_TEST requires evidence_refs"
            )

    if draft.validation_class is MemoryValidationClass.PHYSICAL:
        if draft.authority not in {
            MemoryAuthority.HUMAN,
            MemoryAuthority.DETERMINISTIC_TOOL,
        }:
            raise MemoryPolicyError(
                "PHYSICAL evidence requires HUMAN or DETERMINISTIC_TOOL authority"
            )
        if not draft.evidence_refs:
            raise MemoryPolicyError("PHYSICAL evidence requires evidence_refs")
        if draft.physical_validation_state not in {
            PhysicalValidationState.PHYSICAL_PASS,
            PhysicalValidationState.PHYSICAL_FAIL,
        }:
            raise MemoryPolicyError(
                "PHYSICAL evidence requires explicit PHYSICAL_PASS or PHYSICAL_FAIL"
            )
    elif draft.physical_validation_state in {
        PhysicalValidationState.PHYSICAL_PASS,
        PhysicalValidationState.PHYSICAL_FAIL,
    }:
        raise MemoryPolicyError(
            "physical PASS/FAIL requires PHYSICAL validation class"
        )


def _record_hash_payload(record: MemoryRecord) -> dict[str, Any]:
    return {
        "record_id": record.record_id,
        "project_id": record.project_id,
        "memory_id": record.memory_id,
        "revision": record.revision,
        "kind": record.kind.value,
        "authority": record.authority.value,
        "validation_class": record.validation_class.value,
        "title": record.title,
        "summary": record.summary,
        "content": _thaw(record.content),
        "provenance": list(record.provenance),
        "evidence_refs": list(record.evidence_refs),
        "source_refs": list(record.source_refs),
        "decision_status": (
            record.decision_status.value
            if record.decision_status is not None
            else None
        ),
        "physical_validation_state": record.physical_validation_state.value,
        "supersedes_record_id": record.supersedes_record_id,
        "created_at": record.created_at,
    }


class DecisionEvidenceMemory:
    """Local append-only SQLite memory.

    Gate 016 deliberately exposes no semantic/vector retrieval and no automatic
    model-context integration.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        clock: Callable[[], datetime] = _default_clock,
        record_id_factory: Callable[[], str] = _default_record_id,
        max_scan_records: int = 10_000,
    ) -> None:
        if max_scan_records <= 0:
            raise ValueError("max_scan_records must be positive")
        raw = Path(database_path)
        if raw.exists() and raw.is_symlink():
            raise MemoryPolicyError("memory database path must not be a symlink")
        raw.parent.mkdir(parents=True, exist_ok=True)
        self._path = raw.resolve(strict=False)
        self._clock = clock
        self._record_id_factory = record_id_factory
        self._max_scan_records = max_scan_records
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._initialize()

    @property
    def database_path(self) -> Path:
        return self._path

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "DecisionEvidenceMemory":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def append(
        self,
        draft: MemoryRecordDraft,
        *,
        supersedes_record_id: str | None = None,
    ) -> MemoryRecord:
        _validate_semantics(draft)
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("memory clock must return timezone-aware datetime")
        created_at = (
            now.astimezone(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
        record_id = self._record_id_factory()
        if not _ID_RE.fullmatch(record_id):
            raise ValueError(f"invalid record_id from factory: {record_id!r}")

        self._conn.execute("BEGIN IMMEDIATE")
        try:
            latest_row = self._conn.execute(
                """
                SELECT * FROM memory_records
                WHERE project_id = ? AND memory_id = ?
                ORDER BY revision DESC
                LIMIT 1
                """,
                (draft.project_id, draft.memory_id),
            ).fetchone()

            if latest_row is None:
                if supersedes_record_id is not None:
                    raise MemoryConflictError(
                        "new memory_id cannot supersede an existing record"
                    )
                revision = 1
                exact_supersedes = None
            else:
                latest = self._row_to_record(latest_row)
                if supersedes_record_id is None:
                    raise MemoryConflictError(
                        "existing memory_id requires exact supersedes_record_id"
                    )
                if supersedes_record_id != latest.record_id:
                    raise MemoryConflictError(
                        "supersedes_record_id must reference the latest exact revision"
                    )
                revision = latest.revision + 1
                exact_supersedes = latest.record_id

            record = MemoryRecord(
                record_id=record_id,
                project_id=draft.project_id,
                memory_id=draft.memory_id,
                revision=revision,
                kind=draft.kind,
                authority=draft.authority,
                validation_class=draft.validation_class,
                title=draft.title.strip(),
                summary=draft.summary.strip(),
                content=draft.content,
                provenance=draft.provenance,
                evidence_refs=draft.evidence_refs,
                source_refs=draft.source_refs,
                decision_status=draft.decision_status,
                physical_validation_state=draft.physical_validation_state,
                supersedes_record_id=exact_supersedes,
                created_at=created_at,
                content_sha256="",
            )
            record = MemoryRecord(
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

    def get_record(self, *, project_id: str, record_id: str) -> MemoryRecord:
        self._validate_project(project_id)
        row = self._conn.execute(
            """
            SELECT * FROM memory_records
            WHERE project_id = ? AND record_id = ?
            """,
            (project_id, record_id),
        ).fetchone()
        if row is None:
            raise KeyError(record_id)
        return self._row_to_record(row)

    def latest(self, *, project_id: str, memory_id: str) -> MemoryRecord:
        self._validate_project(project_id)
        row = self._conn.execute(
            """
            SELECT * FROM memory_records
            WHERE project_id = ? AND memory_id = ?
            ORDER BY revision DESC
            LIMIT 1
            """,
            (project_id, memory_id),
        ).fetchone()
        if row is None:
            raise KeyError(memory_id)
        return self._row_to_record(row)

    def history(
        self,
        *,
        project_id: str,
        memory_id: str,
    ) -> tuple[MemoryRecord, ...]:
        self._validate_project(project_id)
        rows = self._conn.execute(
            """
            SELECT * FROM memory_records
            WHERE project_id = ? AND memory_id = ?
            ORDER BY revision ASC
            """,
            (project_id, memory_id),
        ).fetchall()
        return tuple(self._row_to_record(row) for row in rows)

    def search(self, query: MemorySearchQuery) -> tuple[MemoryRecord, ...]:
        clauses = ["r.project_id = ?"]
        params: list[Any] = [query.project_id]

        def add_enum_filter(column: str, values: Iterable[Enum]) -> None:
            items = tuple(item.value for item in values)
            if not items:
                return
            placeholders = ",".join("?" for _ in items)
            clauses.append(f"r.{column} IN ({placeholders})")
            params.extend(items)

        add_enum_filter("kind", query.kinds)
        add_enum_filter("authority", query.authorities)
        add_enum_filter("validation_class", query.validation_classes)

        if query.latest_only:
            clauses.append(
                """
                r.revision = (
                    SELECT MAX(r2.revision)
                    FROM memory_records AS r2
                    WHERE r2.project_id = r.project_id
                      AND r2.memory_id = r.memory_id
                )
                """
            )

        sql = (
            "SELECT r.* FROM memory_records AS r WHERE "
            + " AND ".join(clauses)
            + " ORDER BY r.row_id DESC LIMIT ?"
        )
        params.append(self._max_scan_records + 1)
        rows = self._conn.execute(sql, params).fetchall()
        if len(rows) > self._max_scan_records:
            raise MemoryPolicyError(
                "memory search candidate set exceeded max_scan_records"
            )

        needle = query.text.casefold() if query.text is not None else None
        results: list[MemoryRecord] = []
        for row in rows:
            record = self._row_to_record(row)
            if needle is not None:
                haystack = "\n".join(
                    (
                        record.title,
                        record.summary,
                        _canonical_json(record.content),
                    )
                ).casefold()
                if needle not in haystack:
                    continue
            results.append(record)
            if len(results) >= query.limit:
                break
        return tuple(results)

    def verify_integrity(
        self,
        *,
        project_id: str | None = None,
    ) -> MemoryIntegrityReport:
        if project_id is None:
            rows = self._conn.execute(
                "SELECT * FROM memory_records ORDER BY row_id ASC"
            ).fetchall()
        else:
            self._validate_project(project_id)
            rows = self._conn.execute(
                """
                SELECT * FROM memory_records
                WHERE project_id = ?
                ORDER BY row_id ASC
                """,
                (project_id,),
            ).fetchall()
        for row in rows:
            self._row_to_record(row)
        return MemoryIntegrityReport(records_checked=len(rows), ok=True)

    def _initialize(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS memory_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memory_records (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT NOT NULL UNIQUE,
                project_id TEXT NOT NULL,
                memory_id TEXT NOT NULL,
                revision INTEGER NOT NULL CHECK (revision > 0),
                kind TEXT NOT NULL,
                authority TEXT NOT NULL,
                validation_class TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                content_json TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                evidence_refs_json TEXT NOT NULL,
                source_refs_json TEXT NOT NULL,
                decision_status TEXT,
                physical_validation_state TEXT NOT NULL,
                supersedes_record_id TEXT UNIQUE,
                created_at TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                UNIQUE(project_id, memory_id, revision),
                FOREIGN KEY(supersedes_record_id)
                    REFERENCES memory_records(record_id)
                    ON DELETE RESTRICT
            );

            CREATE INDEX IF NOT EXISTS idx_memory_project_kind
                ON memory_records(project_id, kind);
            CREATE INDEX IF NOT EXISTS idx_memory_project_validation
                ON memory_records(project_id, validation_class);
            CREATE INDEX IF NOT EXISTS idx_memory_project_memory_revision
                ON memory_records(project_id, memory_id, revision DESC);

            CREATE TRIGGER IF NOT EXISTS memory_records_no_update
            BEFORE UPDATE ON memory_records
            BEGIN
                SELECT RAISE(ABORT, 'append-only memory: UPDATE prohibited');
            END;

            CREATE TRIGGER IF NOT EXISTS memory_records_no_delete
            BEFORE DELETE ON memory_records
            BEGIN
                SELECT RAISE(ABORT, 'append-only memory: DELETE prohibited');
            END;
            """
        )
        row = self._conn.execute(
            "SELECT value FROM memory_meta WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO memory_meta(key, value) VALUES('schema_version', ?)",
                (SCHEMA_VERSION,),
            )
            self._conn.commit()
        elif row["value"] != SCHEMA_VERSION:
            raise MemorySchemaError(
                f"unsupported memory schema version: {row['value']!r}"
            )

    def _insert_record(self, record: MemoryRecord) -> None:
        try:
            self._conn.execute(
                """
                INSERT INTO memory_records (
                    record_id,
                    project_id,
                    memory_id,
                    revision,
                    kind,
                    authority,
                    validation_class,
                    title,
                    summary,
                    content_json,
                    provenance_json,
                    evidence_refs_json,
                    source_refs_json,
                    decision_status,
                    physical_validation_state,
                    supersedes_record_id,
                    created_at,
                    content_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.record_id,
                    record.project_id,
                    record.memory_id,
                    record.revision,
                    record.kind.value,
                    record.authority.value,
                    record.validation_class.value,
                    record.title,
                    record.summary,
                    _canonical_json(record.content),
                    _canonical_json(record.provenance),
                    _canonical_json(record.evidence_refs),
                    _canonical_json(record.source_refs),
                    (
                        record.decision_status.value
                        if record.decision_status is not None
                        else None
                    ),
                    record.physical_validation_state.value,
                    record.supersedes_record_id,
                    record.created_at,
                    record.content_sha256,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise MemoryConflictError(str(exc)) from exc

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        try:
            record = MemoryRecord(
                record_id=row["record_id"],
                project_id=row["project_id"],
                memory_id=row["memory_id"],
                revision=int(row["revision"]),
                kind=MemoryKind(row["kind"]),
                authority=MemoryAuthority(row["authority"]),
                validation_class=MemoryValidationClass(
                    row["validation_class"]
                ),
                title=row["title"],
                summary=row["summary"],
                content=json.loads(row["content_json"]),
                provenance=tuple(json.loads(row["provenance_json"])),
                evidence_refs=tuple(json.loads(row["evidence_refs_json"])),
                source_refs=tuple(json.loads(row["source_refs_json"])),
                decision_status=(
                    DecisionStatus(row["decision_status"])
                    if row["decision_status"] is not None
                    else None
                ),
                physical_validation_state=PhysicalValidationState(
                    row["physical_validation_state"]
                ),
                supersedes_record_id=row["supersedes_record_id"],
                created_at=row["created_at"],
                content_sha256=row["content_sha256"],
            )
        except (ValueError, TypeError, json.JSONDecodeError, KeyError) as exc:
            raise MemoryIntegrityError(
                f"invalid stored memory record: {row['record_id']!r}"
            ) from exc

        expected = _sha256_canonical(_record_hash_payload(record))
        if not hashlib.compare_digest(expected, record.content_sha256):
            raise MemoryIntegrityError(
                f"memory hash mismatch for record {record.record_id}"
            )

        draft = MemoryRecordDraft(
            project_id=record.project_id,
            memory_id=record.memory_id,
            kind=record.kind,
            authority=record.authority,
            validation_class=record.validation_class,
            title=record.title,
            summary=record.summary,
            content=record.content,
            provenance=record.provenance,
            evidence_refs=record.evidence_refs,
            source_refs=record.source_refs,
            decision_status=record.decision_status,
            physical_validation_state=record.physical_validation_state,
        )
        _validate_semantics(draft)
        return record

    @staticmethod
    def _validate_project(project_id: str) -> None:
        if not _PROJECT_RE.fullmatch(project_id):
            raise ValueError(f"invalid project_id: {project_id!r}")
