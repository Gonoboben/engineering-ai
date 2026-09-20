"""Controlled registered-capability bridge for Gate 022.

This module is transport-neutral. It can be wrapped by MCP later, but no
transport can gain authority beyond the registered capability metadata,
Supervisor/PolicyEngine decision, and private local handler binding.
"""

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
from typing import Any, Callable, Mapping, Protocol
from uuid import uuid4

from jsonschema import Draft202012Validator, ValidationError

from engineering_ai.supervisor.core import Supervisor
from engineering_ai.supervisor.policy import Decision, PolicyDecision
from engineering_ai.tools.filesystem import ReadOnlyFilesystemAdapter
from engineering_ai.tools.git import GitReadOnlyAdapter


TOOL_BRIDGE_SCHEMA_VERSION = "1.0"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
_PROJECT_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
_CAPABILITY_RE = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")
_MAX_REQUEST_CHARS = 32_768
_MAX_RESPONSE_CHARS = 131_072
_MAX_TIMEOUT_SECONDS = 300


class ControlledToolBridgeError(RuntimeError):
    pass


class ControlledToolBridgePolicyError(ControlledToolBridgeError):
    pass


class ControlledToolBridgeIntegrityError(ControlledToolBridgeError):
    pass


class ControlledToolBridgeProtocolError(ControlledToolBridgeError):
    pass


class CapabilitySideEffect(str, Enum):
    READ_ONLY = "READ_ONLY"


class ToolBridgeStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NEEDS_HUMAN_APPROVAL = "NEEDS_HUMAN_APPROVAL"


