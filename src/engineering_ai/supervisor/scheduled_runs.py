"""Deterministic persisted one-shot scheduled runs for Gate 020."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping
from uuid import uuid4

from engineering_ai.supervisor.core import Supervisor, ToolCallable, ToolOutcome
from engineering_ai.supervisor.policy import Decision


SCHEDULE_SCHEMA_VERSION = "1.0"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,95}$")
_PROJECT_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
_SUMMARY_STATES = (
    "PASS",
    "FAIL",
    "BLOCKED",
    "WAITING_FOR_APPROVAL",
    "CANCELLED",
    "QUEUED",
)


class ScheduledRunError(RuntimeError):
    """Base error for scheduled-run persistence/execution."""


class ScheduledRunConflictError(ScheduledRunError):
    pass


class ScheduledRunIntegrityError(ScheduledRunError):
    pass


class ScheduledRunPolicyError(ScheduledRunError):
    pass


class ScheduleEventType(str, Enum):
    SCHEDULED = "SCHEDULED"
    SESSION_STARTED = "SESSION_STARTED"
    SESSION_COMPLETED = "SESSION_COMPLETED"
    SESSION_BLOCKED = "SESSION_BLOCKED"
    CANCELLED = "CANCELLED"


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _default_event_id() -> str:
    return f"sevt-{uuid4().hex}"


def _default_session_id() -> str:
    return f"session-{uuid4().hex}"


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("scheduled-run clock must return timezone-aware datetime")
    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ScheduledRunDefinition:
    schedule_id: str
    project_id: str
    due_at: str
    allowed_actions: tuple[str, ...]
    max_jobs: int
    max_session_seconds: int

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.schedule_id):
            raise ValueError("invalid schedule_id")
        if not _PROJECT_RE.fullmatch(self.project_id):
            raise ValueError("invalid project_id")
        _parse_utc(self.due_at)
        if not self.allowed_actions:
            raise ValueError("allowed_actions must be non-empty")
        if len(set(self.allowed_actions)) != len(self.allowed_actions):
            raise ValueError("allowed_actions must be unique")
        if any(not action.strip() for action in self.allowed_actions):
            raise ValueError("allowed_actions must be non-empty strings")
        if not 1 <= self.max_jobs <= 100:
            raise ValueError("max_jobs must be between 1 and 100")
        if not 1 <= self.max_session_seconds <= 86_400:
            raise ValueError("max_session_seconds must be between 1 and 86400")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "project_id": self.project_id,
            "due_at": self.due_at,
            "allowed_actions": list(self.allowed_actions),
            "max_jobs": self.max_jobs,
            "max_session_seconds": self.max_session_seconds,
        }


@dataclass(frozen=True)
class ScheduledRunSummary:
    session_id: str
    schedule_id: str
    project_id: str
    started_at: str
    completed_at: str
    stop_reason: str
    claims: int
    touched_job_ids: tuple[str, ...]
    recovered_interrupted_job_ids: tuple[str, ...]
    counts: Mapping[str, int]
    evidence_refs: tuple[str, ...]
    physical_validation: str = "PHYSICAL_NOT_EXECUTED"

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.session_id):
            raise ValueError("invalid session_id")
        if not _ID_RE.fullmatch(self.schedule_id):
            raise ValueError("invalid schedule_id")
        if not _PROJECT_RE.fullmatch(self.project_id):
            raise ValueError("invalid project_id")
        _parse_utc(self.started_at)
        _parse_utc(self.completed_at)
        if not self.stop_reason.strip():
            raise ValueError("stop_reason must be non-empty")
        if self.claims < 0:
            raise ValueError("claims must be non-negative")
        if len(set(self.touched_job_ids)) != len(self.touched_job_ids):
            raise ValueError("touched_job_ids must be unique")
        if len(set(self.recovered_interrupted_job_ids)) != len(
            self.recovered_interrupted_job_ids
        ):
            raise ValueError("recovered_interrupted_job_ids must be unique")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("evidence_refs must be unique")
        normalized = {state: int(self.counts.get(state, 0)) for state in _SUMMARY_STATES}
        if set(self.counts) != set(_SUMMARY_STATES):
            raise ValueError("counts must contain exactly the supported summary states")
        if any(value < 0 for value in normalized.values()):
            raise ValueError("summary counts must be non-negative")
        object.__setattr__(self, "counts", MappingProxyType(normalized))
        if self.physical_validation != "PHYSICAL_NOT_EXECUTED":
            raise ValueError("scheduled run cannot infer physical validation")

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "schedule_id": self.schedule_id,
            "project_id": self.project_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "stop_reason": self.stop_reason,
            "claims": self.claims,
            "touched_job_ids": list(self.touched_job_ids),
            "recovered_interrupted_job_ids": list(
                self.recovered_interrupted_job_ids
            ),
            "counts": dict(self.counts),
            "evidence_refs": list(self.evidence_refs),
            "physical_validation": self.physical_validation,
        }


@dataclass(frozen=True)
class ScheduledRunSnapshot:
    sequence: int
    event_id: str
    definition: ScheduledRunDefinition
    event_type: ScheduleEventType
    session_id: str | None
    summary: ScheduledRunSummary | None
    reason: str | None
    supersedes_event_id: str | None
    created_at: str
    content_sha256: str

    @property
    def schedule_id(self) -> str:
        return self.definition.schedule_id

    @property
    def project_id(self) -> str:
        return self.definition.project_id

    @property
    def terminal(self) -> bool:
        return self.event_type in {
            ScheduleEventType.SESSION_COMPLETED,
            ScheduleEventType.SESSION_BLOCKED,
            ScheduleEventType.CANCELLED,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEDULE_SCHEMA_VERSION,
            "sequence": self.sequence,
            **_hash_payload(self),
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class ScheduledRunIntegrityReport:
    events_checked: int
    schedules_checked: int
    ok: bool


def _hash_payload(snapshot: ScheduledRunSnapshot) -> dict[str, Any]:
    return {
        "schema_version": SCHEDULE_SCHEMA_VERSION,
        "event_id": snapshot.event_id,
        "definition": snapshot.definition.as_dict(),
        "event_type": snapshot.event_type.value,
        "session_id": snapshot.session_id,
        "summary": snapshot.summary.as_dict() if snapshot.summary else None,
        "reason": snapshot.reason,
        "supersedes_event_id": snapshot.supersedes_event_id,
        "created_at": snapshot.created_at,
    }


class PersistedScheduledRunStore:
    """Append-only one-shot schedule/session history.

    This store never executes jobs, grants permissions, or installs an OS scheduler.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        clock: Callable[[], datetime] = _default_clock,
        event_id_factory: Callable[[], str] = _default_event_id,
        session_id_factory: Callable[[], str] = _default_session_id,
        max_schedules: int = 10_000,
    ) -> None:
        raw = Path(database_path)
        if raw.exists() and raw.is_symlink():
            raise ScheduledRunPolicyError("scheduled-run database path must not be symlink")
        if max_schedules <= 0:
            raise ValueError("max_schedules must be positive")
        raw.parent.mkdir(parents=True, exist_ok=True)
        self._path = raw.resolve(strict=False)
        self._clock = clock
        self._event_id_factory = event_id_factory
        self._session_id_factory = session_id_factory
        self._max_schedules = max_schedules
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._initialize()

    @property
    def database_path(self) -> Path:
        return self._path

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "PersistedScheduledRunStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def schedule(self, definition: ScheduledRunDefinition) -> ScheduledRunSnapshot:
        existing = self._latest_row(
            project_id=definition.project_id,
            schedule_id=definition.schedule_id,
        )
        if existing is not None:
            raise ScheduledRunConflictError("schedule already exists")
        return self._append(
            definition=definition,
            event_type=ScheduleEventType.SCHEDULED,
            session_id=None,
            summary=None,
            reason=None,
            expected_latest_event_id=None,
        )

    def history(
        self,
        *,
        project_id: str,
        schedule_id: str,
    ) -> tuple[ScheduledRunSnapshot, ...]:
        self._validate_project(project_id)
        rows = self._conn.execute(
            """
            SELECT * FROM scheduled_run_events
            WHERE project_id = ? AND schedule_id = ?
            ORDER BY row_id ASC
            """,
            (project_id, schedule_id),
        ).fetchall()
        snapshots = tuple(self._row_to_snapshot(row) for row in rows)
        self._validate_history(snapshots)
        return snapshots

    def get(
        self,
        *,
        project_id: str,
        schedule_id: str,
    ) -> ScheduledRunSnapshot:
        history = self.history(project_id=project_id, schedule_id=schedule_id)
        if not history:
            raise KeyError(schedule_id)
        return history[-1]

    def list_current(
        self,
        *,
        project_id: str,
    ) -> tuple[ScheduledRunSnapshot, ...]:
        self._validate_project(project_id)
        rows = self._conn.execute(
            """
            SELECT e.*
            FROM scheduled_run_events AS e
            JOIN (
                SELECT schedule_id, MAX(row_id) AS max_row_id
                FROM scheduled_run_events
                WHERE project_id = ?
                GROUP BY schedule_id
            ) AS latest
              ON e.row_id = latest.max_row_id
            WHERE e.project_id = ?
            ORDER BY e.row_id ASC
            LIMIT ?
            """,
            (project_id, project_id, self._max_schedules + 1),
        ).fetchall()
        if len(rows) > self._max_schedules:
            raise ScheduledRunPolicyError("persisted schedule count exceeded max_schedules")
        current: list[ScheduledRunSnapshot] = []
        for row in rows:
            history = self.history(
                project_id=project_id,
                schedule_id=str(row["schedule_id"]),
            )
            if not history:
                raise ScheduledRunIntegrityError("current schedule has no history")
            current.append(history[-1])
        return tuple(current)

    def next_due(
        self,
        *,
        project_id: str,
    ) -> ScheduledRunSnapshot | None:
        now = self._clock().astimezone(timezone.utc)
        due = [
            item
            for item in self.list_current(project_id=project_id)
            if item.event_type is ScheduleEventType.SCHEDULED
            and _parse_utc(item.definition.due_at) <= now
        ]
        if not due:
            return None
        due.sort(key=lambda item: (_parse_utc(item.definition.due_at), item.sequence))
        return due[0]

    def start_next_due(
        self,
        *,
        project_id: str,
    ) -> ScheduledRunSnapshot | None:
        due = self.next_due(project_id=project_id)
        if due is None:
            return None
        session_id = self._session_id_factory()
        if not _ID_RE.fullmatch(session_id):
            raise ValueError("invalid session_id")
        return self._append(
            definition=due.definition,
            event_type=ScheduleEventType.SESSION_STARTED,
            session_id=session_id,
            summary=None,
            reason=None,
            expected_latest_event_id=due.event_id,
        )

    def complete(
        self,
        *,
        project_id: str,
        schedule_id: str,
        summary: ScheduledRunSummary,
    ) -> ScheduledRunSnapshot:
        latest = self.get(project_id=project_id, schedule_id=schedule_id)
        if latest.event_type is not ScheduleEventType.SESSION_STARTED:
            raise ScheduledRunPolicyError("schedule has no active session")
        if latest.session_id != summary.session_id:
            raise ScheduledRunPolicyError("summary session_id mismatch")
        if summary.schedule_id != schedule_id or summary.project_id != project_id:
            raise ScheduledRunPolicyError("summary schedule/project mismatch")
        return self._append(
            definition=latest.definition,
            event_type=ScheduleEventType.SESSION_COMPLETED,
            session_id=summary.session_id,
            summary=summary,
            reason=None,
            expected_latest_event_id=latest.event_id,
        )

    def recover_interrupted_sessions(
        self,
        *,
        project_id: str,
        reason: str = "process restart interrupted scheduled session",
    ) -> tuple[ScheduledRunSnapshot, ...]:
        if not reason.strip():
            raise ValueError("reason must be non-empty")
        recovered: list[ScheduledRunSnapshot] = []
        for latest in self.list_current(project_id=project_id):
            if latest.event_type is not ScheduleEventType.SESSION_STARTED:
                continue
            recovered.append(
                self._append(
                    definition=latest.definition,
                    event_type=ScheduleEventType.SESSION_BLOCKED,
                    session_id=latest.session_id,
                    summary=None,
                    reason=reason.strip(),
                    expected_latest_event_id=latest.event_id,
                )
            )
        return tuple(recovered)

    def cancel(
        self,
        *,
        project_id: str,
        schedule_id: str,
        reason: str,
    ) -> ScheduledRunSnapshot:
        latest = self.get(project_id=project_id, schedule_id=schedule_id)
        if latest.event_type is not ScheduleEventType.SCHEDULED:
            raise ScheduledRunPolicyError("only pending schedule can be cancelled")
        if not reason.strip():
            raise ValueError("reason must be non-empty")
        return self._append(
            definition=latest.definition,
            event_type=ScheduleEventType.CANCELLED,
            session_id=None,
            summary=None,
            reason=reason.strip(),
            expected_latest_event_id=latest.event_id,
        )

    def verify_integrity(
        self,
        *,
        project_id: str | None = None,
    ) -> ScheduledRunIntegrityReport:
        if project_id is None:
            rows = self._conn.execute(
                "SELECT * FROM scheduled_run_events ORDER BY row_id ASC"
            ).fetchall()
        else:
            self._validate_project(project_id)
            rows = self._conn.execute(
                """
                SELECT * FROM scheduled_run_events
                WHERE project_id = ?
                ORDER BY row_id ASC
                """,
                (project_id,),
            ).fetchall()
        grouped: dict[tuple[str, str], list[ScheduledRunSnapshot]] = {}
        for row in rows:
            snapshot = self._row_to_snapshot(row)
            key = (snapshot.project_id, snapshot.schedule_id)
            grouped.setdefault(key, []).append(snapshot)
        for snapshots in grouped.values():
            self._validate_history(tuple(snapshots))
        return ScheduledRunIntegrityReport(
            events_checked=len(rows),
            schedules_checked=len(grouped),
            ok=True,
        )

    def _append(
        self,
        *,
        definition: ScheduledRunDefinition,
        event_type: ScheduleEventType,
        session_id: str | None,
        summary: ScheduledRunSummary | None,
        reason: str | None,
        expected_latest_event_id: str | None,
    ) -> ScheduledRunSnapshot:
        created_at = _utc_iso(self._clock())
        event_id = self._event_id_factory()
        if not _ID_RE.fullmatch(event_id):
            raise ValueError("invalid scheduled-run event_id")

        self._conn.execute("BEGIN IMMEDIATE")
        try:
            latest_row = self._latest_row(
                project_id=definition.project_id,
                schedule_id=definition.schedule_id,
            )
            latest = self._row_to_snapshot(latest_row) if latest_row else None
            if expected_latest_event_id is None:
                if latest is not None:
                    raise ScheduledRunConflictError("initial schedule already exists")
                supersedes = None
            else:
                if latest is None or latest.event_id != expected_latest_event_id:
                    raise ScheduledRunConflictError("scheduled-run head changed")
                supersedes = latest.event_id

            provisional = ScheduledRunSnapshot(
                sequence=1,
                event_id=event_id,
                definition=definition,
                event_type=event_type,
                session_id=session_id,
                summary=summary,
                reason=reason,
                supersedes_event_id=supersedes,
                created_at=created_at,
                content_sha256="",
            )
            content_sha256 = _sha256(_hash_payload(provisional))
            cursor = self._conn.execute(
                """
                INSERT INTO scheduled_run_events (
                    event_id, project_id, schedule_id, definition_json,
                    event_type, session_id, summary_json, reason,
                    supersedes_event_id, created_at, content_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    definition.project_id,
                    definition.schedule_id,
                    _canonical_json(definition.as_dict()),
                    event_type.value,
                    session_id,
                    _canonical_json(summary.as_dict()) if summary else None,
                    reason,
                    supersedes,
                    created_at,
                    content_sha256,
                ),
            )
            row_id = int(cursor.lastrowid)
            self._conn.commit()
            return ScheduledRunSnapshot(
                sequence=row_id,
                event_id=event_id,
                definition=definition,
                event_type=event_type,
                session_id=session_id,
                summary=summary,
                reason=reason,
                supersedes_event_id=supersedes,
                created_at=created_at,
                content_sha256=content_sha256,
            )
        except Exception:
            self._conn.rollback()
            raise

    def _latest_row(
        self,
        *,
        project_id: str,
        schedule_id: str,
    ) -> sqlite3.Row | None:
        return self._conn.execute(
            """
            SELECT * FROM scheduled_run_events
            WHERE project_id = ? AND schedule_id = ?
            ORDER BY row_id DESC
            LIMIT 1
            """,
            (project_id, schedule_id),
        ).fetchone()

    def _row_to_snapshot(self, row: sqlite3.Row) -> ScheduledRunSnapshot:
        try:
            raw_definition = json.loads(row["definition_json"])
            definition = ScheduledRunDefinition(
                schedule_id=raw_definition["schedule_id"],
                project_id=raw_definition["project_id"],
                due_at=raw_definition["due_at"],
                allowed_actions=tuple(raw_definition["allowed_actions"]),
                max_jobs=int(raw_definition["max_jobs"]),
                max_session_seconds=int(raw_definition["max_session_seconds"]),
            )
            raw_summary = json.loads(row["summary_json"]) if row["summary_json"] else None
            summary = (
                ScheduledRunSummary(
                    session_id=raw_summary["session_id"],
                    schedule_id=raw_summary["schedule_id"],
                    project_id=raw_summary["project_id"],
                    started_at=raw_summary["started_at"],
                    completed_at=raw_summary["completed_at"],
                    stop_reason=raw_summary["stop_reason"],
                    claims=int(raw_summary["claims"]),
                    touched_job_ids=tuple(raw_summary["touched_job_ids"]),
                    recovered_interrupted_job_ids=tuple(
                        raw_summary["recovered_interrupted_job_ids"]
                    ),
                    counts=raw_summary["counts"],
                    evidence_refs=tuple(raw_summary["evidence_refs"]),
                    physical_validation=raw_summary["physical_validation"],
                )
                if raw_summary
                else None
            )
            snapshot = ScheduledRunSnapshot(
                sequence=int(row["row_id"]),
                event_id=row["event_id"],
                definition=definition,
                event_type=ScheduleEventType(row["event_type"]),
                session_id=row["session_id"],
                summary=summary,
                reason=row["reason"],
                supersedes_event_id=row["supersedes_event_id"],
                created_at=row["created_at"],
                content_sha256=row["content_sha256"],
            )
        except Exception as exc:
            raise ScheduledRunIntegrityError("invalid persisted scheduled-run event") from exc

        if definition.project_id != row["project_id"] or definition.schedule_id != row["schedule_id"]:
            raise ScheduledRunIntegrityError("scheduled-run identity mismatch")
        self._validate_event(snapshot)
        expected = _sha256(_hash_payload(snapshot))
        if not hmac.compare_digest(expected, snapshot.content_sha256):
            raise ScheduledRunIntegrityError(
                f"scheduled-run hash mismatch for {snapshot.event_id}"
            )
        return snapshot

    @staticmethod
    def _validate_event(snapshot: ScheduledRunSnapshot) -> None:
        _parse_utc(snapshot.created_at)
        event = snapshot.event_type
        if event is ScheduleEventType.SCHEDULED:
            if (
                snapshot.supersedes_event_id is not None
                or snapshot.session_id is not None
                or snapshot.summary is not None
                or snapshot.reason is not None
            ):
                raise ScheduledRunIntegrityError("invalid SCHEDULED event")
        elif event is ScheduleEventType.SESSION_STARTED:
            if (
                snapshot.supersedes_event_id is None
                or snapshot.session_id is None
                or snapshot.summary is not None
                or snapshot.reason is not None
            ):
                raise ScheduledRunIntegrityError("invalid SESSION_STARTED event")
        elif event is ScheduleEventType.SESSION_COMPLETED:
            if (
                snapshot.supersedes_event_id is None
                or snapshot.session_id is None
                or snapshot.summary is None
                or snapshot.reason is not None
            ):
                raise ScheduledRunIntegrityError("invalid SESSION_COMPLETED event")
        elif event is ScheduleEventType.SESSION_BLOCKED:
            if (
                snapshot.supersedes_event_id is None
                or snapshot.session_id is None
                or snapshot.summary is not None
                or not snapshot.reason
            ):
                raise ScheduledRunIntegrityError("invalid SESSION_BLOCKED event")
        elif event is ScheduleEventType.CANCELLED:
            if (
                snapshot.supersedes_event_id is None
                or snapshot.session_id is not None
                or snapshot.summary is not None
                or not snapshot.reason
            ):
                raise ScheduledRunIntegrityError("invalid CANCELLED event")

    @staticmethod
    def _validate_history(snapshots: tuple[ScheduledRunSnapshot, ...]) -> None:
        if not snapshots:
            return
        first = snapshots[0]
        if first.event_type is not ScheduleEventType.SCHEDULED:
            raise ScheduledRunIntegrityError("schedule history must start SCHEDULED")
        definition = first.definition
        previous = first
        for item in snapshots[1:]:
            if item.definition != definition:
                raise ScheduledRunIntegrityError("schedule definition mutated")
            if item.supersedes_event_id != previous.event_id:
                raise ScheduledRunIntegrityError("schedule supersession chain broken")
            previous = item
        if len(snapshots) > 3:
            raise ScheduledRunIntegrityError("one-shot schedule has too many events")
        if len(snapshots) >= 2:
            second = snapshots[1].event_type
            if second not in {
                ScheduleEventType.SESSION_STARTED,
                ScheduleEventType.CANCELLED,
            }:
                raise ScheduledRunIntegrityError("invalid schedule second transition")
        if len(snapshots) == 3:
            if snapshots[1].event_type is not ScheduleEventType.SESSION_STARTED:
                raise ScheduledRunIntegrityError(
                    "terminal session event requires SESSION_STARTED predecessor"
                )
            if snapshots[2].event_type not in {
                ScheduleEventType.SESSION_COMPLETED,
                ScheduleEventType.SESSION_BLOCKED,
            }:
                raise ScheduledRunIntegrityError("invalid scheduled session terminal event")
            if snapshots[2].session_id != snapshots[1].session_id:
                raise ScheduledRunIntegrityError("scheduled session identity changed")
            if snapshots[2].summary is not None:
                if snapshots[2].summary.started_at != snapshots[1].created_at:
                    raise ScheduledRunIntegrityError(
                        "scheduled summary start does not match session start"
                    )

    @staticmethod
    def _validate_project(project_id: str) -> None:
        if not _PROJECT_RE.fullmatch(project_id):
            raise ValueError("invalid project_id")

    def _initialize(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS scheduled_run_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scheduled_run_events (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                project_id TEXT NOT NULL,
                schedule_id TEXT NOT NULL,
                definition_json TEXT NOT NULL,
                event_type TEXT NOT NULL,
                session_id TEXT,
                summary_json TEXT,
                reason TEXT,
                supersedes_event_id TEXT UNIQUE,
                created_at TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                FOREIGN KEY(supersedes_event_id)
                    REFERENCES scheduled_run_events(event_id)
                    ON DELETE RESTRICT
            );

            CREATE INDEX IF NOT EXISTS idx_scheduled_run_project_schedule
                ON scheduled_run_events(project_id, schedule_id, row_id DESC);

            CREATE TRIGGER IF NOT EXISTS scheduled_run_no_update
            BEFORE UPDATE ON scheduled_run_events
            BEGIN
                SELECT RAISE(ABORT, 'append-only scheduled run: UPDATE prohibited');
            END;

            CREATE TRIGGER IF NOT EXISTS scheduled_run_no_delete
            BEFORE DELETE ON scheduled_run_events
            BEGIN
                SELECT RAISE(ABORT, 'append-only scheduled run: DELETE prohibited');
            END;
            """
        )
        row = self._conn.execute(
            "SELECT value FROM scheduled_run_meta WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO scheduled_run_meta(key, value) VALUES('schema_version', ?)",
                (SCHEDULE_SCHEMA_VERSION,),
            )
            self._conn.commit()
        elif row["value"] != SCHEDULE_SCHEMA_VERSION:
            raise ScheduledRunIntegrityError("unsupported scheduled-run schema version")


