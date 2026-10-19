from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from engineering_ai.projects import (
    BuoyCalcControlledEngineeringLoop,
    BuoyCalcControlledState,
    BuoyCalcReadOnlyAdapter,
    ControlledLoopState,
    PlataVMControlledEngineeringLoop,
    PlataVMReadOnlyAdapter,
)
from engineering_ai.tools import GitReadOnlyAdapter, ToolAccessError, ToolExecutionError


GATE = "036"
PLATAVM_EXPECTED_HEAD = "840435615d0b3ebf5f1137f575cfd75b66501964"
PLATAVM_EXPECTED_ORIGIN_MAIN = "dcba77466d4800c0e7a336a2771684e066f845db"
PLATAVM_EXPECTED_BRANCH = "agent/pcb-e-aux-hardware-current-v1-9"
BUOYCALC_EXPECTED_HEAD = "1ea0ddb76f07a41a811390632b64afbf257283eb"
BUOYCALC_REQUIRED_PROFILES = (
    "buoycalc.dotnet_build",
    "buoycalc.selected_shape_consumer_scan",
    "buoycalc.report_store_consumer_scan",
    "buoycalc.validation_601",
)
PLATAVM_REQUIRED_VALIDATORS = (
    "platavm.repository_integrity",
    "platavm.semantic_gates",
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _git_snapshot_dict(snapshot: Any) -> dict[str, Any]:
    return {
        "branch": snapshot.branch,
        "head_sha": snapshot.head_sha,
        "origin_main_sha": snapshot.origin_main_sha,
        "dirty": snapshot.dirty,
        "status_sha256": _sha256_text(snapshot.status_text),
    }


def _branch_removed(repository: Path, branch: str) -> bool:
    result = GitReadOnlyAdapter(repository).ref_sha(branch)
    return not result.ok


def _append_check(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def evaluate_gate036_payload(payload: dict[str, Any]) -> tuple[bool, tuple[str, ...]]:
    """Fail-closed acceptance evaluator for real connected-project evidence."""

    errors: list[str] = []
    _append_check(errors, payload.get("gate") == GATE, "gate identity mismatch")
    _append_check(errors, payload.get("real_execution") is True, "real execution missing")
    _append_check(
        errors,
        payload.get("remote_connected_project_mutation_attempted") is False,
        "remote connected-project mutation must remain false",
    )

    plat = payload.get("platavm")
    if not isinstance(plat, dict):
        errors.append("PlataVM evidence missing")
    else:
        before = plat.get("before") or {}
        after = plat.get("after") or {}
        _append_check(
            errors,
            before.get("head_sha") == PLATAVM_EXPECTED_HEAD,
            "PlataVM exact head mismatch",
        )
        _append_check(
            errors,
            before.get("origin_main_sha") == PLATAVM_EXPECTED_ORIGIN_MAIN,
            "PlataVM origin/main mismatch",
        )
        _append_check(
            errors,
            before.get("branch") == PLATAVM_EXPECTED_BRANCH,
            "PlataVM active branch mismatch",
        )
        _append_check(errors, before.get("dirty") is False, "PlataVM primary checkout dirty")
        _append_check(errors, plat.get("source_conflicts") == [], "PlataVM source conflict remains")
        _append_check(
            errors,
            plat.get("preparation_state") == ControlledLoopState.WORKTREE_READY.value,
            "PlataVM worktree was not prepared",
        )
        _append_check(
            errors,
            plat.get("validation_state")
            == ControlledLoopState.READY_FOR_HUMAN_APPROVAL.value,
            "PlataVM validators did not reach READY_FOR_HUMAN_APPROVAL",
        )
        validators = plat.get("validators")
        validator_ids = tuple(item.get("profile_id") for item in validators or [])
        _append_check(
            errors,
            validator_ids == PLATAVM_REQUIRED_VALIDATORS,
            "PlataVM validator set mismatch",
        )
        _append_check(
            errors,
            bool(validators)
            and all(item.get("state") == "PASS" for item in validators),
            "PlataVM validator PASS closure missing",
        )
        _append_check(errors, plat.get("cleanup_state") == "PASS", "PlataVM cleanup failed")
        _append_check(errors, plat.get("worktree_removed") is True, "PlataVM worktree remains")
        _append_check(errors, plat.get("branch_removed") is True, "PlataVM controlled branch remains")
        _append_check(
            errors,
            plat.get("repository_unchanged") is True and before == after,
            "PlataVM primary repository changed",
        )
        markers = plat.get("authority_markers") or {}
        _append_check(
            errors,
            markers.get("package_set_not_ready") is True,
            "PlataVM package-set barrier not proven",
        )
        _append_check(
            errors,
            markers.get("fabrication_not_granted") is True,
            "PlataVM fabrication barrier not proven",
        )
        _append_check(
            errors,
            markers.get("physical_not_executed") is True,
            "PlataVM physical barrier not proven",
        )
        _append_check(
            errors,
            markers.get("series_not_granted") is True,
            "PlataVM series barrier not proven",
        )

    buoy = payload.get("buoycalc")
    if not isinstance(buoy, dict):
        errors.append("BuoyCalc evidence missing")
    else:
        before = buoy.get("before") or {}
        after = buoy.get("after") or {}
        _append_check(
            errors,
            before.get("head_sha") == BUOYCALC_EXPECTED_HEAD,
            "BuoyCalc exact head mismatch",
        )
        _append_check(errors, before.get("branch") == "main", "BuoyCalc primary branch is not main")
        _append_check(
            errors,
            before.get("origin_main_sha") == BUOYCALC_EXPECTED_HEAD,
            "BuoyCalc origin/main mismatch",
        )
        _append_check(errors, before.get("dirty") is False, "BuoyCalc primary checkout dirty")
        runtime = buoy.get("runtime") or {}
        _append_check(errors, runtime.get("blockers") == [], "BuoyCalc runtime prerequisite blocked")
        _append_check(
            errors,
            buoy.get("preparation_state") == BuoyCalcControlledState.WORKTREE_READY.value,
            "BuoyCalc worktree was not prepared",
        )
        _append_check(
            errors,
            buoy.get("validation_state")
            == BuoyCalcControlledState.READY_FOR_HUMAN_APPROVAL.value,
            "BuoyCalc validators did not reach READY_FOR_HUMAN_APPROVAL",
        )
        profiles = buoy.get("profiles") or []
        profile_ids = tuple(item.get("profile_id") for item in profiles)
        _append_check(
            errors,
            profile_ids == BUOYCALC_REQUIRED_PROFILES,
            "BuoyCalc fixed profile set mismatch",
        )
        _append_check(
            errors,
            bool(profiles) and all(item.get("passed") is True for item in profiles),
            "BuoyCalc profile PASS closure missing",
        )
        _append_check(
            errors,
            buoy.get("tracked_state_unchanged") is True,
            "BuoyCalc tracked state changed",
        )
        _append_check(errors, buoy.get("cleanup_state") == "PASS", "BuoyCalc cleanup failed")
        _append_check(errors, buoy.get("worktree_removed") is True, "BuoyCalc worktree remains")
        _append_check(errors, buoy.get("branch_removed") is True, "BuoyCalc controlled branch remains")
        _append_check(
            errors,
            buoy.get("repository_unchanged") is True and before == after,
            "BuoyCalc primary repository changed",
        )
        release_state = str(buoy.get("release_state") or "")
        _append_check(
            errors,
            release_state.startswith("NOT_AUTHORIZED"),
            "BuoyCalc release authority was promoted",
        )
        _append_check(
            errors,
            buoy.get("project_release_not_ready") is True,
            "BuoyCalc NOT READY release marker not proven",
        )
        _append_check(
            errors,
            buoy.get("physical_validation") == "PHYSICAL_NOT_EXECUTED",
            "BuoyCalc physical state was promoted",
        )

    return not errors, tuple(errors)


def _plata_authority_markers(repository: Path) -> dict[str, bool]:
    text = (repository / "Docs" / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    return {
        "package_set_not_ready": "package set / fabrication / physical / series: NOT_READY / NOT_GRANTED / NOT_EXECUTED / NOT_GRANTED" in text,
        "fabrication_not_granted": "fabrication / physical / series: NOT_READY / NOT_GRANTED / NOT_EXECUTED / NOT_GRANTED" in text
        or "package set / fabrication / physical / series: NOT_READY / NOT_GRANTED / NOT_EXECUTED / NOT_GRANTED" in text,
        "physical_not_executed": "NOT_EXECUTED" in text,
        "series_not_granted": "series: NOT_READY / NOT_GRANTED / NOT_EXECUTED / NOT_GRANTED" in text
        or "package set / fabrication / physical / series: NOT_READY / NOT_GRANTED / NOT_EXECUTED / NOT_GRANTED" in text,
    }


def _run_platavam(repository: Path) -> dict[str, Any]:
    readonly = PlataVMReadOnlyAdapter(repository)
    before_snapshot = readonly.snapshot()
    before = _git_snapshot_dict(before_snapshot.git)
    payload: dict[str, Any] = {
        "expected_head": PLATAVM_EXPECTED_HEAD,
        "expected_origin_main": PLATAVM_EXPECTED_ORIGIN_MAIN,
        "expected_branch": PLATAVM_EXPECTED_BRANCH,
        "before": before,
        "source_conflicts": list(before_snapshot.conflicts),
        "authority_markers": _plata_authority_markers(repository),
        "preparation_state": "NOT_RUN",
        "validation_state": "NOT_RUN",
        "validators": [],
        "cleanup_state": "NOT_ATTEMPTED",
        "worktree_removed": False,
        "branch_removed": False,
        "repository_unchanged": False,
        "execution_error": None,
    }
    identity_errors: list[str] = []
    if before["head_sha"] != PLATAVM_EXPECTED_HEAD:
        identity_errors.append("HEAD")
    if before["origin_main_sha"] != PLATAVM_EXPECTED_ORIGIN_MAIN:
        identity_errors.append("origin/main")
    if before["branch"] != PLATAVM_EXPECTED_BRANCH:
        identity_errors.append("branch")
    if before["dirty"]:
        identity_errors.append("dirty")
    if before_snapshot.conflicts:
        identity_errors.append("source_conflicts")
    if identity_errors:
        payload["execution_error"] = "PLATAVM_BASELINE_BLOCK: " + ", ".join(identity_errors)
        payload["after"] = _git_snapshot_dict(readonly.snapshot().git)
        payload["repository_unchanged"] = payload["before"] == payload["after"]
        return payload

    parent = Path(tempfile.mkdtemp(prefix="engineering-ai-gate036-platavm-"))
    suffix = PLATAVM_EXPECTED_HEAD[:12]
    branch = f"engineering-ai/gate036-platavm-{suffix}"
    worktree_name = f"gate036-platavm-{suffix}"
    worktree_path = parent / worktree_name
    loop = PlataVMControlledEngineeringLoop(
        repository,
        parent,
        python_executable=sys.executable,
    )
    loop.assert_no_remote_mutation_api()
    preparation = None
    try:
        preparation = loop.prepare(
            worktree_name=worktree_name,
            branch=branch,
            base_ref="HEAD",
        )
        payload["preparation_state"] = preparation.state.value
        payload["source_conflicts"] = list(preparation.source_conflicts)
        if preparation.session is None:
            return payload

        validation = loop.validate(session=preparation.session)
        payload["validation_state"] = validation.state.value
        payload["validators"] = [
            {
                "profile_id": item.profile_id,
                "state": item.state.value,
                "ok": item.result.ok,
                "exit_code": item.result.exit_code,
                "timed_out": item.result.timed_out,
                "stdout_sha256": _sha256_text(item.result.stdout),
                "stderr_sha256": _sha256_text(item.result.stderr),
            }
            for item in validation.validators
        ]
        try:
            loop.cleanup(preparation.session)
            payload["cleanup_state"] = "PASS"
        except (ToolAccessError, ToolExecutionError, OSError) as exc:
            payload["cleanup_state"] = f"FAIL: {type(exc).__name__}: {exc}"
    except (ToolAccessError, ToolExecutionError, OSError, ValueError) as exc:
        payload["execution_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        payload["worktree_removed"] = not worktree_path.exists()
        payload["branch_removed"] = _branch_removed(repository, branch)
        payload["after"] = _git_snapshot_dict(readonly.snapshot().git)
        payload["repository_unchanged"] = payload["before"] == payload["after"]
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
    return payload


def _buoy_release_not_ready(repository: Path) -> bool:
    text = (repository / "RELEASE.md").read_text(encoding="utf-8")
    return "CURRENT RELEASE STATUS = NOT READY FOR v1.0" in text


def _run_buoycalc(repository: Path) -> dict[str, Any]:
    readonly = BuoyCalcReadOnlyAdapter(repository)
    before_snapshot = readonly.git_snapshot()
    before = _git_snapshot_dict(before_snapshot)
    payload: dict[str, Any] = {
        "expected_head": BUOYCALC_EXPECTED_HEAD,
        "before": before,
        "runtime": {"blockers": ["NOT_CHECKED"]},
        "preparation_state": "NOT_RUN",
        "validation_state": "NOT_RUN",
        "profiles": [],
        "tracked_state_unchanged": False,
        "cleanup_state": "NOT_ATTEMPTED",
        "cleanup_events": [],
        "worktree_removed": False,
        "branch_removed": False,
        "repository_unchanged": False,
        "release_state": "NOT_AUTHORIZED",
        "project_release_not_ready": _buoy_release_not_ready(repository),
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
        "execution_error": None,
    }
    if (
        before["head_sha"] != BUOYCALC_EXPECTED_HEAD
        or before["origin_main_sha"] != BUOYCALC_EXPECTED_HEAD
        or before["branch"] != "main"
        or before["dirty"]
    ):
        payload["execution_error"] = "BUOYCALC_BASELINE_BLOCK"
        payload["after"] = _git_snapshot_dict(readonly.git_snapshot())
        payload["repository_unchanged"] = payload["before"] == payload["after"]
        return payload

    prereq_parent = Path(tempfile.mkdtemp(prefix="engineering-ai-gate036-buoy-prereq-"))
    try:
        prereq_loop = BuoyCalcControlledEngineeringLoop(repository, prereq_parent)
        runtime = prereq_loop.runtime_prerequisites()
    finally:
        if prereq_parent.exists() and not any(prereq_parent.iterdir()):
            prereq_parent.rmdir()

    payload["runtime"] = {
        "dotnet_executable": runtime.dotnet_executable,
        "pwsh_executable": runtime.pwsh_executable,
        "dotnet_sdk8_available": runtime.dotnet_sdk8_available,
        "dotnet_sdks": list(runtime.dotnet_sdks),
        "blockers": list(runtime.blockers),
    }
    if runtime.blockers:
        payload["execution_error"] = "BUOYCALC_RUNTIME_PREREQUISITE_BLOCK"
        payload["after"] = _git_snapshot_dict(readonly.git_snapshot())
        payload["repository_unchanged"] = payload["before"] == payload["after"]
        return payload

    parent = Path(tempfile.mkdtemp(prefix="engineering-ai-gate036-buoycalc-"))
    suffix = BUOYCALC_EXPECTED_HEAD[:12]
    branch = f"engineering-ai/buoycalc/gate036-{suffix}"
    worktree_name = f"gate036-buoycalc-{suffix}"
    worktree_path = parent / worktree_name
    loop = BuoyCalcControlledEngineeringLoop(repository, parent)
    loop.assert_no_remote_or_release_api(loop)
    preparation = None
    try:
        preparation = loop.prepare(
            worktree_name=worktree_name,
            branch=branch,
            base_ref="HEAD",
        )
        payload["preparation_state"] = preparation.state.value
        payload["blockers"] = list(preparation.blockers)
        if preparation.session is None:
            return payload

        validation = loop.validate(session=preparation.session)
        payload["validation_state"] = validation.state.value
        payload["tracked_state_unchanged"] = validation.tracked_state_unchanged
        payload["release_state"] = validation.release_state
        payload["physical_validation"] = validation.physical_validation
        payload["profiles"] = [
            {
                "profile_id": profile.profile_id,
                "passed": profile.passed,
                "steps": [
                    {
                        "step_id": step.step_id,
                        "ok": step.ok,
                        "exit_code": step.exit_code,
                        "timed_out": step.timed_out,
                        "truncated": step.truncated,
                        "stdout_sha256": step.stdout_sha256,
                        "stderr_sha256": step.stderr_sha256,
                        "network_requirement": step.network_requirement,
                        "blocked": step.blocked,
                        "block_reason": step.block_reason,
                        "validation_class": step.validation_class,
                    }
                    for step in profile.steps
                ],
            }
            for profile in validation.profiles
        ]
        try:
            loop.cleanup_disposable_generated(preparation.session)
            payload["cleanup_state"] = "PASS"
        except (ToolAccessError, ToolExecutionError, OSError) as exc:
            payload["cleanup_state"] = f"FAIL: {type(exc).__name__}: {exc}"
    except (ToolAccessError, ToolExecutionError, OSError, ValueError) as exc:
        payload["execution_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        # Preserve bounded trace even when fail-closed cleanup raises.
        payload["cleanup_events"] = list(loop.cleanup_events)
        payload["worktree_removed"] = not worktree_path.exists()
        payload["branch_removed"] = _branch_removed(repository, branch)
        payload["after"] = _git_snapshot_dict(readonly.git_snapshot())
        payload["repository_unchanged"] = payload["before"] == payload["after"]
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
    return payload


def _synthetic_pass_payload() -> dict[str, Any]:
    plata_before = {
        "branch": PLATAVM_EXPECTED_BRANCH,
        "head_sha": PLATAVM_EXPECTED_HEAD,
        "origin_main_sha": PLATAVM_EXPECTED_ORIGIN_MAIN,
        "dirty": False,
        "status_sha256": "a" * 64,
    }
    buoy_before = {
        "branch": "main",
        "head_sha": BUOYCALC_EXPECTED_HEAD,
        "origin_main_sha": BUOYCALC_EXPECTED_HEAD,
        "dirty": False,
        "status_sha256": "b" * 64,
    }
    return {
        "gate": GATE,
        "real_execution": True,
        "remote_connected_project_mutation_attempted": False,
        "platavm": {
            "before": plata_before,
            "after": dict(plata_before),
            "source_conflicts": [],
            "preparation_state": "WORKTREE_READY",
            "validation_state": "READY_FOR_HUMAN_APPROVAL",
            "validators": [
                {"profile_id": item, "state": "PASS"} for item in PLATAVM_REQUIRED_VALIDATORS
            ],
            "cleanup_state": "PASS",
            "worktree_removed": True,
            "branch_removed": True,
            "repository_unchanged": True,
            "authority_markers": {
                "package_set_not_ready": True,
                "fabrication_not_granted": True,
                "physical_not_executed": True,
                "series_not_granted": True,
            },
        },
        "buoycalc": {
            "before": buoy_before,
            "after": dict(buoy_before),
            "runtime": {"blockers": []},
            "preparation_state": "WORKTREE_READY",
            "validation_state": "READY_FOR_HUMAN_APPROVAL",
            "profiles": [
                {"profile_id": item, "passed": True} for item in BUOYCALC_REQUIRED_PROFILES
            ],
            "tracked_state_unchanged": True,
            "cleanup_state": "PASS",
            "worktree_removed": True,
            "branch_removed": True,
            "repository_unchanged": True,
            "release_state": "NOT_AUTHORIZED_REQUIRES_EXPLICIT_MANUAL_WINDOWS_RC_SMOKE",
            "project_release_not_ready": True,
            "physical_validation": "PHYSICAL_NOT_EXECUTED",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gate 036 real connected-project controlled-use acceptance"
    )
    parser.add_argument(
        "--platavm-repository",
        default=os.environ.get("PLATAVM_REPO", r"C:\workspace\repos\plataVM"),
    )
    parser.add_argument(
        "--buoycalc-repository",
        default=os.environ.get(
            "BUOYCALC_REPO",
            r"C:\workspace\repos\buoycalc-windows",
        ),
    )
    parser.add_argument(
        "--approve-worktrees",
        action="store_true",
        help="Explicit human approval for disposable local worktree/branch creation and cleanup.",
    )
    parser.add_argument("--contract-self-test", action="store_true")
    args = parser.parse_args()

    if args.contract_self_test:
        synthetic = _synthetic_pass_payload()
        passed, errors = evaluate_gate036_payload(synthetic)
        synthetic["real_execution"] = False
        print(
            json.dumps(
                {
                    "gate": GATE,
                    "state": "PASS_CONTRACT_SELF_TEST" if passed else "FAIL_CONTRACT_SELF_TEST",
                    "synthetic_only": True,
                    "errors": list(errors),
                    "physical_validation": "PHYSICAL_NOT_EXECUTED",
                },
                indent=2,
            )
        )
        return 0 if passed else 1

    if not args.approve_worktrees:
        print(
            json.dumps(
                {
                    "gate": GATE,
                    "state": "NEEDS_HUMAN_APPROVAL",
                    "required_action": "write_worktree",
                    "instruction": "rerun with --approve-worktrees after explicit human approval",
                    "real_execution": False,
                    "physical_validation": "PHYSICAL_NOT_EXECUTED",
                },
                indent=2,
            )
        )
        return 3

    plata_repo = Path(args.platavm_repository).resolve(strict=False)
    buoy_repo = Path(args.buoycalc_repository).resolve(strict=False)
    if not plata_repo.is_dir() or not buoy_repo.is_dir():
        missing = []
        if not plata_repo.is_dir():
            missing.append(str(plata_repo))
        if not buoy_repo.is_dir():
            missing.append(str(buoy_repo))
        print(
            json.dumps(
                {
                    "gate": GATE,
                    "state": "LOCAL_REPOSITORY_NOT_FOUND",
                    "missing": missing,
                    "real_execution": False,
                    "physical_validation": "PHYSICAL_NOT_EXECUTED",
                },
                indent=2,
            )
        )
        return 2

    payload = {
        "gate": GATE,
        "real_execution": True,
        "remote_connected_project_mutation_attempted": False,
        "platavm": _run_platavam(plata_repo),
        "buoycalc": _run_buoycalc(buoy_repo),
    }
    passed, errors = evaluate_gate036_payload(payload)
    payload["state"] = (
        "PASS_REAL_CONNECTED_PROJECT_CONTROLLED_USE"
        if passed
        else "BLOCKED_OR_FAILED_REAL_CONNECTED_PROJECT_CONTROLLED_USE"
    )
    payload["acceptance_errors"] = list(errors)
    payload["release_authorization"] = "NOT_GRANTED"
    payload["fabrication_authorization"] = "NOT_GRANTED"
    payload["physical_validation"] = "PHYSICAL_NOT_EXECUTED"
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