class ToolInvocationEventType(str, Enum):
    REQUEST_RECORDED = "REQUEST_RECORDED"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    TOOL_FAILED = "TOOL_FAILED"
    RESULT_ACCEPTED = "RESULT_ACCEPTED"


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _default_event_id() -> str:
    return f"tevt-{uuid4().hex}"


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("tool bridge clock must return timezone-aware datetime")
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
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            _thaw(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ControlledToolBridgeProtocolError(
            "tool bridge values must be canonical JSON"
        ) from exc


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CapabilityDefinition:
    capability_id: str
    project_id: str
    action: str
    description: str
    input_schema: Mapping[str, Any]
    output_schema: Mapping[str, Any]
    side_effect: CapabilitySideEffect = CapabilitySideEffect.READ_ONLY
    timeout_seconds: int = 30
    max_request_chars: int = 8_192
    max_response_chars: int = 65_536

    def __post_init__(self) -> None:
        if not _CAPABILITY_RE.fullmatch(self.capability_id):
            raise ValueError("invalid capability_id")
        if not _PROJECT_RE.fullmatch(self.project_id):
            raise ValueError("invalid capability project_id")
        if not self.action.strip():
            raise ValueError("capability action must be non-empty")
        if not self.description.strip():
            raise ValueError("capability description must be non-empty")
        if self.side_effect is not CapabilitySideEffect.READ_ONLY:
            raise ControlledToolBridgePolicyError(
                "Gate 022 acceptance permits READ_ONLY capabilities only"
            )
        if not 1 <= self.timeout_seconds <= _MAX_TIMEOUT_SECONDS:
            raise ValueError("timeout_seconds out of bounds")
        if not 1 <= self.max_request_chars <= _MAX_REQUEST_CHARS:
            raise ValueError("max_request_chars out of bounds")
        if not 1 <= self.max_response_chars <= _MAX_RESPONSE_CHARS:
            raise ValueError("max_response_chars out of bounds")

        input_schema = deepcopy(dict(self.input_schema))
        output_schema = deepcopy(dict(self.output_schema))
        Draft202012Validator.check_schema(input_schema)
        Draft202012Validator.check_schema(output_schema)
        object.__setattr__(self, "input_schema", _freeze(input_schema))
        object.__setattr__(self, "output_schema", _freeze(output_schema))

    def public_descriptor(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "project_id": self.project_id,
            "action": self.action,
            "description": self.description,
            "input_schema": _thaw(self.input_schema),
            "output_schema": _thaw(self.output_schema),
            "side_effect": self.side_effect.value,
            "timeout_seconds": self.timeout_seconds,
            "max_request_chars": self.max_request_chars,
            "max_response_chars": self.max_response_chars,
        }


@dataclass(frozen=True)
class CapabilityResult:
    ok: bool
    payload: Any
    summary: str
    evidence_refs: tuple[str, ...] = ()
    timed_out: bool = False

    def __post_init__(self) -> None:
        if not self.summary.strip():
            raise ValueError("capability result summary must be non-empty")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("evidence_refs must be unique")


class CapabilityHandler(Protocol):
    def __call__(
        self,
        arguments: Mapping[str, Any],
        *,
        timeout_seconds: int,
    ) -> CapabilityResult:
        ...


@dataclass(frozen=True)
class CapabilityBinding:
    definition: CapabilityDefinition
    handler: CapabilityHandler


class CapabilityRegistry:
    """Immutable registry. Public listing never exposes local handler objects."""

    def __init__(self, bindings: tuple[CapabilityBinding, ...]) -> None:
        if not bindings:
            raise ValueError("capability registry must be non-empty")
        mapped: dict[str, CapabilityBinding] = {}
        for binding in bindings:
            key = binding.definition.capability_id
            if key in mapped:
                raise ValueError(f"duplicate capability_id: {key}")
            mapped[key] = binding
        self._bindings = MappingProxyType(mapped)

    def list_capabilities(
        self,
        *,
        project_id: str,
    ) -> tuple[Mapping[str, Any], ...]:
        if not _PROJECT_RE.fullmatch(project_id):
            raise ValueError("invalid project_id")
        descriptors = [
            binding.definition.public_descriptor()
            for binding in self._bindings.values()
            if binding.definition.project_id == project_id
        ]
        descriptors.sort(key=lambda item: item["capability_id"])
        return tuple(_freeze(item) for item in descriptors)

    def _binding(self, capability_id: str) -> CapabilityBinding | None:
        return self._bindings.get(capability_id)


@dataclass(frozen=True)
class ToolInvocationRequest:
    invocation_id: str
    project_id: str
    capability_id: str
    arguments: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.invocation_id):
            raise ValueError("invalid invocation_id")
        if not _PROJECT_RE.fullmatch(self.project_id):
            raise ValueError("invalid project_id")
        if not _CAPABILITY_RE.fullmatch(self.capability_id):
            raise ValueError("invalid capability_id")
        args = deepcopy(dict(self.arguments))
        serialized = _canonical_json(args)
        if len(serialized) > _MAX_REQUEST_CHARS:
            raise ControlledToolBridgeProtocolError(
                "tool invocation exceeds hard request limit"
            )
        object.__setattr__(self, "arguments", _freeze(args))

    @property
    def request_sha256(self) -> str:
        return _sha256_json(
            {
                "invocation_id": self.invocation_id,
                "project_id": self.project_id,
                "capability_id": self.capability_id,
                "arguments": _thaw(self.arguments),
            }
        )

    @property
    def request_chars(self) -> int:
        return len(
            _canonical_json(
                {
                    "invocation_id": self.invocation_id,
                    "project_id": self.project_id,
                    "capability_id": self.capability_id,
                    "arguments": _thaw(self.arguments),
                }
            )
        )


@dataclass(frozen=True)
class ToolBridgeOutcome:
    status: ToolBridgeStatus
    capability_id: str
    decision: PolicyDecision | None
    result: CapabilityResult | None
    handler_called: bool
    summary: str


@dataclass(frozen=True)
class ToolInvocationSnapshot:
    sequence: int
    event_id: str
    project_id: str
    invocation_id: str
    capability_id: str
    action: str | None
    side_effect: str | None
    event_type: ToolInvocationEventType
    policy_decision: str
    approval_required: bool
    approval_obtained: bool
    approver: str | None
    request_sha256: str
    request_chars: int
    response_sha256: str | None
    response_chars: int | None
    evidence_refs: tuple[str, ...]
    failure_class: str | None
    supersedes_event_id: str | None
    created_at: str
    content_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": TOOL_BRIDGE_SCHEMA_VERSION,
            "sequence": self.sequence,
            **_audit_hash_payload(self),
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class ToolInvocationIntegrityReport:
    events_checked: int
    invocations_checked: int
    ok: bool


