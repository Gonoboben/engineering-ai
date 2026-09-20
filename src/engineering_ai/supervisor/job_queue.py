"""Persistent append-only Supervisor job queue for Gate 019."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping
from uuid import uuid4

from engineering_ai.validation import validate_instance


QUEUE_SCHEMA_VERSION = "1.0"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,95}$")
_PROJECT_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
_TERMINAL_STATES = {"PASS", "FAIL", "CANCELLED"}


class JobQueueError(RuntimeError):
    """Base error for persisted queue operations."""


class JobQueueConflictError(JobQueueError):
    pass


class JobQueueIntegrityError(JobQueueError):
    pass


class JobQueuePolicyError(JobQueueError):
    pass


class QueueEventType(str, Enum):
    ENQUEUED = "ENQUEUED"
    RUN_STARTED = "RUN_STARTED"
    EXECUTION_RESULT = "EXECUTION_RESULT"
    INTERRUPTED_RECOVERY = "INTERRUPTED_RECOVERY"
    TIMEOUT_RECOVERY = "TIMEOUT_RECOVERY"


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
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


def _default_event_id() -> str:
    return f"qevt-{uuid4().hex}"


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("queue clock must return timezone-aware datetime")
    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _immutable_job_payload(job: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "schema_version",
        "job_id",
        "project_id",
        "objective",
        "scope",
        "out_of_scope",
        "requested_actions",
        "required_validators",
        "retry_limit",
    )
    payload = {key: deepcopy(_thaw(job[key])) for key in required}
    payload["gate_id"] = deepcopy(_thaw(job.get("gate_id")))
    return payload


@dataclass(frozen=True)
class JobQueueSnapshot:
    queue_sequence: int
    event_id: str
    project_id: str
    job_id: str
    event_type: QueueEventType
    job: Mapping[str, Any]
    timeout_seconds: int
    run_started_at: str | None
    run_deadline_at: str | None
    reason: str | None
    supersedes_event_id: str | None
    created_at: str
    content_sha256: str

    def __post_init__(self) -> None:
        if self.queue_sequence <= 0:
            raise ValueError("queue_sequence must be positive")
        object.__setattr__(self, "job", _freeze(dict(self.job)))

    @property
    def status(self) -> str:
        return str(self.job["status"])

    @property
    def attempts(self) -> int:
        return int(self.job["attempts"])

    def job_dict(self) -> dict[str, Any]:
        return deepcopy(_thaw(self.job))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": QUEUE_SCHEMA_VERSION,
            "queue_sequence": self.queue_sequence,
            **_event_hash_payload(self),
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class JobQueueIntegrityReport:
    events_checked: int
    jobs_checked: int
    ok: bool


def _event_hash_payload(snapshot: JobQueueSnapshot) -> dict[str, Any]:
    return {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "event_id": snapshot.event_id,
        "project_id": snapshot.project_id,
        "job_id": snapshot.job_id,
        "event_type": snapshot.event_type.value,
        "job": _thaw(snapshot.job),
        "timeout_seconds": snapshot.timeout_seconds,
        "run_started_at": snapshot.run_started_at,
        "run_deadline_at": snapshot.run_deadline_at,
        "reason": snapshot.reason,
        "supersedes_event_id": snapshot.supersedes_event_id,
        "created_at": snapshot.created_at,
    }


class PersistedJobQueue:
    """Append-only local queue state.

    The queue stores control state only. It never executes tools, evaluates policy,
    grants approval, schedules work, or promotes engineering evidence.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        clock: Callable[[], datetime] = _default_clock,
        event_id_factory: Callable[[], str] = _default_event_id,
        max_jobs: int = 10_000,
    ) -> None:
        if max_jobs <= 0:
            raise ValueError("max_jobs must be positive")
        raw = Path(database_path)
        if raw.exists() and raw.is_symlink():
            raise JobQueuePolicyError("job queue database path must not be a symlink")
        raw.parent.mkdir(parents=True, exist_ok=True)
        self._path = raw.resolve(strict=False)
        self._clock = clock
        self._event_id_factory = event_id_factory
        self._max_jobs = max_jobs
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._initialize()

    @property
    def database_path(self) -> Path:
        return self._path

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "PersistedJobQueue":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def enqueue(
        self,
        job: Mapping[str, Any],
        *,
        timeout_seconds: int = 3600,
    ) -> JobQueueSnapshot:
        payload = deepcopy(_thaw(job))
        validate_instance("job.schema.json", payload)
        self._validate_timeout(timeout_seconds)
        if payload["status"] != "QUEUED":
            raise JobQueuePolicyError("new persisted job must start QUEUED")
        if payload.get("blocker") is not None:
            raise JobQueuePolicyError("new persisted job must not start with blocker")

        project_id = str(payload["project_id"])
        job_id = str(payload["job_id"])
        self._validate_project(project_id)

        existing = self._conn.execute(
            """
            SELECT 1 FROM job_queue_events
            WHERE project_id = ? AND job_id = ?
            LIMIT 1
            """,
            (project_id, job_id),
        ).fetchone()
        if existing is not None:
            raise JobQueueConflictError(
                f"persisted job already exists: {project_id}/{job_id}"
            )

        return self._append_event(
            project_id=project_id,
            job_id=job_id,
            event_type=QueueEventType.ENQUEUED,
            job=payload,
            timeout_seconds=timeout_seconds,
            run_started_at=None,
            run_deadline_at=None,
            reason=None,
            expected_latest_event_id=None,
        )

    def get(
        self,
        *,
        project_id: str,
        job_id: str,
    ) -> JobQueueSnapshot:
        self._validate_project(project_id)
        history = self.history(project_id=project_id, job_id=job_id)
        if not history:
            raise KeyError(job_id)
        return history[-1]

    def history(
        self,
        *,
        project_id: str,
        job_id: str,
    ) -> tuple[JobQueueSnapshot, ...]:
        self._validate_project(project_id)
        rows = self._conn.execute(
            """
            SELECT * FROM job_queue_events
            WHERE project_id = ? AND job_id = ?
            ORDER BY row_id ASC
            """,
            (project_id, job_id),
        ).fetchall()
        snapshots = tuple(self._row_to_snapshot(row) for row in rows)
        self._validate_history_chain(snapshots)
        return snapshots

    def list_current(
        self,
        *,
        project_id: str,
    ) -> tuple[JobQueueSnapshot, ...]:
        self._validate_project(project_id)
        rows = self._conn.execute(
            """
            SELECT e.*
            FROM job_queue_events AS e
            JOIN (
                SELECT job_id, MAX(row_id) AS max_row_id
                FROM job_queue_events
                WHERE project_id = ?
                GROUP BY job_id
            ) AS latest
              ON e.row_id = latest.max_row_id
            WHERE e.project_id = ?
            ORDER BY e.row_id ASC
            LIMIT ?
            """,
            (project_id, project_id, self._max_jobs + 1),
        ).fetchall()
        if len(rows) > self._max_jobs:
            raise JobQueuePolicyError("persisted job count exceeded max_jobs")
        return tuple(self._row_to_snapshot(row) for row in rows)

    def claim_next(
        self,
        *,
        project_id: str,
    ) -> JobQueueSnapshot | None:
        """Claim the oldest currently QUEUED job.

        Retry results re-enter at the tail because their latest QUEUED event has a
        newer queue sequence than jobs that have not yet run.
        """

        for snapshot in self.list_current(project_id=project_id):
            if snapshot.status == "QUEUED":
                return self.begin_run(
                    project_id=project_id,
                    job_id=snapshot.job_id,
                    expected_event_id=snapshot.event_id,
                )
        return None

    def begin_run(
        self,
        *,
        project_id: str,
        job_id: str,
        expected_event_id: str | None = None,
        allow_waiting_for_approval: bool = False,
    ) -> JobQueueSnapshot:
        latest = self.get(project_id=project_id, job_id=job_id)
        if expected_event_id is not None and latest.event_id != expected_event_id:
            raise JobQueueConflictError("queue head changed before run claim")

        allowed = {"QUEUED"}
        if allow_waiting_for_approval:
            allowed.add("WAITING_FOR_APPROVAL")
        if latest.status not in allowed:
            raise JobQueuePolicyError(
                f"job cannot begin run from state {latest.status}"
            )

        now = self._clock()
        start = _utc_iso(now)
        deadline = _utc_iso(now + timedelta(seconds=latest.timeout_seconds))
        job = latest.job_dict()
        job["status"] = "RUNNING"
        job["blocker"] = None
        return self._append_event(
            project_id=project_id,
            job_id=job_id,
            event_type=QueueEventType.RUN_STARTED,
            job=job,
            timeout_seconds=latest.timeout_seconds,
            run_started_at=start,
            run_deadline_at=deadline,
            reason=None,
            expected_latest_event_id=latest.event_id,
        )

    def persist_execution_result(
        self,
        *,
        project_id: str,
        job_id: str,
        result_job: Mapping[str, Any],
    ) -> JobQueueSnapshot:
        latest = self.get(project_id=project_id, job_id=job_id)
        if latest.status != "RUNNING":
            raise JobQueuePolicyError(
                f"execution result requires RUNNING queue state, got {latest.status}"
            )

        result = deepcopy(_thaw(result_job))
        validate_instance("job.schema.json", result)
        if str(result["project_id"]) != project_id or str(result["job_id"]) != job_id:
            raise JobQueuePolicyError("execution result project/job identity mismatch")
        if _immutable_job_payload(result) != _immutable_job_payload(latest.job):
            raise JobQueuePolicyError(
                "execution result cannot mutate persisted job scope or permissions"
            )
        self._validate_attempt_transition(latest.job, result)
        if result["status"] == "RUNNING":
            raise JobQueuePolicyError("execution result cannot remain RUNNING")

        now = self._clock()
        if latest.run_deadline_at is None:
            raise JobQueueIntegrityError("RUNNING queue event lacks deadline")
        if now >= _parse_utc(latest.run_deadline_at):
            return self._append_recovery(
                latest=latest,
                event_type=QueueEventType.TIMEOUT_RECOVERY,
                reason="run deadline expired before result persistence",
            )

        return self._append_event(
            project_id=project_id,
            job_id=job_id,
            event_type=QueueEventType.EXECUTION_RESULT,
            job=result,
            timeout_seconds=latest.timeout_seconds,
            run_started_at=latest.run_started_at,
            run_deadline_at=latest.run_deadline_at,
            reason=None,
            expected_latest_event_id=latest.event_id,
        )

    def recover_interrupted_runs(
        self,
        *,
        project_id: str,
        reason: str = "process restart interrupted RUNNING job",
    ) -> tuple[JobQueueSnapshot, ...]:
        if not reason.strip():
            raise ValueError("recovery reason must be non-empty")
        recovered: list[JobQueueSnapshot] = []
        for snapshot in self.list_current(project_id=project_id):
            if snapshot.status != "RUNNING":
                continue
            recovered.append(
                self._append_recovery(
                    latest=snapshot,
                    event_type=QueueEventType.INTERRUPTED_RECOVERY,
                    reason=reason.strip(),
                )
            )
        return tuple(recovered)

    def recover_expired_runs(
        self,
        *,
        project_id: str,
    ) -> tuple[JobQueueSnapshot, ...]:
        now = self._clock()
        recovered: list[JobQueueSnapshot] = []
        for snapshot in self.list_current(project_id=project_id):
            if snapshot.status != "RUNNING":
                continue
            if snapshot.run_deadline_at is None:
                raise JobQueueIntegrityError("RUNNING queue event lacks deadline")
            if now < _parse_utc(snapshot.run_deadline_at):
                continue
            recovered.append(
                self._append_recovery(
                    latest=snapshot,
                    event_type=QueueEventType.TIMEOUT_RECOVERY,
                    reason="persisted run deadline expired",
                )
            )
        return tuple(recovered)

    def verify_integrity(
        self,
        *,
        project_id: str | None = None,
    ) -> JobQueueIntegrityReport:
        if project_id is None:
            rows = self._conn.execute(
                "SELECT * FROM job_queue_events ORDER BY row_id ASC"
            ).fetchall()
        else:
            self._validate_project(project_id)
            rows = self._conn.execute(
                """
                SELECT * FROM job_queue_events
                WHERE project_id = ?
                ORDER BY row_id ASC
                """,
                (project_id,),
            ).fetchall()

        job_ids: set[tuple[str, str]] = set()
        grouped: dict[tuple[str, str], list[JobQueueSnapshot]] = {}
        for row in rows:
            snapshot = self._row_to_snapshot(row)
            key = (snapshot.project_id, snapshot.job_id)
            job_ids.add(key)
            grouped.setdefault(key, []).append(snapshot)
        for snapshots in grouped.values():
            self._validate_history_chain(tuple(snapshots))
        return JobQueueIntegrityReport(
            events_checked=len(rows),
            jobs_checked=len(job_ids),
            ok=True,
        )

    def _append_recovery(
        self,
        *,
        latest: JobQueueSnapshot,
        event_type: QueueEventType,
        reason: str,
    ) -> JobQueueSnapshot:
        if event_type not in {
            QueueEventType.INTERRUPTED_RECOVERY,
            QueueEventType.TIMEOUT_RECOVERY,
        }:
            raise ValueError("invalid recovery event type")
        job = latest.job_dict()
        job["status"] = "BLOCKED"
        job["blocker"] = f"queue recovery required: {reason}"
        return self._append_event(
            project_id=latest.project_id,
            job_id=latest.job_id,
            event_type=event_type,
            job=job,
            timeout_seconds=latest.timeout_seconds,
            run_started_at=latest.run_started_at,
            run_deadline_at=latest.run_deadline_at,
            reason=reason,
            expected_latest_event_id=latest.event_id,
        )

    def _append_event(
        self,
        *,
        project_id: str,
        job_id: str,
        event_type: QueueEventType,
        job: Mapping[str, Any],
        timeout_seconds: int,
        run_started_at: str | None,
        run_deadline_at: str | None,
        reason: str | None,
        expected_latest_event_id: str | None,
    ) -> JobQueueSnapshot:
        self._validate_project(project_id)
        self._validate_timeout(timeout_seconds)
        payload = deepcopy(_thaw(job))
        validate_instance("job.schema.json", payload)
        if str(payload["project_id"]) != project_id or str(payload["job_id"]) != job_id:
            raise JobQueuePolicyError("queue event project/job identity mismatch")

        created_at = _utc_iso(self._clock())
        event_id = self._event_id_factory()
        if not _ID_RE.fullmatch(event_id):
            raise ValueError(f"invalid queue event id: {event_id!r}")

        self._conn.execute("BEGIN IMMEDIATE")
        try:
            latest_row = self._latest_row(project_id=project_id, job_id=job_id)
            latest = self._row_to_snapshot(latest_row) if latest_row is not None else None

            if expected_latest_event_id is None:
                if latest is not None:
                    raise JobQueueConflictError(
                        "initial queue event requires no existing job history"
                    )
                supersedes = None
            else:
                if latest is None:
                    raise JobQueueConflictError("queue history disappeared")
                if latest.event_id != expected_latest_event_id:
                    raise JobQueueConflictError(
                        "expected queue event is not the latest exact event"
                    )
                supersedes = latest.event_id

            provisional = JobQueueSnapshot(
                queue_sequence=1,
                event_id=event_id,
                project_id=project_id,
                job_id=job_id,
                event_type=event_type,
                job=payload,
                timeout_seconds=timeout_seconds,
                run_started_at=run_started_at,
                run_deadline_at=run_deadline_at,
                reason=reason,
                supersedes_event_id=supersedes,
                created_at=created_at,
                content_sha256="",
            )
            content_sha256 = _sha256_canonical(_event_hash_payload(provisional))
            cursor = self._conn.execute(
                """
                INSERT INTO job_queue_events (
                    event_id,
                    project_id,
                    job_id,
                    event_type,
                    job_json,
                    timeout_seconds,
                    run_started_at,
                    run_deadline_at,
                    reason,
                    supersedes_event_id,
                    created_at,
                    content_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    project_id,
                    job_id,
                    event_type.value,
                    _canonical_json(payload),
                    timeout_seconds,
                    run_started_at,
                    run_deadline_at,
                    reason,
                    supersedes,
                    created_at,
                    content_sha256,
                ),
            )
            row_id = int(cursor.lastrowid)
            self._conn.commit()
            return JobQueueSnapshot(
                **{
                    **provisional.__dict__,
                    "queue_sequence": row_id,
                    "content_sha256": content_sha256,
                }
            )
        except Exception:
            self._conn.rollback()
            raise

    def _latest_row(
        self,
        *,
        project_id: str,
        job_id: str,
    ) -> sqlite3.Row | None:
        return self._conn.execute(
            """
            SELECT * FROM job_queue_events
            WHERE project_id = ? AND job_id = ?
            ORDER BY row_id DESC
            LIMIT 1
            """,
            (project_id, job_id),
        ).fetchone()

    def _row_to_snapshot(self, row: sqlite3.Row) -> JobQueueSnapshot:
        try:
            job = json.loads(row["job_json"])
            validate_instance("job.schema.json", job)
            snapshot = JobQueueSnapshot(
                queue_sequence=int(row["row_id"]),
                event_id=row["event_id"],
                project_id=row["project_id"],
                job_id=row["job_id"],
                event_type=QueueEventType(row["event_type"]),
                job=job,
                timeout_seconds=int(row["timeout_seconds"]),
                run_started_at=row["run_started_at"],
                run_deadline_at=row["run_deadline_at"],
                reason=row["reason"],
                supersedes_event_id=row["supersedes_event_id"],
                created_at=row["created_at"],
                content_sha256=row["content_sha256"],
            )
        except Exception as exc:
            if isinstance(exc, JobQueueError):
                raise
            raise JobQueueIntegrityError("invalid persisted queue event") from exc

        if snapshot.project_id != snapshot.job["project_id"]:
            raise JobQueueIntegrityError("queue project_id does not match job payload")
        if snapshot.job_id != snapshot.job["job_id"]:
            raise JobQueueIntegrityError("queue job_id does not match job payload")
        self._validate_event_semantics(snapshot)

        expected = _sha256_canonical(_event_hash_payload(snapshot))
        if not hmac.compare_digest(expected, snapshot.content_sha256):
            raise JobQueueIntegrityError(
                f"job queue hash mismatch for event {snapshot.event_id}"
            )
        return snapshot

    @staticmethod
    def _validate_event_semantics(snapshot: JobQueueSnapshot) -> None:
        event = snapshot.event_type
        status = snapshot.status
        try:
            _parse_utc(snapshot.created_at)
            if snapshot.run_started_at is not None:
                start = _parse_utc(snapshot.run_started_at)
            else:
                start = None
            if snapshot.run_deadline_at is not None:
                deadline = _parse_utc(snapshot.run_deadline_at)
            else:
                deadline = None
        except (ValueError, TypeError) as exc:
            raise JobQueueIntegrityError("invalid queue timestamp") from exc
        if start is not None and deadline is not None and deadline <= start:
            raise JobQueueIntegrityError("run deadline must be after run start")
        if event is QueueEventType.ENQUEUED:
            if snapshot.supersedes_event_id is not None or status != "QUEUED":
                raise JobQueueIntegrityError("invalid ENQUEUED event semantics")
            if snapshot.run_started_at is not None or snapshot.run_deadline_at is not None:
                raise JobQueueIntegrityError("ENQUEUED cannot have run timestamps")
        elif event is QueueEventType.RUN_STARTED:
            if snapshot.supersedes_event_id is None or status != "RUNNING":
                raise JobQueueIntegrityError("invalid RUN_STARTED event semantics")
            if snapshot.run_started_at is None or snapshot.run_deadline_at is None:
                raise JobQueueIntegrityError("RUN_STARTED requires run timestamps")
        elif event is QueueEventType.EXECUTION_RESULT:
            if snapshot.supersedes_event_id is None or status == "RUNNING":
                raise JobQueueIntegrityError("invalid EXECUTION_RESULT semantics")
        elif event in {
            QueueEventType.INTERRUPTED_RECOVERY,
            QueueEventType.TIMEOUT_RECOVERY,
        }:
            if snapshot.supersedes_event_id is None or status != "BLOCKED":
                raise JobQueueIntegrityError("invalid recovery event semantics")
            if not snapshot.reason:
                raise JobQueueIntegrityError("recovery event requires reason")

    @staticmethod
    def _validate_history_chain(
        snapshots: tuple[JobQueueSnapshot, ...],
    ) -> None:
        if not snapshots:
            return
        first = snapshots[0]
        if first.event_type is not QueueEventType.ENQUEUED:
            raise JobQueueIntegrityError("job queue history must start with ENQUEUED")
        immutable = _immutable_job_payload(first.job)
        previous = first
        for snapshot in snapshots[1:]:
            if snapshot.project_id != first.project_id or snapshot.job_id != first.job_id:
                raise JobQueueIntegrityError("queue history crosses project/job identity")
            if snapshot.supersedes_event_id != previous.event_id:
                raise JobQueueIntegrityError("queue history supersession chain is broken")
            if _immutable_job_payload(snapshot.job) != immutable:
                raise JobQueueIntegrityError("queue history mutated immutable job definition")
            previous = snapshot

    @staticmethod
    def _validate_attempt_transition(
        current_job: Mapping[str, Any],
        result_job: Mapping[str, Any],
    ) -> None:
        current = int(current_job["attempts"])
        result = int(result_job["attempts"])
        status = str(result_job["status"])
        if status == "QUEUED":
            if result != current + 1:
                raise JobQueuePolicyError(
                    "retry result must increment attempts exactly once"
                )
        elif result != current:
            raise JobQueuePolicyError(
                "non-retry execution result cannot change attempts"
            )

    @staticmethod
    def _validate_timeout(timeout_seconds: int) -> None:
        if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool):
            raise ValueError("timeout_seconds must be an integer")
        if not 1 <= timeout_seconds <= 86_400:
            raise ValueError("timeout_seconds must be between 1 and 86400")

    @staticmethod
    def _validate_project(project_id: str) -> None:
        if not _PROJECT_RE.fullmatch(project_id):
            raise ValueError(f"invalid project_id: {project_id!r}")

    def _initialize(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS job_queue_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS job_queue_events (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                project_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                job_json TEXT NOT NULL,
                timeout_seconds INTEGER NOT NULL CHECK (timeout_seconds BETWEEN 1 AND 86400),
                run_started_at TEXT,
                run_deadline_at TEXT,
                reason TEXT,
                supersedes_event_id TEXT UNIQUE,
                created_at TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                FOREIGN KEY(supersedes_event_id)
                    REFERENCES job_queue_events(event_id)
                    ON DELETE RESTRICT
            );

            CREATE INDEX IF NOT EXISTS idx_job_queue_project_job
                ON job_queue_events(project_id, job_id, row_id DESC);

            CREATE TRIGGER IF NOT EXISTS job_queue_events_no_update
            BEFORE UPDATE ON job_queue_events
            BEGIN
                SELECT RAISE(ABORT, 'append-only job queue: UPDATE prohibited');
            END;

            CREATE TRIGGER IF NOT EXISTS job_queue_events_no_delete
            BEFORE DELETE ON job_queue_events
            BEGIN
                SELECT RAISE(ABORT, 'append-only job queue: DELETE prohibited');
            END;
            """
        )
        row = self._conn.execute(
            "SELECT value FROM job_queue_meta WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO job_queue_meta(key, value) VALUES('schema_version', ?)",
                (QUEUE_SCHEMA_VERSION,),
            )
            self._conn.commit()
        elif row["value"] != QUEUE_SCHEMA_VERSION:
            raise JobQueueIntegrityError(
                f"unsupported job queue schema version: {row['value']!r}"
            )
