from __future__ import annotations

import json
import tempfile
from pathlib import Path

from engineering_ai.supervisor import (
    PersistedJobQueue,
    StubTool,
    Supervisor,
    ToolOutcome,
)


def policy() -> dict:
    return {
        "schema_version": "1.0",
        "policy_version": "gate019-smoke",
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
        "current_gate": "019",
        "active_job_id": None,
        "repository_ref": {
            "branch": "gate-019-persisted-job-queue",
            "head_sha": "0123456789abcdef0123456789abcdef01234567",
        },
        "architecture_baseline": "Gate 018 accepted knowledge lifecycle",
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
        "gate_id": "019",
        "objective": f"Gate 019 smoke {job_id}",
        "scope": ["persisted local queue"],
        "out_of_scope": ["scheduled execution", "automatic approval"],
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
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "gate019-jobs.sqlite3"

        queue = PersistedJobQueue(db)
        first = supervisor(queue)
        first.enqueue_persisted_job(job("gate019-retry", "read_repository"))
        first.enqueue_persisted_job(job("gate019-approval", "architecture_change"))

        retry_claim = first.claim_next_persisted_job()
        assert retry_claim is not None
        retry_fail = first.execute(
            job=retry_claim.job_dict(),
            action="read_repository",
            tool=StubTool(ToolOutcome(False, "synthetic retry evidence")),
        )
        retry_persisted = first.persist_persisted_job_result(
            job_id="gate019-retry",
            result_job=retry_fail.job,
        )
        assert retry_persisted.status == "QUEUED"
        assert retry_persisted.attempts == 1

        approval_claim = first.claim_next_persisted_job()
        assert approval_claim is not None
        approval_wait = first.execute(
            job=approval_claim.job_dict(),
            action="architecture_change",
            tool=StubTool(ToolOutcome(True, "must wait for approval")),
        )
        waiting = first.persist_persisted_job_result(
            job_id="gate019-approval",
            result_job=approval_wait.job,
        )
        assert waiting.status == "WAITING_FOR_APPROVAL"
        queue.close()

        queue = PersistedJobQueue(db)
        reopened = supervisor(queue)
        retry_after_reopen = reopened.persisted_job(job_id="gate019-retry")
        waiting_after_reopen = reopened.persisted_job(job_id="gate019-approval")
        assert retry_after_reopen.status == "QUEUED"
        assert retry_after_reopen.attempts == 1
        assert waiting_after_reopen.status == "WAITING_FOR_APPROVAL"

        retry_claim_2 = reopened.claim_next_persisted_job()
        assert retry_claim_2 is not None
        assert retry_claim_2.job_id == "gate019-retry"
        retry_pass = reopened.execute(
            job=retry_claim_2.job_dict(),
            action="read_repository",
            tool=StubTool(ToolOutcome(True, "retry succeeded", ("ev-retry-pass",))),
        )
        retry_final = reopened.persist_persisted_job_result(
            job_id="gate019-retry",
            result_job=retry_pass.job,
        )
        assert retry_final.status == "PASS"

        approved_claim = reopened.claim_approved_persisted_job(
            job_id="gate019-approval",
            action="architecture_change",
            approver="human-owner",
        )
        approval_pass = reopened.execute(
            job=approved_claim.job_dict(),
            action="architecture_change",
            tool=StubTool(
                ToolOutcome(True, "explicitly approved", ("ev-approval-pass",))
            ),
            approval_obtained=True,
            approver="human-owner",
        )
        approval_final = reopened.persist_persisted_job_result(
            job_id="gate019-approval",
            result_job=approval_pass.job,
        )
        assert approval_final.status == "PASS"

        reopened.enqueue_persisted_job(
            job("gate019-interrupted", "read_repository")
        )
        interrupted_claim = reopened.claim_next_persisted_job()
        assert interrupted_claim is not None
        assert interrupted_claim.status == "RUNNING"
        queue.close()

        queue = PersistedJobQueue(db)
        recovered_supervisor = supervisor(queue)
        recovered = recovered_supervisor.recover_interrupted_persisted_jobs()
        assert len(recovered) == 1
        assert recovered[0].job_id == "gate019-interrupted"
        assert recovered[0].status == "BLOCKED"

        integrity = queue.verify_integrity(project_id="engineering-ai")
        current = recovered_supervisor.persisted_jobs()
        current_states = {item.job_id: item.status for item in current}
        queue.close()

        payload = {
            "gate": "019",
            "state": "PASS_PERSISTED_JOB_QUEUE_REOPEN_RECOVERY",
            "database_created": True,
            "database_reopened": True,
            "fifo_retry_tail_preserved": True,
            "retry_attempts_preserved": retry_after_reopen.attempts,
            "retry_final_state": retry_final.status,
            "approval_wait_survived_reopen": waiting_after_reopen.status
            == "WAITING_FOR_APPROVAL",
            "approval_final_state": approval_final.status,
            "interrupted_run_recovery": recovered[0].event_type.value,
            "interrupted_final_state": recovered[0].status,
            "current_states": current_states,
            "queue_events_checked": integrity.events_checked,
            "queue_jobs_checked": integrity.jobs_checked,
            "queue_integrity": integrity.ok,
            "automatic_approval": False,
            "scheduled_execution": False,
            "distributed_workers": False,
            "physical_validation": "PHYSICAL_NOT_EXECUTED",
        }

    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
