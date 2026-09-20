from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from engineering_ai.supervisor import (
    PersistedJobQueue,
    PersistedScheduledRunStore,
    ScheduleEventType,
    ScheduledRunDefinition,
    ScheduledRunExecutor,
    StubTool,
    Supervisor,
    ToolOutcome,
)


FIXED_NOW = datetime(2026, 9, 20, 22, 0, 0, tzinfo=timezone.utc)


class FixedClock:
    def __init__(self) -> None:
        self.value = FIXED_NOW

    def __call__(self) -> datetime:
        return self.value


def policy() -> dict:
    return {
        "schema_version": "1.0",
        "policy_version": "gate020-smoke",
        "project_id": "engineering-ai",
        "autonomous_actions": ["read_repository", "run_validator"],
        "approval_required_actions": [
            "architecture_change",
            "physics_change",
            "destructive_action",
            "fabrication_authorization",
            "release_authorization",
            "external_disclosure",
            "scope_expansion",
        ],
        "forbidden_actions": ["validator_weakening"],
        "mandatory_validators": [],
        "stop_conditions": ["approval boundary reached"],
        "retry_limit": 2,
    }


def state() -> dict:
    return {
        "schema_version": "1.0",
        "state_revision": 1,
        "project_id": "engineering-ai",
        "current_gate": "020",
        "active_job_id": None,
        "repository_ref": {
            "branch": "gate-020-scheduled-overnight-runs",
            "head_sha": "0123456789abcdef0123456789abcdef01234567",
        },
        "architecture_baseline": "Gate 019 accepted persisted queue",
        "effective_permissions": {
            "autonomous": ["read_repository", "run_validator"],
            "approval_required": [
                "architecture_change",
                "physics_change",
                "destructive_action",
                "fabrication_authorization",
                "release_authorization",
                "external_disclosure",
                "scope_expansion",
            ],
            "forbidden": ["validator_weakening"],
        },
        "pending_checks": [],
        "blockers": [],
        "validation_states": [
            {
                "check_id": "physical-validation",
                "validation_class": "PHYSICAL",
                "state": "PHYSICAL_NOT_EXECUTED",
                "evidence_refs": [],
            }
        ],
        "next_admissible_action": None,
    }


def job(job_id: str, action: str) -> dict:
    return {
        "schema_version": "1.0",
        "job_id": job_id,
        "project_id": "engineering-ai",
        "gate_id": "020",
        "objective": f"Gate 020 smoke {job_id}",
        "scope": ["bounded unattended scheduled run"],
        "out_of_scope": [
            "automatic approval",
            "OS scheduler installation",
            "physical validation",
        ],
        "requested_actions": [action],
        "required_validators": [],
        "retry_limit": 2,
        "attempts": 0,
        "status": "QUEUED",
        "blocker": None,
    }


def supervisor(queue: PersistedJobQueue) -> Supervisor:
    return Supervisor(policy=policy(), state=state(), job_queue=queue)


