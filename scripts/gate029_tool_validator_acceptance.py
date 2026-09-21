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
        "test_tools.py",
        "test_platavm_adapter.py",
        "test_platavm_controlled.py",
        "test_buoycalc_adapter.py",
        "test_buoycalc_controlled.py",
    )
    for pattern in modules:
        run_test_module(pattern)

    gate027 = run_json_smoke("scripts/gate027_offline_continuation_smoke.py")
    require(gate027["gate"] == "027", "unexpected Gate 027 smoke identity")
    require(
        gate027["state"] == "PASS_OFFLINE_CONTINUATION_BOUNDARY",
        "Gate 027 offline boundary did not pass",
    )
    require(
        not gate027["external_network_exercised"],
        "Gate 027 unexpectedly exercised external network",
    )
    require(
        gate027["buoycalc"]["blocked_reason"] == "OFFLINE_NETWORK_REQUIRED",
        "BuoyCalc network-capable restore was not explicitly blocked offline",
    )
    require(
        gate027["platavm"]["controlled_state"] == "READY_FOR_HUMAN_APPROVAL",
        "PlataVM controlled local validation did not reach approval boundary",
    )
    require(
        gate027["buoycalc"]["network_block_state"] == "BLOCKED_RUNTIME_PREREQUISITE",
        "BuoyCalc network-required validation did not remain blocked",
    )

    payload = {
        "gate": "029",
        "state": "PASS_V1_0_DETERMINISTIC_TOOL_VALIDATOR_INTEGRATION",
        "acceptance_basis": {
            "tool_adapter_module": True,
            "platavm_read_only_module": True,
            "platavm_controlled_module": True,
            "buoycalc_read_only_module": True,
            "buoycalc_controlled_module": True,
            "offline_continuation_smoke": gate027["state"],
        },
        "assertions": {
            "filesystem_root_bounded": True,
            "git_read_only_surface": True,
            "generic_git_command_surface": False,
            "process_fixed_allow_list": True,
            "process_shell_false_preserved": True,
            "process_timeout_bounded": True,
            "process_output_bounded": True,
            "offline_network_capable_pre_subprocess_block": True,
            "platavm_validator_failure_blocks_ready": True,
            "buoycalc_validator_failure_blocks_ready": True,
            "buoycalc_tracked_mutation_blocks_ready": True,
            "remote_git_mutation_authority": False,
            "generic_filesystem_write_authority": False,
            "release_authority": False,
            "fabrication_authority": False,
        },
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
