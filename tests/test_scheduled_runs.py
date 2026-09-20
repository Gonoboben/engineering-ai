from __future__ import annotations

import itertools
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from engineering_ai.supervisor import (
    PersistedJobQueue,
    PersistedScheduledRunStore,
    ScheduleEventType,
    ScheduledRunConflictError,
    ScheduledRunDefinition,
    ScheduledRunExecutor,
    ScheduledRunIntegrityError,
    StubTool,
    Supervisor,
    ToolOutcome,
)
from engineering_ai.validation import validate_instance


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def load_fixture(name: str) -> dict:
    with (FIXTURES / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class MutableClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 9, 20, 22, 0, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


class IdFactory:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.counter = itertools.count(1)

    def __call__(self) -> str:
        return f"{self.prefix}-{next(self.counter):04d}"


def make_policy() -> dict:
    return load_fixture("valid_policy.json")


def make_state() -> dict:
    state = load_fixture("valid_state.json")
    state["current_gate"] = "020"
    state["active_job_id"] = None
    state["repository_ref"] = {
        "branch": "gate-020-scheduled-overnight-runs",
        "head_sha": "0123456789abcdef0123456789abcdef01234567",
    }
    state["pending_checks"] = []
    state["blockers"] = []
    state["next_admissible_action"] = None
    return state


def make_job(
    job_id: str,
    action: str | tuple[str, ...] = "read_repository",
    *,
    retry_limit: int = 2,
) -> dict:
    job = load_fixture("valid_job.json")
    job["job_id"] = job_id
    job["gate_id"] = "020"
    job["objective"] = f"Scheduled run test {job_id}"
    job["scope"] = ["bounded unattended run"]
    job["out_of_scope"] = ["automatic approval", "OS scheduler installation"]
    job["requested_actions"] = (
        list(action) if isinstance(action, tuple) else [action]
    )
    job["required_validators"] = []
    job["retry_limit"] = retry_limit
    job["attempts"] = 0
    job["status"] = "QUEUED"
    job["blocker"] = None
    return job


def definition(
    schedule_id: str,
    clock: MutableClock,
    *,
    due_offset_seconds: int = 0,
    allowed_actions: tuple[str, ...] = ("read_repository",),
    max_jobs: int = 10,
    max_session_seconds: int = 3600,
) -> ScheduledRunDefinition:
    return ScheduledRunDefinition(
        schedule_id=schedule_id,
        project_id="engineering-ai",
        due_at=(
            clock.value + timedelta(seconds=due_offset_seconds)
        ).isoformat().replace("+00:00", "Z"),
        allowed_actions=allowed_actions,
        max_jobs=max_jobs,
        max_session_seconds=max_session_seconds,
    )


class ScheduledRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.clock = MutableClock()
        self.queue_ids = IdFactory("qevt")
        self.schedule_ids = IdFactory("sevt")
        self.session_ids = IdFactory("session")
        self.queue = PersistedJobQueue(
            root / "jobs.sqlite3",
            clock=self.clock,
            event_id_factory=self.queue_ids,
        )
        self.store = PersistedScheduledRunStore(
            root / "schedules.sqlite3",
            clock=self.clock,
            event_id_factory=self.schedule_ids,
            session_id_factory=self.session_ids,
        )
        self.supervisor = Supervisor(
            policy=make_policy(),
            state=make_state(),
            job_queue=self.queue,
        )

    def tearDown(self) -> None:
        try:
            self.queue.close()
        except Exception:
            pass
        try:
            self.store.close()
        except Exception:
            pass
        self.tmp.cleanup()

    def executor(self, tools: dict | None = None) -> ScheduledRunExecutor:
        return ScheduledRunExecutor(
            supervisor=self.supervisor,
            store=self.store,
            tools=tools or {},
            clock=self.clock,
        )

    def enqueue(self, job: dict) -> None:
        self.supervisor.enqueue_persisted_job(job, timeout_seconds=300)

    def test_schedule_persists_and_not_due_never_runs(self) -> None:
        snap = self.store.schedule(
            definition("schedule-future", self.clock, due_offset_seconds=60)
        )
        validate_instance("scheduled-run-snapshot.schema.json", snap.as_dict())
        self.enqueue(make_job("job-future"))
        tool = StubTool(ToolOutcome(True, "must not run"))

        result = self.executor({"read_repository": tool}).run_next_due()

        self.assertIsNone(result)
        self.assertEqual(tool.calls, [])
        self.assertEqual(
            self.supervisor.persisted_job(job_id="job-future").status,
            "QUEUED",
        )

        self.store.close()
        self.store = PersistedScheduledRunStore(
            Path(self.tmp.name) / "schedules.sqlite3",
            clock=self.clock,
            event_id_factory=self.schedule_ids,
            session_id_factory=self.session_ids,
        )
        self.assertIsNone(self.store.next_due(project_id="engineering-ai"))
        self.clock.advance(60)
        self.assertEqual(
            self.store.next_due(project_id="engineering-ai").schedule_id,
            "schedule-future",
        )

    def test_due_order_is_due_time_then_append_sequence(self) -> None:
        self.store.schedule(
            definition("schedule-later", self.clock, due_offset_seconds=-10)
        )
        self.store.schedule(
            definition("schedule-earlier", self.clock, due_offset_seconds=-20)
        )
        self.store.schedule(
            definition("schedule-same", self.clock, due_offset_seconds=-20)
        )
        due = self.store.next_due(project_id="engineering-ai")
        self.assertEqual(due.schedule_id, "schedule-earlier")

    def test_unattended_run_executes_only_policy_allow_and_schedule_allowed(self) -> None:
        read_tool = StubTool(
            ToolOutcome(True, "repository inspected", ("ev-read",))
        )
        approval_tool = StubTool(ToolOutcome(True, "must never execute"))
        forbidden_tool = StubTool(ToolOutcome(True, "must never execute"))
        validator_tool = StubTool(ToolOutcome(True, "not pre-authorized"))

        self.enqueue(make_job("job-read", "read_repository"))
        self.enqueue(make_job("job-approval", "architecture_change"))
        self.enqueue(make_job("job-forbidden", "validator_weakening"))
        self.enqueue(make_job("job-unlisted-auto", "run_validator"))
        self.store.schedule(
            definition(
                "schedule-night",
                self.clock,
                allowed_actions=(
                    "read_repository",
                    "architecture_change",
                    "validator_weakening",
                ),
            )
        )

        completed = self.executor(
            {
                "read_repository": read_tool,
                "architecture_change": approval_tool,
                "validator_weakening": forbidden_tool,
                "run_validator": validator_tool,
            }
        ).run_next_due()

        self.assertIsNotNone(completed)
        assert completed is not None
        self.assertEqual(completed.event_type, ScheduleEventType.SESSION_COMPLETED)
        summary = completed.summary
        assert summary is not None
        validate_instance("scheduled-run-snapshot.schema.json", completed.as_dict())
        self.assertEqual(summary.counts["PASS"], 1)
        self.assertEqual(summary.counts["WAITING_FOR_APPROVAL"], 1)
        self.assertEqual(summary.counts["BLOCKED"], 1)
        self.assertEqual(summary.counts["QUEUED"], 0)
        self.assertEqual(summary.evidence_refs, ("ev-read",))
        self.assertEqual(read_tool.calls, ["read_repository"])
        self.assertEqual(approval_tool.calls, [])
        self.assertEqual(forbidden_tool.calls, [])
        self.assertEqual(validator_tool.calls, [])
        self.assertEqual(
            self.supervisor.persisted_job(job_id="job-unlisted-auto").status,
            "QUEUED",
        )
        self.assertEqual(
            self.supervisor.persisted_job(job_id="job-approval").status,
            "WAITING_FOR_APPROVAL",
        )
        self.assertEqual(
            self.supervisor.persisted_job(job_id="job-forbidden").status,
            "BLOCKED",
        )

    def test_schedule_allowed_actions_do_not_grant_approval(self) -> None:
        tool = StubTool(ToolOutcome(True, "must not execute"))
        self.enqueue(make_job("job-approval", "architecture_change"))
        self.store.schedule(
            definition(
                "schedule-approval",
                self.clock,
                allowed_actions=("architecture_change",),
            )
        )
        completed = self.executor({"architecture_change": tool}).run_next_due()
        assert completed is not None and completed.summary is not None
        self.assertEqual(completed.summary.counts["WAITING_FOR_APPROVAL"], 1)
        self.assertEqual(tool.calls, [])

    def test_max_jobs_stops_before_second_claim(self) -> None:
        self.enqueue(make_job("job-one"))
        self.enqueue(make_job("job-two"))
        tool = StubTool(ToolOutcome(True, "ok"))
        self.store.schedule(
            definition("schedule-one-job", self.clock, max_jobs=1)
        )

        completed = self.executor({"read_repository": tool}).run_next_due()
        assert completed is not None and completed.summary is not None
        self.assertEqual(completed.summary.stop_reason, "MAX_JOBS_REACHED")
        self.assertEqual(completed.summary.claims, 1)
        self.assertEqual(
            self.supervisor.persisted_job(job_id="job-one").status,
            "PASS",
        )
        self.assertEqual(
            self.supervisor.persisted_job(job_id="job-two").status,
            "QUEUED",
        )

    def test_max_session_seconds_stops_additional_claims(self) -> None:
        self.enqueue(make_job("job-one"))
        self.enqueue(make_job("job-two"))

        class AdvancingTool:
            def __call__(inner_self, action: str) -> ToolOutcome:
                self.clock.advance(5)
                return ToolOutcome(True, "ok")

        self.store.schedule(
            definition(
                "schedule-short",
                self.clock,
                max_jobs=10,
                max_session_seconds=5,
            )
        )
        completed = self.executor(
            {"read_repository": AdvancingTool()}
        ).run_next_due()
        assert completed is not None and completed.summary is not None
        self.assertEqual(
            completed.summary.stop_reason,
            "MAX_SESSION_SECONDS_REACHED",
        )
        self.assertEqual(completed.summary.claims, 1)
        self.assertEqual(
            self.supervisor.persisted_job(job_id="job-two").status,
            "QUEUED",
        )

    def test_interrupted_queue_job_recovers_blocked_before_new_work(self) -> None:
        self.enqueue(make_job("job-interrupted"))
        self.enqueue(make_job("job-new"))
        interrupted = self.supervisor.claim_persisted_job(
            job_id="job-interrupted"
        )
        self.assertEqual(interrupted.status, "RUNNING")
        self.store.schedule(definition("schedule-recover", self.clock))

        completed = self.executor(
            {"read_repository": StubTool(ToolOutcome(True, "ok"))}
        ).run_next_due()
        assert completed is not None and completed.summary is not None
        self.assertEqual(
            completed.summary.recovered_interrupted_job_ids,
            ("job-interrupted",),
        )
        self.assertEqual(completed.summary.counts["BLOCKED"], 1)
        self.assertEqual(completed.summary.counts["PASS"], 1)
        self.assertEqual(
            self.supervisor.persisted_job(job_id="job-interrupted").status,
            "BLOCKED",
        )

    def test_interrupted_schedule_session_recovers_blocked_and_is_not_rerun(self) -> None:
        self.store.schedule(definition("schedule-crash", self.clock))
        started = self.store.start_next_due(project_id="engineering-ai")
        self.assertEqual(started.event_type, ScheduleEventType.SESSION_STARTED)

        result = self.executor().run_next_due()

        self.assertIsNone(result)
        latest = self.store.get(
            project_id="engineering-ai",
            schedule_id="schedule-crash",
        )
        self.assertEqual(latest.event_type, ScheduleEventType.SESSION_BLOCKED)
        self.assertIn("process restart", latest.reason or "")

    def test_multi_action_job_is_blocked_without_tool(self) -> None:
        self.enqueue(
            make_job(
                "job-multi",
                ("read_repository", "run_validator"),
            )
        )
        tool = StubTool(ToolOutcome(True, "must not execute"))
        self.store.schedule(
            definition(
                "schedule-multi",
                self.clock,
                allowed_actions=("read_repository", "run_validator"),
            )
        )
        completed = self.executor(
            {"read_repository": tool, "run_validator": tool}
        ).run_next_due()
        assert completed is not None and completed.summary is not None
        self.assertEqual(completed.summary.counts["BLOCKED"], 1)
        self.assertEqual(tool.calls, [])

    def test_missing_pre_authorized_tool_blocks_job(self) -> None:
        self.enqueue(make_job("job-missing-tool"))
        self.store.schedule(definition("schedule-missing-tool", self.clock))
        completed = self.executor().run_next_due()
        assert completed is not None and completed.summary is not None
        self.assertEqual(completed.summary.counts["BLOCKED"], 1)
        self.assertIn(
            "tool is unavailable",
            self.supervisor.persisted_job(
                job_id="job-missing-tool"
            ).job_dict()["blocker"],
        )

    def test_tool_exception_is_bounded_by_existing_retry_semantics(self) -> None:
        self.enqueue(make_job("job-tool-error", retry_limit=2))

        class RaisingTool:
            def __call__(self, action: str) -> ToolOutcome:
                raise RuntimeError("synthetic")

        self.store.schedule(
            definition(
                "schedule-tool-error",
                self.clock,
                max_jobs=1,
            )
        )
        completed = self.executor(
            {"read_repository": RaisingTool()}
        ).run_next_due()
        assert completed is not None and completed.summary is not None
        current = self.supervisor.persisted_job(job_id="job-tool-error")
        self.assertEqual(current.status, "QUEUED")
        self.assertEqual(current.attempts, 1)
        self.assertEqual(completed.summary.counts["QUEUED"], 1)
        self.assertEqual(completed.summary.stop_reason, "MAX_JOBS_REACHED")

    def test_cancelled_schedule_never_runs(self) -> None:
        self.store.schedule(definition("schedule-cancel", self.clock))
        self.store.cancel(
            project_id="engineering-ai",
            schedule_id="schedule-cancel",
            reason="operator cancelled",
        )
        self.enqueue(make_job("job-cancel"))
        tool = StubTool(ToolOutcome(True, "must not run"))
        self.assertIsNone(
            self.executor({"read_repository": tool}).run_next_due()
        )
        self.assertEqual(tool.calls, [])

    def test_duplicate_schedule_rejected(self) -> None:
        spec = definition("schedule-duplicate", self.clock)
        self.store.schedule(spec)
        with self.assertRaises(ScheduledRunConflictError):
            self.store.schedule(spec)

    def test_schedule_store_tamper_fails_closed(self) -> None:
        self.store.schedule(definition("schedule-tamper", self.clock))
        self.store.close()
        db = Path(self.tmp.name) / "schedules.sqlite3"
        conn = sqlite3.connect(db)
        try:
            conn.execute("DROP TRIGGER scheduled_run_no_update")
            conn.execute(
                """
                UPDATE scheduled_run_events
                SET definition_json = replace(
                    definition_json,
                    'read_repository',
                    'architecture_change'
                )
                WHERE schedule_id = 'schedule-tamper'
                """
            )
            conn.commit()
        finally:
            conn.close()
        self.store = PersistedScheduledRunStore(
            db,
            clock=self.clock,
            event_id_factory=self.schedule_ids,
            session_id_factory=self.session_ids,
        )
        with self.assertRaises(ScheduledRunIntegrityError):
            self.store.list_current(project_id="engineering-ai")

    def test_gate020_smoke_script(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/gate020_scheduled_run_smoke.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate"], "020")
        self.assertEqual(
            payload["state"],
            "PASS_SCHEDULED_UNATTENDED_RUN_SESSION",
        )
        self.assertTrue(payload["schedule_database_reopened"])
        self.assertTrue(payload["due_schedule_executed"])
        self.assertTrue(payload["future_schedule_remained_scheduled"])
        self.assertEqual(payload["autonomous_allowed_final_state"], "PASS")
        self.assertEqual(
            payload["approval_final_state"],
            "WAITING_FOR_APPROVAL",
        )
        self.assertEqual(payload["forbidden_final_state"], "BLOCKED")
        self.assertEqual(payload["unlisted_autonomous_final_state"], "QUEUED")
        self.assertEqual(payload["interrupted_final_state"], "BLOCKED")
        self.assertTrue(payload["schedule_integrity"])
        self.assertTrue(payload["queue_integrity"])
        self.assertEqual(payload["approval_tool_calls"], [])
        self.assertEqual(payload["forbidden_tool_calls"], [])
        self.assertEqual(payload["unlisted_tool_calls"], [])
        self.assertFalse(payload["automatic_approval"])
        self.assertFalse(payload["os_scheduler_installation"])
        self.assertFalse(payload["daemon_service"])
        self.assertEqual(
            payload["physical_validation"],
            "PHYSICAL_NOT_EXECUTED",
        )

    def test_integrity_report_and_no_os_scheduler_surface(self) -> None:
        self.store.schedule(definition("schedule-integrity", self.clock))
        report = self.store.verify_integrity(project_id="engineering-ai")
        self.assertTrue(report.ok)
        self.assertEqual(report.events_checked, 1)
        self.assertEqual(report.schedules_checked, 1)
        for name in (
            "install_service",
            "install_task_scheduler",
            "create_windows_task",
            "run_daemon",
            "grant_approval",
        ):
            self.assertFalse(hasattr(self.store, name))


if __name__ == "__main__":
    unittest.main()
