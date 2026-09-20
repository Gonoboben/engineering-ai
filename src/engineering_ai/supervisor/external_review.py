"""Policy-controlled provider-neutral external advisory review bridge."""

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
from typing import Any, Callable, Mapping, Protocol
from uuid import uuid4

from engineering_ai.supervisor.core import Supervisor
from engineering_ai.supervisor.policy import Decision, PolicyDecision


EXTERNAL_REVIEW_SCHEMA_VERSION = "1.0"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,95}$")
_PROJECT_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
_MAX_HARD_CONTEXT_CHARS = 200_000
_MAX_HARD_OUTPUT_CHARS = 50_000
_MAX_PURPOSE_CHARS = 4_000
_MAX_SOURCE_REF_CHARS = 2_048
_MAX_KIND_CHARS = 128
_MAX_TIMEOUT_SECONDS = 600


class ExternalReviewError(RuntimeError):
    """Base error for controlled external review operations."""


class ExternalReviewIntegrityError(ExternalReviewError):
    pass


class ExternalReviewPolicyError(ExternalReviewError):
    pass


class ExternalReviewProtocolError(ExternalReviewError):
    pass


class ExternalConsultationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NEEDS_HUMAN_APPROVAL = "NEEDS_HUMAN_APPROVAL"


class ExternalConsultationEventType(str, Enum):
    REQUEST_RECORDED = "REQUEST_RECORDED"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    PROVIDER_FAILED = "PROVIDER_FAILED"
    RESPONSE_ACCEPTED = "RESPONSE_ACCEPTED"


class ExternalReviewAuthority(str, Enum):
    ADVISORY = "ADVISORY"


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _default_event_id() -> str:
    return f"xevt-{uuid4().hex}"


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("external review clock must return timezone-aware datetime")
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


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExternalContextItem:
    """One explicit outbound context item.

    The content is sent only to the supplied provider call. The persistent
    consultation ledger records source/hash/size metadata, not the content.
    """

    context_id: str
    project_id: str
    source_ref: str
    kind: str
    content: str
    contains_secrets: bool = False

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.context_id):
            raise ValueError("invalid context_id")
        if not _PROJECT_RE.fullmatch(self.project_id):
            raise ValueError("invalid context project_id")
        if not self.source_ref.strip():
            raise ValueError("source_ref must be non-empty")
        if len(self.source_ref) > _MAX_SOURCE_REF_CHARS:
            raise ValueError("source_ref exceeds hard character limit")
        if not self.kind.strip():
            raise ValueError("kind must be non-empty")
        if len(self.kind) > _MAX_KIND_CHARS:
            raise ValueError("kind exceeds hard character limit")
        if not self.content:
            raise ValueError("context content must be non-empty")
        if self.contains_secrets:
            raise ExternalReviewPolicyError(
                "context explicitly marked as containing secrets cannot be disclosed"
            )

    @property
    def content_sha256(self) -> str:
        return _sha256_text(self.content)

    @property
    def char_count(self) -> int:
        return len(self.content)

    def manifest(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "project_id": self.project_id,
            "source_ref": self.source_ref,
            "kind": self.kind,
            "char_count": self.char_count,
            "content_sha256": self.content_sha256,
            "contains_secrets": False,
        }


