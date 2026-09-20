from __future__ import annotations

import itertools
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from engineering_ai.supervisor import (
    JobQueueConflictError,
    JobQueueIntegrityError,
    JobQueuePolicyError,
    PersistedJobQueue,
    QueueEventType,
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
        self.value = datetime(2026, 9, 20, 14, 0, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


class EventIdFactory:
    def __init__(self) -> None:
        self.counter = itertools.count(1)

    def __call__(self) -> str:
        return f"qevt-test-{next(self.counter):04d}"


def make_job(
    job_id: str,
    *,
    action: str = "read_repository",
    retry_limit: int = 2,
    project_id: str = "engineering-ai",
) -> dict:
    job = load_fixture("valid_job.json")
    job["job_id"] = job_id
    job["project_id"] = project_id
    job["gate_id"] = "019"
    job["objective"] = f"Persist and control {job_id}"
    job["scope"] = ["persisted queue"]
    job["out_of_scope"] = ["scheduled execution"]
    job["requested_actions"] = [action]
    job["required_validators"] = []
    job["retry_limit"] = retry_limit
    job["attempts"] = 0
    job["status"] = "QUEUED"
    job["blocker"] = None
    return job


def make_policy() -> dict:
    return load_fixture("valid_policy.json")


def make_state() -> dict:
    state = load_fixture("valid_state.json")
    state["current_gate"] = "019"
    state["active_job_id"] = None
    state["repository_ref"] = {
        "branch": "gate-019-persisted-job-queue",
        "head_sha": "0123456789abcdef0123456789abcdef01234567",
    }
    state["pending_checks"] = []
    state["blockers"] = []
    state["next_admissible_action"] = None
    return state


class PersistedJobQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "jobs.sqlite3"
        self.clock = MutableClock()
        self.ids = EventIdFactory()
        self.queue = PersistedJobQueue(
            self.path,
            clock=self.clock,
            event_id_factory=self.ids,
        )

    def tearDown(self) -> None:
        try:
            self.queue.close()
        except Exception:
            pass
        self.tmp.cleanup()

    def reopen(self) -> PersistedJobQueue:
        self.queue.close()
        self.queue = PersistedJobQueue(
            self.path,
            clock=self.clock,
            event_id_factory=self.ids,
        )
        return self.queue

    def test_enqueue_reopen_and_fifo_claim(self) -> None:
        first = self.queue.enqueue(make_job("job-first"), timeout_seconds=120)
        second = self.queue.enqueue(make_job("job-second"), timeout_seconds=120)
        validate_instance("job-queue-snapshot.schema.json", first.as_dict())
        validate_instance("job-queue-snapshot.schema.json", second.as_dict())

        self.reopen()
        current = self.queue.list_current(project_id="engineering-ai")
        self.assertEqual(
            tuple(item.job_id for item in current),
            ("job-first", "job-second"),
        )
        claimed = self.queue.claim_next(project_id="engineering-ai")
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(claimed.job_id, "job-first")
        self.assertEqual(claimed.status, "RUNNING")
        self.assertEqual(claimed.event_type, QueueEventType.RUN_STARTED)

    def test_retry_persists_and_reenters_at_fifo_tail(self) -> None:
        self.queue.enqueue(make_job("job-a"), timeout_seconds=120)
        self.queue.enqueue(make_job("job-b"), timeout_seconds=120)

        claimed = self.queue.claim_next(project_id="engineering-ai")
        assert claimed is not None
        retry = claimed.job_dict()
        retry["status"] = "QUEUED"
        retry["attempts"] = 1
        retry["blocker"] = "tool failure; retry available: synthetic"
        persisted = self.queue.persist_execution_result(
            project_id="engineering-ai",
            job_id="job-a",
            result_job=retry,
        )
        self.assertEqual(persisted.status, "QUEUED")
        self.assertEqual(persisted.attempts, 1)

        self.reopen()
        claimed_second = self.queue.claim_next(project_id="engineering-ai")
        assert claimed_second is not None
        self.assertEqual(claimed_second.job_id, "job-b")
        a = self.queue.get(project_id="engineering-ai", job_id="job-a")
        self.assertEqual(a.attempts, 1)

    def test_retry_attempt_must_increment_exactly_once(self) -> None:
        self.queue.enqueue(make_job("job-retry"), timeout_seconds=120)
        claimed = self.queue.claim_next(project_id="engineering-ai")
        assert claimed is not None

        bad = claimed.job_dict()
        bad["status"] = "QUEUED"
        bad["attempts"] = 2
        with self.assertRaises(JobQueuePolicyError):
            self.queue.persist_execution_result(
                project_id="engineering-ai",
                job_id="job-retry",
                result_job=bad,
            )

    def test_execution_result_cannot_expand_scope_or_permissions(self) -> None:
        self.queue.enqueue(make_job("job-scope"), timeout_seconds=120)
        claimed = self.queue.claim_next(project_id="engineering-ai")
        assert claimed is not None

        bad = claimed.job_dict()
        bad["status"] = "PASS"
        bad["requested_actions"].append("architecture_change")
        with self.assertRaises(JobQueuePolicyError):
            self.queue.persist_execution_result(
                project_id="engineering-ai",
                job_id="job-scope",
                result_job=bad,
            )

    def test_waiting_for_approval_survives_reopen_and_is_not_auto_claimed(self) -> None:
        supervisor = Supervisor(
            policy=make_policy(),
            state=make_state(),
            job_queue=self.queue,
        )
        supervisor.enqueue_persisted_job(
            make_job("job-approval", action="architecture_change"),
            timeout_seconds=120,
        )
        claimed = supervisor.claim_next_persisted_job()
        assert claimed is not None

        tool = StubTool(ToolOutcome(True, "approved action would execute"))
        waiting = supervisor.execute(
            job=claimed.job_dict(),
            action="architecture_change",
            tool=tool,
        )
        self.assertEqual(waiting.job["status"], "WAITING_FOR_APPROVAL")
        supervisor.persist_persisted_job_result(
            job_id="job-approval",
            result_job=waiting.job,
        )
        self.assertEqual(tool.calls, [])

        self.reopen()
        resumed_supervisor = Supervisor(
            policy=make_policy(),
            state=make_state(),
            job_queue=self.queue,
        )
        self.assertIsNone(resumed_supervisor.claim_next_persisted_job())
        persisted = resumed_supervisor.persisted_job(job_id="job-approval")
        self.assertEqual(persisted.status, "WAITING_FOR_APPROVAL")

        approved_claim = resumed_supervisor.claim_approved_persisted_job(
            job_id="job-approval",
            action="architecture_change",
            approver="human-owner",
        )
        self.assertEqual(approved_claim.status, "RUNNING")
        approved = resumed_supervisor.execute(
            job=approved_claim.job_dict(),
            action="architecture_change",
            tool=tool,
            approval_obtained=True,
            approver="human-owner",
        )
        final = resumed_supervisor.persist_persisted_job_result(
            job_id="job-approval",
            result_job=approved.job,
        )
        self.assertEqual(final.status, "PASS")
        self.assertEqual(tool.calls, ["architecture_change"])

    def test_approval_resume_requires_matching_waiting_action(self) -> None:
        supervisor = Supervisor(
            policy=make_policy(),
            state=make_state(),
            job_queue=self.queue,
        )
        supervisor.enqueue_persisted_job(
            make_job("job-approval", action="architecture_change")
        )
        claimed = supervisor.claim_next_persisted_job()
        assert claimed is not None
        waiting = supervisor.execute(
            job=claimed.job_dict(),
            action="architecture_change",
            tool=StubTool(ToolOutcome(True, "unused")),
        )
        supervisor.persist_persisted_job_result(
            job_id="job-approval",
            result_job=waiting.job,
        )

        with self.assertRaises(Exception):
            supervisor.claim_approved_persisted_job(
                job_id="job-approval",
                action="physics_change",
                approver="human-owner",
            )

    def test_interrupted_running_job_recovers_blocked_not_queued(self) -> None:
        self.queue.enqueue(make_job("job-interrupted"), timeout_seconds=120)
        claimed = self.queue.claim_next(project_id="engineering-ai")
        assert claimed is not None
        self.assertEqual(claimed.status, "RUNNING")

        self.reopen()
        recovered = self.queue.recover_interrupted_runs(
            project_id="engineering-ai"
        )
        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0].status, "BLOCKED")
        self.assertEqual(
            recovered[0].event_type,
            QueueEventType.INTERRUPTED_RECOVERY,
        )
        self.assertIsNone(self.queue.claim_next(project_id="engineering-ai"))

    def test_expired_deadline_blocks_late_pass(self) -> None:
        self.queue.enqueue(make_job("job-timeout"), timeout_seconds=10)
        claimed = self.queue.claim_next(project_id="engineering-ai")
        assert claimed is not None
        late = claimed.job_dict()
        late["status"] = "PASS"
        self.clock.advance(10)
        persisted = self.queue.persist_execution_result(
            project_id="engineering-ai",
            job_id="job-timeout",
            result_job=late,
        )
        self.assertEqual(persisted.status, "BLOCKED")
        self.assertEqual(persisted.event_type, QueueEventType.TIMEOUT_RECOVERY)
        self.assertIn("deadline expired", persisted.reason or "")

    def test_expired_running_job_can_be_recovered_without_result(self) -> None:
        self.queue.enqueue(make_job("job-expired"), timeout_seconds=5)
        claimed = self.queue.claim_next(project_id="engineering-ai")
        assert claimed is not None
        self.clock.advance(6)
        recovered = self.queue.recover_expired_runs(project_id="engineering-ai")
        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0].status, "BLOCKED")
        self.assertEqual(recovered[0].event_type, QueueEventType.TIMEOUT_RECOVERY)

    def test_terminal_jobs_remain_terminal_and_unclaimable(self) -> None:
        self.queue.enqueue(make_job("job-terminal"), timeout_seconds=120)
        claimed = self.queue.claim_next(project_id="engineering-ai")
        assert claimed is not None
        passed = claimed.job_dict()
        passed["status"] = "PASS"
        final = self.queue.persist_execution_result(
            project_id="engineering-ai",
            job_id="job-terminal",
            result_job=passed,
        )
        self.assertEqual(final.status, "PASS")
        self.assertIsNone(self.queue.claim_next(project_id="engineering-ai"))
        with self.assertRaises(JobQueuePolicyError):
            self.queue.begin_run(
                project_id="engineering-ai",
                job_id="job-terminal",
            )

    def test_project_isolation(self) -> None:
        self.queue.enqueue(make_job("shared-job", project_id="engineering-ai"))
        self.queue.enqueue(make_job("shared-job", project_id="buoycalc"))
        one = self.queue.list_current(project_id="engineering-ai")
        two = self.queue.list_current(project_id="buoycalc")
        self.assertEqual(tuple(x.project_id for x in one), ("engineering-ai",))
        self.assertEqual(tuple(x.project_id for x in two), ("buoycalc",))

    def test_duplicate_job_id_within_project_rejected(self) -> None:
        self.queue.enqueue(make_job("duplicate-job"))
        with self.assertRaises(JobQueueConflictError):
            self.queue.enqueue(make_job("duplicate-job"))

    def test_tampered_latest_event_fails_closed(self) -> None:
        self.queue.enqueue(make_job("job-tamper"))
        self.queue.close()
        conn = sqlite3.connect(self.path)
        try:
            conn.execute("DROP TRIGGER job_queue_events_no_update")
            conn.execute(
                """
                UPDATE job_queue_events
                SET job_json = replace(job_json, 'Persist and control', 'tampered')
                WHERE job_id = 'job-tamper'
                """
            )
            conn.commit()
        finally:
            conn.close()

        self.queue = PersistedJobQueue(
            self.path,
            clock=self.clock,
            event_id_factory=self.ids,
        )
        with self.assertRaises(JobQueueIntegrityError):
            self.queue.get(
                project_id="engineering-ai",
                job_id="job-tamper",
            )

    def test_history_chain_and_integrity_report(self) -> None:
        self.queue.enqueue(make_job("job-history"), timeout_seconds=120)
        claimed = self.queue.claim_next(project_id="engineering-ai")
        assert claimed is not None
        passed = claimed.job_dict()
        passed["status"] = "PASS"
        self.queue.persist_execution_result(
            project_id="engineering-ai",
            job_id="job-history",
            result_job=passed,
        )
        history = self.queue.history(
            project_id="engineering-ai",
            job_id="job-history",
        )
        self.assertEqual(
            tuple(item.event_type for item in history),
            (
                QueueEventType.ENQUEUED,
                QueueEventType.RUN_STARTED,
                QueueEventType.EXECUTION_RESULT,
            ),
        )
        report = self.queue.verify_integrity(project_id="engineering-ai")
        self.assertTrue(report.ok)
        self.assertEqual(report.events_checked, 3)
        self.assertEqual(report.jobs_checked, 1)

    def test_queue_exposes_no_execution_or_scheduling_surface(self) -> None:
        for name in (
            "execute",
            "run_tool",
            "schedule",
            "schedule_at",
            "approve",
            "grant_approval",
            "run_daemon",
        ):
            self.assertFalse(hasattr(self.queue, name))


if __name__ == "__main__":
    unittest.main()
