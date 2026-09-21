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
        "test_buoycalc_controlled.py",
        "test_external_review.py",
        "test_tool_bridge.py",
    )
    for pattern in modules:
        run_test_module(pattern)

    gate019 = run_json_smoke("scripts/gate019_job_queue_smoke.py")
    gate021 = run_json_smoke("scripts/gate021_external_review_smoke.py")
    gate022 = run_json_smoke("scripts/gate022_controlled_tool_smoke.py")

    require(gate019["gate"] == "019", "unexpected Gate 019 smoke identity")
    require(
        gate019["approval_wait_survived_reopen"],
        "persisted approval wait did not survive reopen",
    )
    require(
        gate019["approval_final_state"] == "PASS",
        "approved persisted job did not reach PASS",
    )
    require(
        not gate019["automatic_approval"],
        "Gate 019 reported automatic approval",
    )

    require(gate021["gate"] == "021", "unexpected Gate 021 smoke identity")
    require(
        gate021["unapproved_status"] == "NEEDS_HUMAN_APPROVAL",
        "external review did not stop at approval boundary",
    )
    require(
        not gate021["unapproved_provider_called"],
        "external provider was called before approval",
    )
    require(
        gate021["approved_status"] == "PASS"
        and gate021["approved_provider_called"],
        "approved external review did not execute exactly through approved path",
    )
    require(
        gate021["provider_call_count"] == 1,
        "external review provider call count was not exactly one",
    )
    require(
        not gate021["automatic_external_approval"],
        "Gate 021 reported automatic external approval",
    )

    require(gate022["gate"] == "022", "unexpected Gate 022 smoke identity")
    require(
        gate022["external_disclosure_missing_status"]
        == "NEEDS_HUMAN_APPROVAL",
        "tool bridge external disclosure did not stop at approval boundary",
    )
    require(
        not gate022["external_disclosure_missing_handler_called"],
        "tool handler ran before external disclosure approval",
    )
    require(
        gate022["approval_missing_status"] == "NEEDS_HUMAN_APPROVAL",
        "approval-required capability did not stop without approval",
    )
    require(
        not gate022["approval_missing_handler_called"],
        "approval-required handler ran before approval",
    )
    require(
        gate022["approval_named_status"] == "PASS"
        and gate022["approval_named_handler_call_count"] == 1,
        "named approval did not authorize exactly one bounded handler call",
    )
    require(
        gate022["forbidden_status"] == "BLOCKED"
        and not gate022["forbidden_handler_called"],
        "forbidden capability was not fail-closed",
    )
    require(
        not gate022["automatic_approval"],
        "Gate 022 reported automatic approval",
    )
    require(
        not gate022["git_mutation_surface"],
        "Gate 022 exposed Git mutation authority",
    )

    payload = {
        "gate": "028",
        "state": "PASS_V1_0_POLICY_APPROVAL_ENFORCEMENT",
        "acceptance_basis": {
            "supervisor_policy_module": True,
            "controlled_project_mutation_module": True,
            "external_review_module": True,
            "controlled_tool_bridge_module": True,
            "persisted_job_queue_smoke": gate019["state"],
            "external_review_smoke": gate021["state"],
            "controlled_tool_smoke": gate022["state"],
        },
        "assertions": {
            "deny_is_fail_closed": True,
            "approval_required_executes_zero_before_approval": True,
            "approval_without_identity_is_non_authorizing": True,
            "named_approval_is_bounded": True,
            "persisted_waiting_for_approval_survives_reopen": True,
            "external_provider_not_called_before_approval": True,
            "tool_handler_not_called_before_approval": True,
            "forbidden_tool_handler_not_called": True,
            "automatic_approval": False,
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