@dataclass(frozen=True)
class ExternalConsultationRequest:
    consultation_id: str
    project_id: str
    gate_id: str | None
    job_id: str
    purpose: str
    provider_name: str
    model: str
    context_items: tuple[ExternalContextItem, ...]
    max_context_chars: int = 50_000
    max_output_chars: int = 8_000
    timeout_seconds: int = 120

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.consultation_id):
            raise ValueError("invalid consultation_id")
        if not _PROJECT_RE.fullmatch(self.project_id):
            raise ValueError("invalid project_id")
        if not _ID_RE.fullmatch(self.job_id):
            raise ValueError("invalid job_id")
        if not self.purpose.strip():
            raise ValueError("purpose must be non-empty")
        if len(self.purpose) > _MAX_PURPOSE_CHARS:
            raise ValueError("purpose exceeds hard character limit")
        if not self.provider_name.strip():
            raise ValueError("provider_name must be non-empty")
        if not self.model.strip():
            raise ValueError("model must be non-empty")
        if not self.context_items:
            raise ValueError("context_items must be non-empty")
        ids = [item.context_id for item in self.context_items]
        if len(set(ids)) != len(ids):
            raise ValueError("context_ids must be unique")
        for item in self.context_items:
            if item.project_id != self.project_id:
                raise ExternalReviewPolicyError(
                    "external context cannot mix project identities"
                )
        if not 1 <= self.max_context_chars <= _MAX_HARD_CONTEXT_CHARS:
            raise ValueError("max_context_chars out of bounds")
        if not 1 <= self.max_output_chars <= _MAX_HARD_OUTPUT_CHARS:
            raise ValueError("max_output_chars out of bounds")
        if not 1 <= self.timeout_seconds <= _MAX_TIMEOUT_SECONDS:
            raise ValueError("timeout_seconds out of bounds")
        if self.total_context_chars > self.max_context_chars:
            raise ExternalReviewPolicyError(
                "explicit outbound context exceeds request max_context_chars"
            )

    @property
    def total_context_chars(self) -> int:
        return sum(item.char_count for item in self.context_items)

    def manifest(self) -> dict[str, Any]:
        return {
            "consultation_id": self.consultation_id,
            "project_id": self.project_id,
            "gate_id": self.gate_id,
            "job_id": self.job_id,
            "purpose_sha256": _sha256_text(self.purpose),
            "purpose_char_count": len(self.purpose),
            "provider_name": self.provider_name,
            "model": self.model,
            "context_items": [item.manifest() for item in self.context_items],
            "total_context_chars": self.total_context_chars,
            "max_context_chars": self.max_context_chars,
            "max_output_chars": self.max_output_chars,
            "timeout_seconds": self.timeout_seconds,
            "contains_secrets": False,
        }


@dataclass(frozen=True)
class ExternalProviderRequest:
    consultation_id: str
    model: str
    purpose: str
    contexts: tuple[tuple[str, str, str, str], ...]
    max_output_chars: int

    @classmethod
    def from_consultation(
        cls,
        request: ExternalConsultationRequest,
    ) -> "ExternalProviderRequest":
        return cls(
            consultation_id=request.consultation_id,
            model=request.model,
            purpose=request.purpose,
            contexts=tuple(
                (item.context_id, item.source_ref, item.kind, item.content)
                for item in request.context_items
            ),
            max_output_chars=request.max_output_chars,
        )


@dataclass(frozen=True)
class ExternalProviderResponse:
    provider_name: str
    model: str
    content: str
    raw_metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.provider_name.strip():
            raise ValueError("provider_name must be non-empty")
        if not self.model.strip():
            raise ValueError("model must be non-empty")
        if not isinstance(self.content, str):
            raise TypeError("content must be str")
        object.__setattr__(
            self,
            "raw_metadata",
            MappingProxyType(dict(self.raw_metadata or {})),
        )


class ExternalReviewProvider(Protocol):
    @property
    def provider_name(self) -> str:
        ...

    def review(
        self,
        request: ExternalProviderRequest,
        *,
        timeout_seconds: int,
    ) -> ExternalProviderResponse:
        ...


@dataclass(frozen=True)
class ExternalAdvisoryReview:
    consultation_id: str
    provider_name: str
    model: str
    content: str
    request_manifest_sha256: str
    response_sha256: str
    output_char_count: int
    authority: ExternalReviewAuthority = ExternalReviewAuthority.ADVISORY
    evidence_eligible: bool = False
    physical_validation: str = "PHYSICAL_NOT_EXECUTED"

    def __post_init__(self) -> None:
        if self.authority is not ExternalReviewAuthority.ADVISORY:
            raise ValueError("external review authority must remain ADVISORY")
        if self.evidence_eligible:
            raise ValueError("external advisory review cannot be deterministic evidence")
        if self.physical_validation != "PHYSICAL_NOT_EXECUTED":
            raise ValueError("external review cannot infer physical validation")