def main() -> int:
    clock = FixedClock()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        queue_path = root / "jobs.sqlite3"
        schedule_path = root / "scheduled.sqlite3"

        queue = PersistedJobQueue(queue_path, clock=clock)
        schedules = PersistedScheduledRunStore(schedule_path, clock=clock)
        sup = supervisor(queue)

        for item in (
            job("gate020-interrupted", "read_repository"),
            job("gate020-read", "read_repository"),
            job("gate020-approval", "architecture_change"),
            job("gate020-forbidden", "validator_weakening"),
            job("gate020-unlisted-auto", "run_validator"),
        ):
            sup.enqueue_persisted_job(item, timeout_seconds=300)

        interrupted = sup.claim_persisted_job(job_id="gate020-interrupted")
        assert interrupted.status == "RUNNING"

        schedules.schedule(
            ScheduledRunDefinition(
                schedule_id="gate020-overnight",
                project_id="engineering-ai",
                due_at=clock.value.isoformat().replace("+00:00", "Z"),
                allowed_actions=(
                    "read_repository",
                    "architecture_change",
                    "validator_weakening",
                ),
                max_jobs=10,
                max_session_seconds=3600,
            )
        )
        schedules.schedule(
            ScheduledRunDefinition(
                schedule_id="gate020-future",
                project_id="engineering-ai",
                due_at=(
                    clock.value + timedelta(hours=1)
                ).isoformat().replace("+00:00", "Z"),
                allowed_actions=("read_repository",),
                max_jobs=10,
                max_session_seconds=3600,
            )
        )

        read_tool = StubTool(
            ToolOutcome(True, "scheduled read passed", ("ev-gate020-read",))
        )
        approval_tool = StubTool(ToolOutcome(True, "must never execute"))
        forbidden_tool = StubTool(ToolOutcome(True, "must never execute"))
        unlisted_tool = StubTool(ToolOutcome(True, "must never execute"))

        completed = ScheduledRunExecutor(
            supervisor=sup,
            store=schedules,
            tools={
                "read_repository": read_tool,
                "architecture_change": approval_tool,
                "validator_weakening": forbidden_tool,
                "run_validator": unlisted_tool,
            },
            clock=clock,
        ).run_next_due()

        assert completed is not None
        assert completed.event_type is ScheduleEventType.SESSION_COMPLETED
        assert completed.summary is not None
        summary = completed.summary

        assert summary.counts["PASS"] == 1
        assert summary.counts["WAITING_FOR_APPROVAL"] == 1
        assert summary.counts["BLOCKED"] == 2
        assert summary.evidence_refs == ("ev-gate020-read",)
        assert read_tool.calls == ["read_repository"]
        assert approval_tool.calls == []
        assert forbidden_tool.calls == []
        assert unlisted_tool.calls == []
        assert sup.persisted_job(job_id="gate020-interrupted").status == "BLOCKED"
        assert sup.persisted_job(job_id="gate020-approval").status == "WAITING_FOR_APPROVAL"
        assert sup.persisted_job(job_id="gate020-forbidden").status == "BLOCKED"
        assert sup.persisted_job(job_id="gate020-unlisted-auto").status == "QUEUED"

        schedule_integrity_before = schedules.verify_integrity(
            project_id="engineering-ai"
        )
        queue_integrity = queue.verify_integrity(project_id="engineering-ai")

        schedules.close()
        schedules = PersistedScheduledRunStore(schedule_path, clock=clock)
        completed_reopened = schedules.get(
            project_id="engineering-ai",
            schedule_id="gate020-overnight",
        )
        future_reopened = schedules.get(
            project_id="engineering-ai",
            schedule_id="gate020-future",
        )
        schedule_integrity_after = schedules.verify_integrity(
            project_id="engineering-ai"
        )

        assert completed_reopened.event_type is ScheduleEventType.SESSION_COMPLETED
        assert completed_reopened.summary is not None
        assert future_reopened.event_type is ScheduleEventType.SCHEDULED

        payload = {
            "gate": "020",
            "state": "PASS_SCHEDULED_UNATTENDED_RUN_SESSION",
            "schedule_database_created": True,
            "schedule_database_reopened": True,
            "due_schedule_executed": True,
            "future_schedule_remained_scheduled": True,
            "autonomous_allowed_final_state": sup.persisted_job(
                job_id="gate020-read"
            ).status,
            "approval_final_state": sup.persisted_job(
                job_id="gate020-approval"
            ).status,
            "forbidden_final_state": sup.persisted_job(
                job_id="gate020-forbidden"
            ).status,
            "unlisted_autonomous_final_state": sup.persisted_job(
                job_id="gate020-unlisted-auto"
            ).status,
            "interrupted_final_state": sup.persisted_job(
                job_id="gate020-interrupted"
            ).status,
            "summary_counts": dict(summary.counts),
            "summary_evidence_refs": list(summary.evidence_refs),
            "read_tool_calls": list(read_tool.calls),
            "approval_tool_calls": list(approval_tool.calls),
            "forbidden_tool_calls": list(forbidden_tool.calls),
            "unlisted_tool_calls": list(unlisted_tool.calls),
            "schedule_events_checked_before_reopen": schedule_integrity_before.events_checked,
            "schedule_events_checked_after_reopen": schedule_integrity_after.events_checked,
            "schedule_integrity": schedule_integrity_after.ok,
            "queue_events_checked": queue_integrity.events_checked,
            "queue_integrity": queue_integrity.ok,
            "automatic_approval": False,
            "os_scheduler_installation": False,
            "daemon_service": False,
            "distributed_workers": False,
            "physical_validation": "PHYSICAL_NOT_EXECUTED",
        }

        schedules.close()
        queue.close()

    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
