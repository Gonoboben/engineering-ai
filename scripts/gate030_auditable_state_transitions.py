from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_checked(args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr or result.stdout or "no output"
        raise RuntimeError(f"command failed: {args!r}\n{detail}")
    return result


def run_test_module(pattern: str) -> None:
    run_checked(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            pattern,
        ]
    )


def run_json_smoke(path: str) -> dict:
    result = run_checked([sys.executable, path])
    return json.loads(result.stdout)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    modules = (
        "test_supervisor.py",
        "test_memory.py",
        "test_knowledge_lifecycle.py",
        "test_job_queue.py",
        "test_scheduled_runs.py",
        "test_external_review.py",
        "test_tool_bridge.py",
    )
    for pattern in modules:
        run_test_module(pattern)

    gate018 = run_json_smoke("scripts/gate018_knowledge_lifecycle_smoke.py")
    gate019 = run_json_smoke("scripts/gate019_job_queue_smoke.py")
    gate020 = run_json_smoke("scripts/gate020_scheduled_run_smoke.py")
    gate021 = run_json_smoke("scripts/gate021_external_review_smoke.py")
    gate022 = run_json_smoke("scripts/gate022_controlled_tool_smoke.py")

    require(
        gate018["state"] == "PASS_APPEND_ONLY_KNOWLEDGE_LIFECYCLE",
        "knowledge lifecycle acceptance did not pass",
    )
    require(
        gate018["history_revisions"] == [1, 2, 3, 4],
        "knowledge lifecycle history was not append-only",
    )
    require(
        gate018["stale_state"] == "STALE_SOURCE_REVISION",
        "source revision drift was not detected as stale",
    )
    require(
        gate018["final_state"] == "INVALIDATED",
        "stale accepted knowledge was not invalidated",
    )
    require(
        gate018["memory_integrity"] and gate018["lifecycle_integrity"],
        "memory/lifecycle integrity check failed",
    )
    require(
        not gate018["physical_validation_inferred"],
        "knowledge lifecycle inferred physical validation",
    )

    require(
        gate019["state"] == "PASS_PERSISTED_JOB_QUEUE_REOPEN_RECOVERY",
        "persisted job queue acceptance did not pass",
    )
    require(gate019["database_reopened"], "job queue was not reopened")
    require(gate019["queue_integrity"], "job queue integrity failed")
    require(
        gate019["approval_wait_survived_reopen"],
        "WAITING_FOR_APPROVAL did not survive reopen",
    )
    require(
        gate019["interrupted_final_state"] == "BLOCKED",
        "interrupted RUNNING job did not recover fail-closed",
    )
    require(
        not gate019["automatic_approval"],
        "job queue reported automatic approval",
    )

    require(
        gate020["state"] == "PASS_SCHEDULED_UNATTENDED_RUN_SESSION",
        "scheduled run acceptance did not pass",
    )
    require(
        gate020["schedule_database_reopened"],
        "schedule store was not reopened",
    )
    require(
        gate020["schedule_integrity"] and gate020["queue_integrity"],
        "scheduled-run or queue integrity failed",
    )
    require(
        gate020["approval_final_state"] == "WAITING_FOR_APPROVAL",
        "scheduled approval boundary was not preserved",
    )
    require(
        gate020["forbidden_final_state"] == "BLOCKED",
        "scheduled forbidden action did not remain blocked",
    )
    require(
        gate020["approval_tool_calls"] == [],
        "approval-gated scheduled tool executed before approval",
    )
    require(
        gate020["forbidden_tool_calls"] == [],
        "forbidden scheduled tool executed",
    )
    require(
        not gate020["automatic_approval"],
        "scheduled execution reported automatic approval",
    )

    require(
        gate021["state"] == "PASS_CONTROLLED_EXTERNAL_REVIEW_BOUNDARY",
        "external review acceptance did not pass",
    )
    require(
        gate021["ledger_database_reopened"] and gate021["ledger_integrity"],
        "external review ledger did not preserve reopen integrity",
    )
    require(
        gate021["unapproved_status"] == "NEEDS_HUMAN_APPROVAL",
        "external review approval state was not preserved",
    )
    require(
        not gate021["unapproved_provider_called"],
        "external provider executed before approval",
    )
    require(
        not gate021["automatic_external_approval"],
        "external review reported automatic approval",
    )

    require(
        gate022["state"] == "PASS_CONTROLLED_REGISTERED_TOOL_EXPOSURE",
        "controlled tool bridge acceptance did not pass",
    )
    require(
        gate022["ledger_database_reopened"] and gate022["ledger_integrity"],
        "controlled tool ledger did not preserve reopen integrity",
    )
    require(
        gate022["approval_missing_status"] == "NEEDS_HUMAN_APPROVAL",
        "tool bridge approval transition was not preserved",
    )
    require(
        not gate022["approval_missing_handler_called"],
        "tool handler executed before approval",
    )
    require(
        gate022["forbidden_status"] == "BLOCKED"
        and not gate022["forbidden_handler_called"],
        "forbidden tool invocation did not remain fail-closed",
    )
    require(
        not gate022["automatic_approval"],
        "tool bridge reported automatic approval",
    )

    payload = {
        "gate": "030",
        "state": "PASS_V1_0_AUDITABLE_STATE_TRANSITIONS",
        "acceptance_basis": {
            "supervisor_audit_module": True,
            "memory_module": True,
            "knowledge_lifecycle_module": True,
            "persisted_job_queue_module": True,
            "scheduled_run_module": True,
            "external_review_module": True,
            "controlled_tool_bridge_module": True,
            "knowledge_lifecycle_smoke": gate018["state"],
            "job_queue_smoke": gate019["state"],
            "scheduled_run_smoke": gate020["state"],
            "external_review_smoke": gate021["state"],
            "controlled_tool_smoke": gate022["state"],
        },
        "assertions": {
            "supervisor_transitions_audited": True,
            "approval_blocked_transition_does_not_advance": True,
            "forbidden_transition_does_not_advance": True,
            "memory_history_append_only": True,
            "knowledge_source_drift_detected": True,
            "knowledge_stale_acceptance_invalidated": True,
            "job_queue_reopen_integrity": True,
            "waiting_for_approval_persists": True,
            "interrupted_run_recovers_fail_closed": True,
            "scheduled_run_reopen_integrity": True,
            "external_review_ledger_reopen_integrity": True,
            "controlled_tool_ledger_reopen_integrity": True,
            "automatic_approval": False,
            "history_rewrite_authority": False,
            "remote_git_mutation_authority": False,
            "release_authority": False,
            "fabrication_authority": False,
        },
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