@dataclass(frozen=True)
class ExternalConsultationOutcome:
    status: ExternalConsultationStatus
    decision: PolicyDecision
    review: ExternalAdvisoryReview | None
    provider_called: bool
    summary: str


@dataclass(frozen=True)
class ExternalConsultationSnapshot:
    sequence: int
    event_id: str
    project_id: str
    consultation_id: str
    event_type: ExternalConsultationEventType
    request_manifest: Mapping[str, Any]
    provider_name: str
    model: str
    approval_required: bool
    approval_obtained: bool
    approver: str | None
    response_sha256: str | None
    response_chars: int | None
    failure_reason: str | None
    supersedes_event_id: str | None
    created_at: str
    content_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_manifest",
            _freeze(dict(self.request_manifest)),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EXTERNAL_REVIEW_SCHEMA_VERSION,
            "sequence": self.sequence,
            **_snapshot_hash_payload(self),
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class ExternalConsultationIntegrityReport:
    events_checked: int
    consultations_checked: int
    ok: bool


def _snapshot_hash_payload(snapshot: ExternalConsultationSnapshot) -> dict[str, Any]:
    return {
        "schema_version": EXTERNAL_REVIEW_SCHEMA_VERSION,
        "event_id": snapshot.event_id,
        "project_id": snapshot.project_id,
        "consultation_id": snapshot.consultation_id,
        "event_type": snapshot.event_type.value,
        "request_manifest": _thaw(snapshot.request_manifest),
        "provider_name": snapshot.provider_name,
        "model": snapshot.model,
        "approval_required": snapshot.approval_required,
        "approval_obtained": snapshot.approval_obtained,
        "approver": snapshot.approver,
        "response_sha256": snapshot.response_sha256,
        "response_chars": snapshot.response_chars,
        "failure_reason": snapshot.failure_reason,
        "supersedes_event_id": snapshot.supersedes_event_id,
        "created_at": snapshot.created_at,
    }