class _NeverTool:
    def __call__(self, action: str) -> ToolOutcome:
        raise ScheduledRunPolicyError(
            f"policy-blocked unattended action unexpectedly attempted tool call: {action}"
        )


class ScheduledRunExecutor:
    """Execute at most one due one-shot schedule through the deterministic Supervisor."""

    def __init__(
        self,
        *,
        supervisor: Supervisor,
        store: PersistedScheduledRunStore,
        tools: Mapping[str, ToolCallable],
        clock: Callable[[], datetime] = _default_clock,
    ) -> None:
        self._supervisor = supervisor
        self._store = store
        self._tools = MappingProxyType(dict(tools))
        self._clock = clock

    def run_next_due(self) -> ScheduledRunSnapshot | None:
        project_id = str(self._supervisor.state["project_id"])

        # A previous process may have died while a schedule/session or queue job
        # was RUNNING. Never silently resume uncertain external side effects.
        self._store.recover_interrupted_sessions(project_id=project_id)

        started = self._store.start_next_due(project_id=project_id)
        if started is None:
            return None

        recovered_jobs = self._supervisor.recover_interrupted_persisted_jobs(
            reason="scheduled session startup recovered interrupted RUNNING job"
        )
        recovered_ids = tuple(item.job_id for item in recovered_jobs)
        touched: list[str] = list(recovered_ids)
        evidence_refs: set[str] = set()
        claims = 0
        started_at = _parse_utc(started.created_at)
        stop_reason = "NO_ELIGIBLE_PREAUTHORIZED_JOBS"

        while True:
            elapsed = (
                self._clock().astimezone(timezone.utc) - started_at
            ).total_seconds()
            if claims >= started.definition.max_jobs:
                stop_reason = "MAX_JOBS_REACHED"
                break
            if elapsed >= started.definition.max_session_seconds:
                stop_reason = "MAX_SESSION_SECONDS_REACHED"
                break

            candidate = self._select_candidate(started.definition)
            if candidate is None:
                stop_reason = "NO_ELIGIBLE_PREAUTHORIZED_JOBS"
                break

            job = candidate.job_dict()
            claimed = self._supervisor.claim_persisted_job(
                job_id=candidate.job_id,
                expected_event_id=candidate.event_id,
            )
            claims += 1
            if candidate.job_id not in touched:
                touched.append(candidate.job_id)

            actions = tuple(job["requested_actions"])
            if len(actions) != 1:
                self._supervisor.block_running_persisted_job(
                    job_id=claimed.job_id,
                    blocker="unattended run requires exactly one requested action",
                )
                continue

            action = actions[0]
            decision = self._supervisor.inspect_job_action(job=job, action=action)

            if decision.decision is Decision.ALLOW:
                tool = self._tools.get(action)
                if action not in started.definition.allowed_actions:
                    # Should be unreachable because _select_candidate skips it,
                    # but fail closed under any inconsistent state.
                    self._supervisor.block_running_persisted_job(
                        job_id=claimed.job_id,
                        blocker=f"action is not pre-authorized by schedule: {action}",
                    )
                    continue
                if tool is None:
                    self._supervisor.block_running_persisted_job(
                        job_id=claimed.job_id,
                        blocker=f"pre-authorized unattended tool is unavailable: {action}",
                    )
                    continue
                result = self._supervisor.execute(
                    job=claimed.job_dict(),
                    action=action,
                    tool=self._safe_tool(tool),
                )
            else:
                # Policy DENY / NEEDS_HUMAN_APPROVAL must be persisted through
                # Supervisor.execute, which guarantees the tool is not called.
                result = self._supervisor.execute(
                    job=claimed.job_dict(),
                    action=action,
                    tool=_NeverTool(),
                )

            self._supervisor.persist_persisted_job_result(
                job_id=claimed.job_id,
                result_job=result.job,
            )
            for event in result.audit_events:
                for ref in event.get("evidence_refs", []):
                    evidence_refs.add(ref)

        summary = self._build_summary(
            started=started,
            touched_job_ids=tuple(touched),
            recovered_job_ids=recovered_ids,
            claims=claims,
            evidence_refs=tuple(sorted(evidence_refs)),
            stop_reason=stop_reason,
        )
        return self._store.complete(
            project_id=project_id,
            schedule_id=started.schedule_id,
            summary=summary,
        )

    def _select_candidate(
        self,
        definition: ScheduledRunDefinition,
    ):
        for snapshot in self._supervisor.persisted_jobs():
            if snapshot.status != "QUEUED":
                continue
            job = snapshot.job_dict()
            actions = tuple(job["requested_actions"])
            if len(actions) != 1:
                return snapshot
            action = actions[0]
            decision = self._supervisor.inspect_job_action(job=job, action=action)
            if decision.decision is not Decision.ALLOW:
                return snapshot
            if action in definition.allowed_actions:
                return snapshot
            # Autonomous but not pre-authorized by this schedule: leave QUEUED.
        return None

    def _build_summary(
        self,
        *,
        started: ScheduledRunSnapshot,
        touched_job_ids: tuple[str, ...],
        recovered_job_ids: tuple[str, ...],
        claims: int,
        evidence_refs: tuple[str, ...],
        stop_reason: str,
    ) -> ScheduledRunSummary:
        counts = {state: 0 for state in _SUMMARY_STATES}
        for job_id in touched_job_ids:
            state = self._supervisor.persisted_job(job_id=job_id).status
            if state in counts:
                counts[state] += 1
        return ScheduledRunSummary(
            session_id=started.session_id or "",
            schedule_id=started.schedule_id,
            project_id=started.project_id,
            started_at=started.created_at,
            completed_at=_utc_iso(self._clock()),
            stop_reason=stop_reason,
            claims=claims,
            touched_job_ids=touched_job_ids,
            recovered_interrupted_job_ids=recovered_job_ids,
            counts=counts,
            evidence_refs=evidence_refs,
        )

    @staticmethod
    def _safe_tool(tool: ToolCallable) -> ToolCallable:
        def call(action: str) -> ToolOutcome:
            try:
                result = tool(action)
            except Exception as exc:
                return ToolOutcome(
                    False,
                    f"unattended tool raised {type(exc).__name__}",
                )
            if not isinstance(result, ToolOutcome):
                return ToolOutcome(False, "unattended tool returned invalid outcome")
            return result

        return call
