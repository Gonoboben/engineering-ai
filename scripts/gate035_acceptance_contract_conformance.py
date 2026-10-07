from __future__ import annotations

import json
import subprocess
from pathlib import Path

from engineering_ai.supervisor import Supervisor, ToolOutcome, ValidatorOutcome


ROOT = Path(__file__).resolve().parents[1]


def policy() -> dict:
    return {
        "schema_version": "1.0",
        "policy_version": "1.0",
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
        "stop_conditions": ["required validator failure"],
        "retry_limit": 1,
    }


def state(head: str) -> dict:
    return {
        "schema_version": "1.0",
        "state_revision": 1,
        "project_id": "engineering-ai",
        "current_gate": "035",
        "active_job_id": None,
        "repository_ref": {
            "branch": "gate-035-deterministic-acceptance-contract-conformance",
            "head_sha": head,
        },
        "architecture_baseline": "Gate 001",
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


def job(required: tuple[str, ...] = ("schema-suite",)) -> dict:
    return {
        "schema_version": "1.0",
        "job_id": "gate-035-acceptance-contract",
        "project_id": "engineering-ai",
        "gate_id": "035",
        "objective": "Validate generic acceptance-contract conformance",
        "scope": ["generic Supervisor completion"],
        "out_of_scope": ["project-specific validator semantics"],
        "requested_actions": ["read_repository", "run_validator"],
        "required_validators": list(required),
        "retry_limit": 1,
        "attempts": 0,
        "status": "QUEUED",
        "blocker": None,
    }


def result(
    head: str,
    *,
    state_value: str = "PASS",
    evidence: tuple[str, ...] = ("ev-schema-suite",),
    revision: str | None = None,
    timed_out: bool = False,
) -> ValidatorOutcome:
    return ValidatorOutcome(
        validator_id="schema-suite",
        state=state_value,
        evidence_refs=evidence,
        repository_head_sha=head if revision is None else revision,
        timed_out=timed_out,
    )


def run() -> dict:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    mandatory_policy = policy()
    mandatory_policy["mandatory_validators"] = ["schema-suite"]
    mandatory_supervisor = Supervisor(
        policy=mandatory_policy,
        state=state(head),
    )
    mandatory_omission = mandatory_supervisor.execute(
        job=job(required=()),
        action="read_repository",
        tool=lambda action: ToolOutcome(True, "read ok", ("ev-read",)),
    )

    missing_supervisor = Supervisor(policy=policy(), state=state(head))
    missing = missing_supervisor.execute(
        job=job(),
        action="read_repository",
        tool=lambda action: ToolOutcome(True, "read ok", ("ev-read",)),
    )

    failed_supervisor = Supervisor(policy=policy(), state=state(head))
    failed = failed_supervisor.execute(
        job=job(),
        action="run_validator",
        tool=lambda action: ToolOutcome(
            True,
            "validator completed",
            validator_results=(result(head, state_value="FAIL"),),
        ),
    )

    timeout_supervisor = Supervisor(policy=policy(), state=state(head))
    timeout = timeout_supervisor.execute(
        job=job(),
        action="run_validator",
        tool=lambda action: ToolOutcome(
            True,
            "validator timed out",
            validator_results=(
                result(
                    head,
                    state_value="NOT_RUN",
                    evidence=(),
                    timed_out=True,
                ),
            ),
        ),
    )

    wrong_supervisor = Supervisor(policy=policy(), state=state(head))
    wrong = wrong_supervisor.execute(
        job=job(),
        action="run_validator",
        tool=lambda action: ToolOutcome(
            True,
            "wrong revision",
            validator_results=(
                result(head, revision="1" * 40),
            ),
        ),
    )

    exact_supervisor = Supervisor(policy=policy(), state=state(head))
    blocked = exact_supervisor.execute(
        job=job(),
        action="read_repository",
        tool=lambda action: ToolOutcome(True, "read ok", ("ev-read",)),
    )
    exact = exact_supervisor.execute(
        job=blocked.job,
        action="run_validator",
        tool=lambda action: ToolOutcome(
            True,
            "validator pass",
            validator_results=(result(head),),
        ),
    )

    no_validator_supervisor = Supervisor(policy=policy(), state=state(head))
    no_validator = no_validator_supervisor.execute(
        job=job(required=()),
        action="read_repository",
        tool=lambda action: ToolOutcome(True, "read ok", ("ev-read",)),
    )

    checks = {
        "policy_mandatory_validator_cannot_be_bypassed_by_job_omission":
            mandatory_omission.job["status"] == "BLOCKED"
            and "schema-suite=MISSING" in mandatory_omission.job["blocker"],
        "missing_required_validator_blocked": missing.job["status"] == "BLOCKED",
        "failed_required_validator_failed": failed.job["status"] == "FAIL",
        "timeout_not_pass": timeout.job["status"] == "BLOCKED",
        "wrong_revision_not_pass": wrong.job["status"] == "BLOCKED",
        "exact_revision_evidence_pass": exact.job["status"] == "PASS",
        "no_required_validator_path_pass": no_validator.job["status"] == "PASS",
        "physical_validation_not_claimed": next(
            item
            for item in exact.state["validation_states"]
            if item["check_id"] == "physical-validation"
        )["state"]
        == "PHYSICAL_NOT_EXECUTED",
    }
    if not all(checks.values()):
        raise SystemExit("Gate 035 acceptance contract check failed")

    return {
        "gate": "035",
        "state": "PASS_V1_0_DETERMINISTIC_ACCEPTANCE_CONTRACT_CONFORMANCE",
        "source_revision": head,
        "checks": checks,
        "release_authority": False,
        "fabrication_authority": False,
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=True, indent=2, sort_keys=True))