class ExternalConsultationLedger:
    """Append-only local metadata ledger; never stores outbound context content."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        clock: Callable[[], datetime] = _default_clock,
        event_id_factory: Callable[[], str] = _default_event_id,
    ) -> None:
        raw = Path(database_path)
        if raw.exists() and raw.is_symlink():
            raise ExternalReviewPolicyError(
                "external consultation database path must not be a symlink"
            )
        raw.parent.mkdir(parents=True, exist_ok=True)
        self._path = raw.resolve(strict=False)
        self._clock = clock
        self._event_id_factory = event_id_factory
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._initialize()

    @property
    def database_path(self) -> Path:
        return self._path

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "ExternalConsultationLedger":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def record_request(
        self,
        request: ExternalConsultationRequest,
        decision: PolicyDecision,
    ) -> ExternalConsultationSnapshot:
        if self._latest_row(request.project_id, request.consultation_id) is not None:
            raise ExternalReviewPolicyError("consultation_id already exists")
        return self._append(
            request=request,
            decision=decision,
            event_type=ExternalConsultationEventType.REQUEST_RECORDED,
            response_sha256=None,
            response_chars=None,
            failure_reason=None,
            expected_latest_event_id=None,
        )

    def record_terminal(
        self,
        *,
        request: ExternalConsultationRequest,
        decision: PolicyDecision,
        event_type: ExternalConsultationEventType,
        response_sha256: str | None = None,
        response_chars: int | None = None,
        failure_reason: str | None = None,
    ) -> ExternalConsultationSnapshot:
        if event_type not in {
            ExternalConsultationEventType.POLICY_BLOCKED,
            ExternalConsultationEventType.PROVIDER_FAILED,
            ExternalConsultationEventType.RESPONSE_ACCEPTED,
        }:
            raise ValueError("invalid terminal consultation event")
        latest = self.get(
            project_id=request.project_id,
            consultation_id=request.consultation_id,
        )
        if latest.event_type is not ExternalConsultationEventType.REQUEST_RECORDED:
            raise ExternalReviewPolicyError("consultation is already terminal")
        return self._append(
            request=request,
            decision=decision,
            event_type=event_type,
            response_sha256=response_sha256,
            response_chars=response_chars,
            failure_reason=failure_reason,
            expected_latest_event_id=latest.event_id,
        )

    def history(
        self,
        *,
        project_id: str,
        consultation_id: str,
    ) -> tuple[ExternalConsultationSnapshot, ...]:
        self._validate_project(project_id)
        rows = self._conn.execute(
            """
            SELECT * FROM external_consultation_events
            WHERE project_id = ? AND consultation_id = ?
            ORDER BY row_id ASC
            """,
            (project_id, consultation_id),
        ).fetchall()
        snapshots = tuple(self._row_to_snapshot(row) for row in rows)
        self._validate_history(snapshots)
        return snapshots

    def get(
        self,
        *,
        project_id: str,
        consultation_id: str,
    ) -> ExternalConsultationSnapshot:
        history = self.history(
            project_id=project_id,
            consultation_id=consultation_id,
        )
        if not history:
            raise KeyError(consultation_id)
        return history[-1]

    def verify_integrity(
        self,
        *,
        project_id: str | None = None,
    ) -> ExternalConsultationIntegrityReport:
        if project_id is None:
            rows = self._conn.execute(
                "SELECT * FROM external_consultation_events ORDER BY row_id ASC"
            ).fetchall()
        else:
            self._validate_project(project_id)
            rows = self._conn.execute(
                """
                SELECT * FROM external_consultation_events
                WHERE project_id = ?
                ORDER BY row_id ASC
                """,
                (project_id,),
            ).fetchall()
        grouped: dict[tuple[str, str], list[ExternalConsultationSnapshot]] = {}
        for row in rows:
            item = self._row_to_snapshot(row)
            grouped.setdefault(
                (item.project_id, item.consultation_id),
                [],
            ).append(item)
        for items in grouped.values():
            self._validate_history(tuple(items))
        return ExternalConsultationIntegrityReport(
            events_checked=len(rows),
            consultations_checked=len(grouped),
            ok=True,
        )

    def _append(
        self,
        *,
        request: ExternalConsultationRequest,
        decision: PolicyDecision,
        event_type: ExternalConsultationEventType,
        response_sha256: str | None,
        response_chars: int | None,
        failure_reason: str | None,
        expected_latest_event_id: str | None,
    ) -> ExternalConsultationSnapshot:
        event_id = self._event_id_factory()
        if not _ID_RE.fullmatch(event_id):
            raise ValueError("invalid external consultation event_id")
        created_at = _utc_iso(self._clock())
        manifest = request.manifest()

        self._conn.execute("BEGIN IMMEDIATE")
        try:
            latest_row = self._latest_row(
                request.project_id,
                request.consultation_id,
            )
            latest = self._row_to_snapshot(latest_row) if latest_row else None
            if expected_latest_event_id is None:
                if latest is not None:
                    raise ExternalReviewPolicyError(
                        "initial external consultation event already exists"
                    )
                supersedes = None
            else:
                if latest is None or latest.event_id != expected_latest_event_id:
                    raise ExternalReviewIntegrityError(
                        "external consultation head changed"
                    )
                supersedes = latest.event_id

            provisional = ExternalConsultationSnapshot(
                sequence=1,
                event_id=event_id,
                project_id=request.project_id,
                consultation_id=request.consultation_id,
                event_type=event_type,
                request_manifest=manifest,
                provider_name=request.provider_name,
                model=request.model,
                approval_required=decision.approval_required,
                approval_obtained=decision.approval_obtained,
                approver=decision.approver,
                response_sha256=response_sha256,
                response_chars=response_chars,
                failure_reason=failure_reason,
                supersedes_event_id=supersedes,
                created_at=created_at,
                content_sha256="",
            )
            content_sha256 = _sha256_json(_snapshot_hash_payload(provisional))
            cursor = self._conn.execute(
                """
                INSERT INTO external_consultation_events (
                    event_id, project_id, consultation_id, event_type,
                    request_manifest_json, provider_name, model,
                    approval_required, approval_obtained, approver,
                    response_sha256, response_chars, failure_reason,
                    supersedes_event_id, created_at, content_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    request.project_id,
                    request.consultation_id,
                    event_type.value,
                    _canonical_json(manifest),
                    request.provider_name,
                    request.model,
                    int(decision.approval_required),
                    int(decision.approval_obtained),
                    decision.approver,
                    response_sha256,
                    response_chars,
                    failure_reason,
                    supersedes,
                    created_at,
                    content_sha256,
                ),
            )
            sequence = int(cursor.lastrowid)
            self._conn.commit()
            return ExternalConsultationSnapshot(
                **{
                    **provisional.__dict__,
                    "sequence": sequence,
                    "content_sha256": content_sha256,
                }
            )
        except Exception:
            self._conn.rollback()
            raise

    def _latest_row(
        self,
        project_id: str,
        consultation_id: str,
    ) -> sqlite3.Row | None:
        return self._conn.execute(
            """
            SELECT * FROM external_consultation_events
            WHERE project_id = ? AND consultation_id = ?
            ORDER BY row_id DESC
            LIMIT 1
            """,
            (project_id, consultation_id),
        ).fetchone()

    def _row_to_snapshot(self, row: sqlite3.Row) -> ExternalConsultationSnapshot:
        try:
            manifest = json.loads(row["request_manifest_json"])
            item = ExternalConsultationSnapshot(
                sequence=int(row["row_id"]),
                event_id=row["event_id"],
                project_id=row["project_id"],
                consultation_id=row["consultation_id"],
                event_type=ExternalConsultationEventType(row["event_type"]),
                request_manifest=manifest,
                provider_name=row["provider_name"],
                model=row["model"],
                approval_required=bool(row["approval_required"]),
                approval_obtained=bool(row["approval_obtained"]),
                approver=row["approver"],
                response_sha256=row["response_sha256"],
                response_chars=row["response_chars"],
                failure_reason=row["failure_reason"],
                supersedes_event_id=row["supersedes_event_id"],
                created_at=row["created_at"],
                content_sha256=row["content_sha256"],
            )
        except Exception as exc:
            raise ExternalReviewIntegrityError(
                "invalid persisted external consultation event"
            ) from exc

        if item.request_manifest.get("project_id") != item.project_id:
            raise ExternalReviewIntegrityError("consultation manifest project mismatch")
        if item.request_manifest.get("consultation_id") != item.consultation_id:
            raise ExternalReviewIntegrityError("consultation manifest identity mismatch")
        if item.request_manifest.get("provider_name") != item.provider_name:
            raise ExternalReviewIntegrityError("consultation provider mismatch")
        if item.request_manifest.get("model") != item.model:
            raise ExternalReviewIntegrityError("consultation model mismatch")
        _parse_utc(item.created_at)
        self._validate_event(item)
        expected = _sha256_json(_snapshot_hash_payload(item))
        if not hmac.compare_digest(expected, item.content_sha256):
            raise ExternalReviewIntegrityError(
                f"external consultation hash mismatch for {item.event_id}"
            )
        return item

    @staticmethod
    def _validate_event(item: ExternalConsultationSnapshot) -> None:
        if item.event_type is ExternalConsultationEventType.REQUEST_RECORDED:
            if (
                item.supersedes_event_id is not None
                or item.response_sha256 is not None
                or item.response_chars is not None
                or item.failure_reason is not None
            ):
                raise ExternalReviewIntegrityError("invalid REQUEST_RECORDED event")
            return

        if item.supersedes_event_id is None:
            raise ExternalReviewIntegrityError("terminal event needs predecessor")

        if item.event_type is ExternalConsultationEventType.RESPONSE_ACCEPTED:
            if (
                not item.response_sha256
                or item.response_chars is None
                or item.response_chars < 0
                or item.failure_reason is not None
            ):
                raise ExternalReviewIntegrityError("invalid RESPONSE_ACCEPTED event")
        else:
            if (
                item.response_sha256 is not None
                or item.response_chars is not None
                or not item.failure_reason
            ):
                raise ExternalReviewIntegrityError("invalid failed/blocked event")

    @staticmethod
    def _validate_history(
        items: tuple[ExternalConsultationSnapshot, ...],
    ) -> None:
        if not items:
            return
        if len(items) not in {1, 2}:
            raise ExternalReviewIntegrityError(
                "external consultation history must contain request and optional terminal event"
            )
        first = items[0]
        if first.event_type is not ExternalConsultationEventType.REQUEST_RECORDED:
            raise ExternalReviewIntegrityError("consultation must start REQUEST_RECORDED")
        if len(items) == 1:
            return
        second = items[1]
        if second.event_type is ExternalConsultationEventType.REQUEST_RECORDED:
            raise ExternalReviewIntegrityError("consultation terminal event missing")
        if second.supersedes_event_id != first.event_id:
            raise ExternalReviewIntegrityError("consultation supersession chain broken")
        if _thaw(first.request_manifest) != _thaw(second.request_manifest):
            raise ExternalReviewIntegrityError("consultation manifest mutated")
        if (
            first.provider_name != second.provider_name
            or first.model != second.model
            or first.approval_required != second.approval_required
            or first.approval_obtained != second.approval_obtained
            or first.approver != second.approver
        ):
            raise ExternalReviewIntegrityError("consultation control metadata mutated")

    @staticmethod
    def _validate_project(project_id: str) -> None:
        if not _PROJECT_RE.fullmatch(project_id):
            raise ValueError("invalid project_id")

    def _initialize(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS external_consultation_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS external_consultation_events (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                project_id TEXT NOT NULL,
                consultation_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                request_manifest_json TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                model TEXT NOT NULL,
                approval_required INTEGER NOT NULL,
                approval_obtained INTEGER NOT NULL,
                approver TEXT,
                response_sha256 TEXT,
                response_chars INTEGER,
                failure_reason TEXT,
                supersedes_event_id TEXT UNIQUE,
                created_at TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                FOREIGN KEY(supersedes_event_id)
                    REFERENCES external_consultation_events(event_id)
                    ON DELETE RESTRICT
            );

            CREATE INDEX IF NOT EXISTS idx_external_consultation_project_id
                ON external_consultation_events(project_id, consultation_id, row_id DESC);

            CREATE TRIGGER IF NOT EXISTS external_consultation_no_update
            BEFORE UPDATE ON external_consultation_events
            BEGIN
                SELECT RAISE(ABORT, 'append-only external consultation: UPDATE prohibited');
            END;

            CREATE TRIGGER IF NOT EXISTS external_consultation_no_delete
            BEFORE DELETE ON external_consultation_events
            BEGIN
                SELECT RAISE(ABORT, 'append-only external consultation: DELETE prohibited');
            END;
            """
        )
        row = self._conn.execute(
            "SELECT value FROM external_consultation_meta WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO external_consultation_meta(key, value) VALUES('schema_version', ?)",
                (EXTERNAL_REVIEW_SCHEMA_VERSION,),
            )
            self._conn.commit()
        elif row["value"] != EXTERNAL_REVIEW_SCHEMA_VERSION:
            raise ExternalReviewIntegrityError(
                "unsupported external consultation schema version"
            )


class ExternalReviewBridge:
    """Policy-controlled one-call bridge with no local tool surface."""

    def __init__(
        self,
        *,
        supervisor: Supervisor,
        ledger: ExternalConsultationLedger,
        provider: ExternalReviewProvider,
    ) -> None:
        self._supervisor = supervisor
        self._ledger = ledger
        self._provider = provider

    def consult(
        self,
        request: ExternalConsultationRequest,
        *,
        approval_obtained: bool = False,
        approver: str | None = None,
    ) -> ExternalConsultationOutcome:
        state_project = str(self._supervisor.state["project_id"])
        if request.project_id != state_project:
            raise ExternalReviewPolicyError(
                "external consultation project must match Supervisor project"
            )
        if self._provider.provider_name != request.provider_name:
            raise ExternalReviewProtocolError(
                "configured provider identity does not match request"
            )

        decision = self._supervisor.inspect_project_action(
            action="external_disclosure",
            approval_obtained=approval_obtained,
            approver=approver,
        )
        self._ledger.record_request(request, decision)

        if decision.decision is not Decision.ALLOW:
            self._ledger.record_terminal(
                request=request,
                decision=decision,
                event_type=ExternalConsultationEventType.POLICY_BLOCKED,
                failure_reason=decision.reason,
            )
            return ExternalConsultationOutcome(
                status=(
                    ExternalConsultationStatus.NEEDS_HUMAN_APPROVAL
                    if decision.decision is Decision.NEEDS_HUMAN_APPROVAL
                    else ExternalConsultationStatus.BLOCKED
                ),
                decision=decision,
                review=None,
                provider_called=False,
                summary=decision.reason,
            )

        provider_request = ExternalProviderRequest.from_consultation(request)
        try:
            response = self._provider.review(
                provider_request,
                timeout_seconds=request.timeout_seconds,
            )
            self._validate_provider_response(request, response)
        except Exception as exc:
            # Do not persist provider exception text: a remote runtime may echo
            # outbound project content or secrets in its error string.
            reason = f"external provider failure: {type(exc).__name__}"
            self._ledger.record_terminal(
                request=request,
                decision=decision,
                event_type=ExternalConsultationEventType.PROVIDER_FAILED,
                failure_reason=reason,
            )
            return ExternalConsultationOutcome(
                status=ExternalConsultationStatus.FAIL,
                decision=decision,
                review=None,
                provider_called=True,
                summary=reason,
            )

        response_hash = _sha256_text(response.content)
        review = ExternalAdvisoryReview(
            consultation_id=request.consultation_id,
            provider_name=response.provider_name,
            model=response.model,
            content=response.content,
            request_manifest_sha256=_sha256_json(request.manifest()),
            response_sha256=response_hash,
            output_char_count=len(response.content),
        )
        self._ledger.record_terminal(
            request=request,
            decision=decision,
            event_type=ExternalConsultationEventType.RESPONSE_ACCEPTED,
            response_sha256=response_hash,
            response_chars=len(response.content),
        )
        return ExternalConsultationOutcome(
            status=ExternalConsultationStatus.PASS,
            decision=decision,
            review=review,
            provider_called=True,
            summary="external advisory review received",
        )

    @staticmethod
    def _validate_provider_response(
        request: ExternalConsultationRequest,
        response: ExternalProviderResponse,
    ) -> None:
        if response.provider_name != request.provider_name:
            raise ExternalReviewProtocolError("provider response identity mismatch")
        if response.model != request.model:
            raise ExternalReviewProtocolError("provider response model mismatch")
        if not response.content.strip():
            raise ExternalReviewProtocolError("external response content is empty")
        if len(response.content) > request.max_output_chars:
            raise ExternalReviewProtocolError(
                "external response exceeds max_output_chars"
            )
        forbidden_metadata = {"tools", "tool_calls", "function_call", "functions"}
        if forbidden_metadata & set(response.raw_metadata or {}):
            raise ExternalReviewProtocolError(
                "external response attempted to carry tool-call metadata"
            )
