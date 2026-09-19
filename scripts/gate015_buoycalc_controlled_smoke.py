from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from engineering_ai.projects import (
    BuoyCalcControlledEngineeringLoop,
    BuoyCalcControlledState,
    BuoyCalcReadOnlyAdapter,
)
from engineering_ai.tools import GitReadOnlyAdapter, ToolAccessError, ToolExecutionError


def snapshot_dict(adapter: BuoyCalcReadOnlyAdapter) -> dict[str, object]:
    snap = adapter.git_snapshot()
    return {
        "branch": snap.branch,
        "head_sha": snap.head_sha,
        "origin_main_sha": snap.origin_main_sha,
        "dirty": snap.dirty,
        "status_text": snap.status_text,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gate 015 BuoyCalc controlled validation smoke"
    )
    parser.add_argument(
        "--repository",
        default=os.environ.get(
            "BUOYCALC_REPO",
            r"C:\workspace\repos\buoycalc-windows",
        ),
    )
    parser.add_argument(
        "--approve-worktree",
        action="store_true",
        help="Explicit human approval to create and later remove a disposable local worktree/branch.",
    )
    args = parser.parse_args()

    repository = Path(args.repository)
    if not repository.exists():
        print(
            json.dumps(
                {
                    "gate": "015",
                    "state": "LOCAL_REPOSITORY_NOT_FOUND",
                    "repository": str(repository),
                    "physical_validation": "PHYSICAL_NOT_EXECUTED",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    if not args.approve_worktree:
        print(
            json.dumps(
                {
                    "gate": "015",
                    "state": "NEEDS_HUMAN_APPROVAL",
                    "required_action": "write_worktree",
                    "instruction": "rerun with --approve-worktree after explicit human approval",
                    "physical_validation": "PHYSICAL_NOT_EXECUTED",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 3

    readonly = BuoyCalcReadOnlyAdapter(repository)
    before = snapshot_dict(readonly)

    with tempfile.TemporaryDirectory(prefix="engineering-ai-gate015-prereq-") as prereq_tmp:
        prereq_loop = BuoyCalcControlledEngineeringLoop(repository, prereq_tmp)
        runtime = prereq_loop.runtime_prerequisites()

    if runtime.blockers:
        payload = {
            "gate": "015",
            "state": "BLOCKED_RUNTIME_PREREQUISITE",
            "runtime": {
                "dotnet_executable": runtime.dotnet_executable,
                "pwsh_executable": runtime.pwsh_executable,
                "dotnet_sdk8_available": runtime.dotnet_sdk8_available,
                "dotnet_sdks": list(runtime.dotnet_sdks),
                "blockers": list(runtime.blockers),
            },
            "before": before,
            "after": snapshot_dict(readonly),
            "repository_unchanged": before == snapshot_dict(readonly),
            "release_state": "NOT_AUTHORIZED",
            "physical_validation": "PHYSICAL_NOT_EXECUTED",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 4
    base_sha = str(before["head_sha"])
    suffix = base_sha[:12]
    worktree_parent = Path(
        tempfile.mkdtemp(prefix="engineering-ai-gate015-buoycalc-")
    )
    worktree_name = f"gate015-{suffix}"
    branch = f"engineering-ai/buoycalc/gate015-smoke-{suffix}"
    worktree_path = worktree_parent / worktree_name

    loop = BuoyCalcControlledEngineeringLoop(repository, worktree_parent)
    preparation = None
    validation = None
    cleanup_state = "NOT_ATTEMPTED"
    execution_error: str | None = None

    try:
        preparation = loop.prepare(
            worktree_name=worktree_name,
            branch=branch,
            base_ref="HEAD",
        )
        if preparation.state is not BuoyCalcControlledState.WORKTREE_READY:
            after = snapshot_dict(readonly)
            payload = {
                "gate": "015",
                "state": preparation.state.value,
                "blockers": list(preparation.blockers),
                "before": before,
                "after": after,
                "repository_unchanged": before == after,
                "worktree_created": worktree_path.exists(),
                "release_state": "NOT_AUTHORIZED",
                "physical_validation": "PHYSICAL_NOT_EXECUTED",
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1

        assert preparation.session is not None
        try:
            validation = loop.validate(session=preparation.session)
        except (ToolAccessError, ToolExecutionError, OSError) as exc:
            execution_error = f"{type(exc).__name__}: {exc}"

        if validation is not None and validation.tracked_state_unchanged:
            try:
                loop.cleanup_disposable_generated(preparation.session)
                cleanup_state = "PASS"
            except (ToolAccessError, ToolExecutionError, OSError) as exc:
                cleanup_state = f"FAIL: {type(exc).__name__}: {exc}"
        elif validation is not None:
            cleanup_state = "BLOCKED_TRACKED_STATE_CHANGED"
        else:
            try:
                loop.cleanup_disposable_generated(preparation.session)
                cleanup_state = "PASS_AFTER_EXECUTION_ERROR"
            except (ToolAccessError, ToolExecutionError, OSError) as exc:
                cleanup_state = f"FAIL_AFTER_EXECUTION_ERROR: {type(exc).__name__}: {exc}"

        after = snapshot_dict(readonly)
        branch_ref = GitReadOnlyAdapter(repository).ref_sha(branch)
        branch_removed = not branch_ref.ok
        worktree_removed = not worktree_path.exists()

        profile_payload = []
        if validation is not None:
            for profile in validation.profiles:
                profile_payload.append(
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
                                "validation_class": step.validation_class,
                            }
                            for step in profile.steps
                        ],
                    }
                )

        state = (
            validation.state.value
            if validation is not None
            else "VALIDATION_EXECUTION_ERROR"
        )
        payload = {
            "gate": "015",
            "repository": str(repository.resolve()),
            "state": state,
            "base_sha": base_sha,
            "branch": branch,
            "worktree_parent": str(worktree_parent),
            "worktree_removed": worktree_removed,
            "branch_removed": branch_removed,
            "cleanup_state": cleanup_state,
            "execution_error": execution_error,
            "profiles": profile_payload,
            "tracked_state_unchanged": (
                validation.tracked_state_unchanged
                if validation is not None
                else None
            ),
            "release_state": (
                validation.release_state
                if validation is not None
                else "NOT_AUTHORIZED"
            ),
            "physical_validation": "PHYSICAL_NOT_EXECUTED",
            "before": before,
            "after": after,
            "repository_unchanged": before == after,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))

        success = (
            validation is not None
            and validation.state is BuoyCalcControlledState.READY_FOR_HUMAN_APPROVAL
            and validation.tracked_state_unchanged
            and cleanup_state == "PASS"
            and worktree_removed
            and branch_removed
            and before == after
            and validation.release_state.startswith("NOT_AUTHORIZED")
            and validation.physical_validation == "PHYSICAL_NOT_EXECUTED"
        )
        return 0 if success else 1
    finally:
        if worktree_parent.exists() and not any(worktree_parent.iterdir()):
            worktree_parent.rmdir()


if __name__ == "__main__":
    sys.exit(main())