def _audit_hash_payload(item: ToolInvocationSnapshot) -> dict[str, Any]:
    return {
        "schema_version": TOOL_BRIDGE_SCHEMA_VERSION,
        "event_id": item.event_id,
        "project_id": item.project_id,
        "invocation_id": item.invocation_id,
        "capability_id": item.capability_id,
        "action": item.action,
        "side_effect": item.side_effect,
        "event_type": item.event_type.value,
        "policy_decision": item.policy_decision,
        "approval_required": item.approval_required,
        "approval_obtained": item.approval_obtained,
        "approver": item.approver,
        "request_sha256": item.request_sha256,
        "request_chars": item.request_chars,
        "response_sha256": item.response_sha256,
        "response_chars": item.response_chars,
        "evidence_refs": list(item.evidence_refs),
        "failure_class": item.failure_class,
        "supersedes_event_id": item.supersedes_event_id,
        "created_at": item.created_at,
    }


class ToolInvocationLedger:
    """Append-only invocation metadata ledger; request/result payloads are not stored."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        clock: Callable[[], datetime] = _default_clock,
        event_id_factory: Callable[[], str] = _default_event_id,
    ) -> None:
        raw = Path(database_path)
        if raw.exists() and raw.is_symlink():
            raise ControlledToolBridgePolicyError(
                "tool invocation database path must not be a symlink"
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

    def __enter__(self) -> "ToolInvocationLedger":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def record_request(
        self,
        request: ToolInvocationRequest,
        *,
        definition: CapabilityDefinition | None,
        policy_decision: str,
        approval_required: bool,
        approval_obtained: bool,
        approver: str | None,
    ) -> ToolInvocationSnapshot:
        if self._latest_row(request.project_id, request.invocation_id) is not None:
            raise ControlledToolBridgePolicyError("invocation_id already exists")
        return self._append(
            request=request,
            definition=definition,
            event_type=ToolInvocationEventType.REQUEST_RECORDED,
            policy_decision=policy_decision,
            approval_required=approval_required,
            approval_obtained=approval_obtained,
            approver=approver,
            response_sha256=None,
            response_chars=None,
            evidence_refs=(),
            failure_class=None,
            expected_latest_event_id=None,
        )

    def record_terminal(
        self,
        *,
        request: ToolInvocationRequest,
        definition: CapabilityDefinition | None,
        event_type: ToolInvocationEventType,
        policy_decision: str,
        approval_required: bool,
        approval_obtained: bool,
        approver: str | None,
        response_payload: Any | None = None,
        evidence_refs: tuple[str, ...] = (),
        failure_class: str | None = None,
    ) -> ToolInvocationSnapshot:
        if event_type not in {
            ToolInvocationEventType.POLICY_BLOCKED,
            ToolInvocationEventType.TOOL_FAILED,
            ToolInvocationEventType.RESULT_ACCEPTED,
        }:
            raise ValueError("invalid terminal invocation event")
        latest = self.get(
            project_id=request.project_id,
            invocation_id=request.invocation_id,
        )
        if latest.event_type is not ToolInvocationEventType.REQUEST_RECORDED:
            raise ControlledToolBridgePolicyError("invocation is already terminal")

        response_sha256 = None
        response_chars = None
        if event_type is ToolInvocationEventType.RESULT_ACCEPTED:
            encoded = _canonical_json(response_payload)
            response_sha256 = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
            response_chars = len(encoded)
            if failure_class is not None:
                raise ValueError("accepted result cannot have failure_class")
        else:
            if failure_class is None or not failure_class.strip():
                raise ValueError("blocked/failed result requires failure_class")

        return self._append(
            request=request,
            definition=definition,
            event_type=event_type,
            policy_decision=policy_decision,
            approval_required=approval_required,
            approval_obtained=approval_obtained,
            approver=approver,
            response_sha256=response_sha256,
            response_chars=response_chars,
            evidence_refs=evidence_refs,
            failure_class=failure_class,
            expected_latest_event_id=latest.event_id,
        )

    def history(
        self,
        *,
        project_id: str,
        invocation_id: str,
    ) -> tuple[ToolInvocationSnapshot, ...]:
        if not _PROJECT_RE.fullmatch(project_id):
            raise ValueError("invalid project_id")
        rows = self._conn.execute(
            """
            SELECT * FROM controlled_tool_invocation_events
            WHERE project_id = ? AND invocation_id = ?
            ORDER BY row_id ASC
            """,
            (project_id, invocation_id),
        ).fetchall()
        items = tuple(self._row_to_snapshot(row) for row in rows)
        self._validate_history(items)
        return items

    def get(
        self,
        *,
        project_id: str,
        invocation_id: str,
    ) -> ToolInvocationSnapshot:
        history = self.history(project_id=project_id, invocation_id=invocation_id)
        if not history:
            raise KeyError(invocation_id)
        return history[-1]

    def verify_integrity(
        self,
        *,
        project_id: str | None = None,
    ) -> ToolInvocationIntegrityReport:
        if project_id is None:
            rows = self._conn.execute(
                "SELECT * FROM controlled_tool_invocation_events ORDER BY row_id ASC"
            ).fetchall()
        else:
            if not _PROJECT_RE.fullmatch(project_id):
                raise ValueError("invalid project_id")
            rows = self._conn.execute(
                """
                SELECT * FROM controlled_tool_invocation_events
                WHERE project_id = ?
                ORDER BY row_id ASC
                """,
                (project_id,),
            ).fetchall()
        grouped: dict[tuple[str, str], list[ToolInvocationSnapshot]] = {}
        for row in rows:
            item = self._row_to_snapshot(row)
            grouped.setdefault((item.project_id, item.invocation_id), []).append(item)
        for items in grouped.values():
            self._validate_history(tuple(items))
        return ToolInvocationIntegrityReport(
            events_checked=len(rows),
            invocations_checked=len(grouped),
            ok=True,
        )

    def _append(
        self,
        *,
        request: ToolInvocationRequest,
        definition: CapabilityDefinition | None,
        event_type: ToolInvocationEventType,
        policy_decision: str,
        approval_required: bool,
        approval_obtained: bool,
        approver: str | None,
        response_sha256: str | None,
        response_chars: int | None,
        evidence_refs: tuple[str, ...],
        failure_class: str | None,
        expected_latest_event_id: str | None,
    ) -> ToolInvocationSnapshot:
        event_id = self._event_id_factory()
        if not _ID_RE.fullmatch(event_id):
            raise ValueError("invalid tool invocation event_id")
        created_at = _utc_iso(self._clock())

        self._conn.execute("BEGIN IMMEDIATE")
        try:
            latest_row = self._latest_row(request.project_id, request.invocation_id)
            latest = self._row_to_snapshot(latest_row) if latest_row else None
            if expected_latest_event_id is None:
                if latest is not None:
                    raise ControlledToolBridgePolicyError(
                        "initial invocation event already exists"
                    )
                supersedes = None
            else:
                if latest is None or latest.event_id != expected_latest_event_id:
                    raise ControlledToolBridgeIntegrityError(
                        "tool invocation audit head changed"
                    )
                supersedes = latest.event_id

            provisional = ToolInvocationSnapshot(
                sequence=1,
                event_id=event_id,
                project_id=request.project_id,
                invocation_id=request.invocation_id,
                capability_id=request.capability_id,
                action=definition.action if definition else None,
                side_effect=definition.side_effect.value if definition else None,
                event_type=event_type,
                policy_decision=policy_decision,
                approval_required=approval_required,
                approval_obtained=approval_obtained,
                approver=approver,
                request_sha256=request.request_sha256,
                request_chars=request.request_chars,
                response_sha256=response_sha256,
                response_chars=response_chars,
                evidence_refs=tuple(evidence_refs),
                failure_class=failure_class,
                supersedes_event_id=supersedes,
                created_at=created_at,
                content_sha256="",
            )
            content_sha256 = _sha256_json(_audit_hash_payload(provisional))
            cursor = self._conn.execute(
                """
                INSERT INTO controlled_tool_invocation_events (
                    event_id, project_id, invocation_id, capability_id,
                    action, side_effect, event_type, policy_decision,
                    approval_required, approval_obtained, approver,
                    request_sha256, request_chars,
                    response_sha256, response_chars, evidence_refs_json,
                    failure_class, supersedes_event_id, created_at, content_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    request.project_id,
                    request.invocation_id,
                    request.capability_id,
                    provisional.action,
                    provisional.side_effect,
                    event_type.value,
                    policy_decision,
                    int(approval_required),
                    int(approval_obtained),
                    approver,
                    provisional.request_sha256,
                    provisional.request_chars,
                    response_sha256,
                    response_chars,
                    _canonical_json(list(evidence_refs)),
                    failure_class,
                    supersedes,
                    created_at,
                    content_sha256,
                ),
            )
            sequence = int(cursor.lastrowid)
            self._conn.commit()
            return ToolInvocationSnapshot(
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
        invocation_id: str,
    ) -> sqlite3.Row | None:
        return self._conn.execute(
            """
            SELECT * FROM controlled_tool_invocation_events
            WHERE project_id = ? AND invocation_id = ?
            ORDER BY row_id DESC
            LIMIT 1
            """,
            (project_id, invocation_id),
        ).fetchone()

    def _row_to_snapshot(self, row: sqlite3.Row) -> ToolInvocationSnapshot:
        try:
            item = ToolInvocationSnapshot(
                sequence=int(row["row_id"]),
                event_id=row["event_id"],
                project_id=row["project_id"],
                invocation_id=row["invocation_id"],
                capability_id=row["capability_id"],
                action=row["action"],
                side_effect=row["side_effect"],
                event_type=ToolInvocationEventType(row["event_type"]),
                policy_decision=row["policy_decision"],
                approval_required=bool(row["approval_required"]),
                approval_obtained=bool(row["approval_obtained"]),
                approver=row["approver"],
                request_sha256=row["request_sha256"],
                request_chars=int(row["request_chars"]),
                response_sha256=row["response_sha256"],
                response_chars=row["response_chars"],
                evidence_refs=tuple(json.loads(row["evidence_refs_json"])),
                failure_class=row["failure_class"],
                supersedes_event_id=row["supersedes_event_id"],
                created_at=row["created_at"],
                content_sha256=row["content_sha256"],
            )
        except Exception as exc:
            raise ControlledToolBridgeIntegrityError(
                "invalid persisted tool invocation event"
            ) from exc
        _parse_utc(item.created_at)
        self._validate_event(item)
        expected = _sha256_json(_audit_hash_payload(item))
        if not hmac.compare_digest(expected, item.content_sha256):
            raise ControlledToolBridgeIntegrityError(
                f"tool invocation hash mismatch for {item.event_id}"
            )
        return item

    @staticmethod
    def _validate_event(item: ToolInvocationSnapshot) -> None:
        if item.event_type is ToolInvocationEventType.REQUEST_RECORDED:
            if (
                item.supersedes_event_id is not None
                or item.response_sha256 is not None
                or item.response_chars is not None
                or item.failure_class is not None
                or item.evidence_refs
            ):
                raise ControlledToolBridgeIntegrityError(
                    "invalid REQUEST_RECORDED event"
                )
            return
        if item.supersedes_event_id is None:
            raise ControlledToolBridgeIntegrityError(
                "terminal invocation event needs predecessor"
            )
        if item.event_type is ToolInvocationEventType.RESULT_ACCEPTED:
            if (
                not item.response_sha256
                or item.response_chars is None
                or item.response_chars < 0
                or item.failure_class is not None
            ):
                raise ControlledToolBridgeIntegrityError(
                    "invalid RESULT_ACCEPTED event"
                )
        else:
            if (
                item.response_sha256 is not None
                or item.response_chars is not None
                or not item.failure_class
                or item.evidence_refs
            ):
                raise ControlledToolBridgeIntegrityError(
                    "invalid blocked/failed invocation event"
                )

    @staticmethod
    def _validate_history(
        items: tuple[ToolInvocationSnapshot, ...],
    ) -> None:
        if not items:
            return
        if len(items) not in {1, 2}:
            raise ControlledToolBridgeIntegrityError(
                "tool invocation history must contain request and optional terminal event"
            )
        first = items[0]
        if first.event_type is not ToolInvocationEventType.REQUEST_RECORDED:
            raise ControlledToolBridgeIntegrityError(
                "tool invocation must start REQUEST_RECORDED"
            )
        if len(items) == 1:
            return
        second = items[1]
        if second.event_type is ToolInvocationEventType.REQUEST_RECORDED:
            raise ControlledToolBridgeIntegrityError(
                "tool invocation terminal event missing"
            )
        if second.supersedes_event_id != first.event_id:
            raise ControlledToolBridgeIntegrityError(
                "tool invocation supersession chain broken"
            )
        immutable = (
            "project_id",
            "invocation_id",
            "capability_id",
            "action",
            "side_effect",
            "policy_decision",
            "approval_required",
            "approval_obtained",
            "approver",
            "request_sha256",
            "request_chars",
        )
        for field in immutable:
            if getattr(first, field) != getattr(second, field):
                raise ControlledToolBridgeIntegrityError(
                    f"tool invocation control metadata mutated: {field}"
                )

    def _initialize(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS controlled_tool_invocation_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS controlled_tool_invocation_events (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                project_id TEXT NOT NULL,
                invocation_id TEXT NOT NULL,
                capability_id TEXT NOT NULL,
                action TEXT,
                side_effect TEXT,
                event_type TEXT NOT NULL,
                policy_decision TEXT NOT NULL,
                approval_required INTEGER NOT NULL,
                approval_obtained INTEGER NOT NULL,
                approver TEXT,
                request_sha256 TEXT NOT NULL,
                request_chars INTEGER NOT NULL,
                response_sha256 TEXT,
                response_chars INTEGER,
                evidence_refs_json TEXT NOT NULL,
                failure_class TEXT,
                supersedes_event_id TEXT UNIQUE,
                created_at TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                FOREIGN KEY(supersedes_event_id)
                    REFERENCES controlled_tool_invocation_events(event_id)
                    ON DELETE RESTRICT
            );

            CREATE INDEX IF NOT EXISTS idx_controlled_tool_invocation_project
                ON controlled_tool_invocation_events(
                    project_id, invocation_id, row_id DESC
                );

            CREATE TRIGGER IF NOT EXISTS controlled_tool_invocation_no_update
            BEFORE UPDATE ON controlled_tool_invocation_events
            BEGIN
                SELECT RAISE(ABORT, 'append-only tool invocation: UPDATE prohibited');
            END;

            CREATE TRIGGER IF NOT EXISTS controlled_tool_invocation_no_delete
            BEFORE DELETE ON controlled_tool_invocation_events
            BEGIN
                SELECT RAISE(ABORT, 'append-only tool invocation: DELETE prohibited');
            END;
            """
        )
        row = self._conn.execute(
            "SELECT value FROM controlled_tool_invocation_meta WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO controlled_tool_invocation_meta(key, value) VALUES('schema_version', ?)",
                (TOOL_BRIDGE_SCHEMA_VERSION,),
            )
            self._conn.commit()
        elif row["value"] != TOOL_BRIDGE_SCHEMA_VERSION:
            raise ControlledToolBridgeIntegrityError(
                "unsupported controlled tool bridge schema version"
            )


class ControlledToolBridge:
    """Policy-gated invocation of private, pre-registered local capability handlers."""

    def __init__(
        self,
        *,
        supervisor: Supervisor,
        registry: CapabilityRegistry,
        ledger: ToolInvocationLedger,
    ) -> None:
        self._supervisor = supervisor
        self._registry = registry
        self._ledger = ledger

    def list_capabilities(self) -> tuple[Mapping[str, Any], ...]:
        return self._registry.list_capabilities(
            project_id=str(self._supervisor.state["project_id"])
        )

    def invoke(
        self,
        request: ToolInvocationRequest,
        *,
        approval_obtained: bool = False,
        approver: str | None = None,
    ) -> ToolBridgeOutcome:
        supervisor_project = str(self._supervisor.state["project_id"])
        binding = self._registry._binding(request.capability_id)

        if request.project_id != supervisor_project:
            self._record_blocked(
                request=request,
                definition=binding.definition if binding else None,
                policy_decision="PROJECT_MISMATCH",
                approval_required=False,
                approval_obtained=False,
                approver=None,
                failure_class="PROJECT_MISMATCH",
            )
            return ToolBridgeOutcome(
                status=ToolBridgeStatus.BLOCKED,
                capability_id=request.capability_id,
                decision=None,
                result=None,
                handler_called=False,
                summary="invocation project does not match Supervisor project",
            )

        if binding is None:
            self._record_blocked(
                request=request,
                definition=None,
                policy_decision="UNREGISTERED",
                approval_required=False,
                approval_obtained=False,
                approver=None,
                failure_class="UNREGISTERED_CAPABILITY",
            )
            return ToolBridgeOutcome(
                status=ToolBridgeStatus.BLOCKED,
                capability_id=request.capability_id,
                decision=None,
                result=None,
                handler_called=False,
                summary="capability is not registered",
            )

        definition = binding.definition
        if definition.project_id != supervisor_project:
            self._record_blocked(
                request=request,
                definition=definition,
                policy_decision="CAPABILITY_PROJECT_MISMATCH",
                approval_required=False,
                approval_obtained=False,
                approver=None,
                failure_class="CAPABILITY_PROJECT_MISMATCH",
            )
            return ToolBridgeOutcome(
                status=ToolBridgeStatus.BLOCKED,
                capability_id=request.capability_id,
                decision=None,
                result=None,
                handler_called=False,
                summary="capability project does not match Supervisor project",
            )

        request_chars = len(_canonical_json(_thaw(request.arguments)))
        if request_chars > definition.max_request_chars:
            self._record_blocked(
                request=request,
                definition=definition,
                policy_decision="INPUT_REJECTED",
                approval_required=False,
                approval_obtained=False,
                approver=None,
                failure_class="REQUEST_BUDGET_EXCEEDED",
            )
            return ToolBridgeOutcome(
                status=ToolBridgeStatus.BLOCKED,
                capability_id=request.capability_id,
                decision=None,
                result=None,
                handler_called=False,
                summary="capability request exceeds configured bound",
            )

        try:
            Draft202012Validator(_thaw(definition.input_schema)).validate(
                _thaw(request.arguments)
            )
        except ValidationError:
            self._record_blocked(
                request=request,
                definition=definition,
                policy_decision="INPUT_REJECTED",
                approval_required=False,
                approval_obtained=False,
                approver=None,
                failure_class="INPUT_SCHEMA_REJECTED",
            )
            return ToolBridgeOutcome(
                status=ToolBridgeStatus.BLOCKED,
                capability_id=request.capability_id,
                decision=None,
                result=None,
                handler_called=False,
                summary="capability input schema rejected request",
            )

        decision = self._supervisor.inspect_project_action(
            action=definition.action,
            approval_obtained=approval_obtained,
            approver=approver,
        )
        self._ledger.record_request(
            request,
            definition=definition,
            policy_decision=decision.decision.value,
            approval_required=decision.approval_required,
            approval_obtained=decision.approval_obtained,
            approver=decision.approver,
        )

        if decision.decision is not Decision.ALLOW:
            self._ledger.record_terminal(
                request=request,
                definition=definition,
                event_type=ToolInvocationEventType.POLICY_BLOCKED,
                policy_decision=decision.decision.value,
                approval_required=decision.approval_required,
                approval_obtained=decision.approval_obtained,
                approver=decision.approver,
                failure_class=(
                    "NEEDS_HUMAN_APPROVAL"
                    if decision.decision is Decision.NEEDS_HUMAN_APPROVAL
                    else "POLICY_DENIED"
                ),
            )
            return ToolBridgeOutcome(
                status=(
                    ToolBridgeStatus.NEEDS_HUMAN_APPROVAL
                    if decision.decision is Decision.NEEDS_HUMAN_APPROVAL
                    else ToolBridgeStatus.BLOCKED
                ),
                capability_id=request.capability_id,
                decision=decision,
                result=None,
                handler_called=False,
                summary=decision.reason,
            )

        try:
            result = binding.handler(
                _thaw(request.arguments),
                timeout_seconds=definition.timeout_seconds,
            )
            if not isinstance(result, CapabilityResult):
                raise ControlledToolBridgeProtocolError(
                    "capability handler returned invalid result type"
                )
            encoded = _canonical_json(result.payload)
            if len(encoded) > definition.max_response_chars:
                raise ControlledToolBridgeProtocolError(
                    "capability response exceeds configured bound"
                )
            Draft202012Validator(_thaw(definition.output_schema)).validate(
                _thaw(result.payload)
            )
            if result.timed_out:
                raise ControlledToolBridgeProtocolError("capability timed out")
        except Exception as exc:
            failure_class = type(exc).__name__
            self._ledger.record_terminal(
                request=request,
                definition=definition,
                event_type=ToolInvocationEventType.TOOL_FAILED,
                policy_decision=decision.decision.value,
                approval_required=decision.approval_required,
                approval_obtained=decision.approval_obtained,
                approver=decision.approver,
                failure_class=failure_class,
            )
            return ToolBridgeOutcome(
                status=ToolBridgeStatus.FAIL,
                capability_id=request.capability_id,
                decision=decision,
                result=None,
                handler_called=True,
                summary=f"registered capability failed: {failure_class}",
            )

        if not result.ok:
            self._ledger.record_terminal(
                request=request,
                definition=definition,
                event_type=ToolInvocationEventType.TOOL_FAILED,
                policy_decision=decision.decision.value,
                approval_required=decision.approval_required,
                approval_obtained=decision.approval_obtained,
                approver=decision.approver,
                failure_class="CAPABILITY_REPORTED_FAILURE",
            )
            return ToolBridgeOutcome(
                status=ToolBridgeStatus.FAIL,
                capability_id=request.capability_id,
                decision=decision,
                result=result,
                handler_called=True,
                summary=result.summary,
            )

        self._ledger.record_terminal(
            request=request,
            definition=definition,
            event_type=ToolInvocationEventType.RESULT_ACCEPTED,
            policy_decision=decision.decision.value,
            approval_required=decision.approval_required,
            approval_obtained=decision.approval_obtained,
            approver=decision.approver,
            response_payload=_thaw(result.payload),
            evidence_refs=result.evidence_refs,
        )
        return ToolBridgeOutcome(
            status=ToolBridgeStatus.PASS,
            capability_id=request.capability_id,
            decision=decision,
            result=result,
            handler_called=True,
            summary=result.summary,
        )

    def _record_blocked(
        self,
        *,
        request: ToolInvocationRequest,
        definition: CapabilityDefinition | None,
        policy_decision: str,
        approval_required: bool,
        approval_obtained: bool,
        approver: str | None,
        failure_class: str,
    ) -> None:
        self._ledger.record_request(
            request,
            definition=definition,
            policy_decision=policy_decision,
            approval_required=approval_required,
            approval_obtained=approval_obtained,
            approver=approver,
        )
        self._ledger.record_terminal(
            request=request,
            definition=definition,
            event_type=ToolInvocationEventType.POLICY_BLOCKED,
            policy_decision=policy_decision,
            approval_required=approval_required,
            approval_obtained=approval_obtained,
            approver=approver,
            failure_class=failure_class,
        )


class _FilesystemReadTextHandler:
    def __init__(self, adapter: ReadOnlyFilesystemAdapter) -> None:
        self._adapter = adapter

    def __call__(
        self,
        arguments: Mapping[str, Any],
        *,
        timeout_seconds: int,
    ) -> CapabilityResult:
        del timeout_seconds
        text = self._adapter.read_text(str(arguments["path"]))
        return CapabilityResult(
            ok=True,
            payload={"text": text},
            summary="bounded read-only file read completed",
        )


class _GitStatusHandler:
    def __init__(self, adapter: GitReadOnlyAdapter) -> None:
        self._adapter = adapter

    def __call__(
        self,
        arguments: Mapping[str, Any],
        *,
        timeout_seconds: int,
    ) -> CapabilityResult:
        del arguments, timeout_seconds
        result = self._adapter.status()
        return CapabilityResult(
            ok=result.ok,
            payload={
                "operation": result.operation,
                "summary": result.summary,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
                "timed_out": result.timed_out,
                "truncated": result.truncated,
            },
            summary=result.summary,
            timed_out=result.timed_out,
        )


def filesystem_read_text_binding(
    *,
    project_id: str,
    adapter: ReadOnlyFilesystemAdapter,
    capability_id: str = "filesystem.read_text",
) -> CapabilityBinding:
    definition = CapabilityDefinition(
        capability_id=capability_id,
        project_id=project_id,
        action="read_repository",
        description="Read one UTF-8 text file inside the configured project root.",
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 1024,
                }
            },
        },
        output_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["text"],
            "properties": {"text": {"type": "string"}},
        },
        side_effect=CapabilitySideEffect.READ_ONLY,
        timeout_seconds=30,
        max_request_chars=2_048,
        max_response_chars=131_072,
    )
    return CapabilityBinding(
        definition=definition,
        handler=_FilesystemReadTextHandler(adapter),
    )


def git_status_binding(
    *,
    project_id: str,
    adapter: GitReadOnlyAdapter,
    capability_id: str = "git.status",
) -> CapabilityBinding:
    definition = CapabilityDefinition(
        capability_id=capability_id,
        project_id=project_id,
        action="read_repository",
        description="Return bounded read-only Git status for the configured repository.",
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "maxProperties": 0,
        },
        output_schema={
            "type": "object",
            "additionalProperties": False,
            "required": [
                "operation",
                "summary",
                "stdout",
                "stderr",
                "exit_code",
                "timed_out",
                "truncated",
            ],
            "properties": {
                "operation": {"type": "string"},
                "summary": {"type": "string"},
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "exit_code": {"type": ["integer", "null"]},
                "timed_out": {"type": "boolean"},
                "truncated": {"type": "boolean"},
            },
        },
        side_effect=CapabilitySideEffect.READ_ONLY,
        timeout_seconds=30,
        max_request_chars=128,
        max_response_chars=131_072,
    )
    return CapabilityBinding(
        definition=definition,
        handler=_GitStatusHandler(adapter),
    )
