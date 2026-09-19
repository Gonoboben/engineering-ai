from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from engineering_ai.projects import PlataVMControlledEngineeringLoop


def git_output(repository: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repository,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gate 013 real PlataVM controlled-loop policy smoke"
    )
    parser.add_argument(
        "--repository",
        default=os.environ.get("PLATAVM_REPO", r"C:\workspace\repos\plataVM"),
    )
    args = parser.parse_args()

    repository = Path(args.repository)
    if not repository.exists():
        print(
            json.dumps(
                {
                    "gate": "013",
                    "state": "LOCAL_REPOSITORY_NOT_FOUND",
                    "repository": str(repository),
                    "physical_validation": "PHYSICAL_NOT_EXECUTED",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    before_head = git_output(repository, "rev-parse", "HEAD").strip()
    before_status = git_output(
        repository,
        "status",
        "--porcelain=v1",
        "--branch",
        "--untracked-files=normal",
    )

    with tempfile.TemporaryDirectory(prefix="engineering-ai-gate013-") as tmp:
        worktree_parent = Path(tmp)
        loop = PlataVMControlledEngineeringLoop(
            repository,
            worktree_parent,
            python_executable=sys.executable,
        )
        preparation = loop.prepare(
            worktree_name="platavm-policy-smoke",
            branch="engineering-ai/gate013-policy-smoke",
            base_ref="HEAD",
        )
        created = (worktree_parent / "platavm-policy-smoke").exists()

    after_head = git_output(repository, "rev-parse", "HEAD").strip()
    after_status = git_output(
        repository,
        "status",
        "--porcelain=v1",
        "--branch",
        "--untracked-files=normal",
    )

    payload = {
        "gate": "013",
        "repository": str(repository.resolve()),
        "state": preparation.state.value,
        "source_conflicts": list(preparation.source_conflicts),
        "worktree_created": created,
        "before": {
            "head": before_head,
            "status": before_status,
        },
        "after": {
            "head": after_head,
            "status": after_status,
        },
        "repository_unchanged": (
            before_head == after_head and before_status == after_status
        ),
        "remote_mutation_attempted": False,
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
    }

    print(json.dumps(payload, ensure_ascii=False, indent=2))

    expected_block = (
        preparation.state.value == "BLOCKED_SOURCE_CONFLICT"
        and bool(preparation.source_conflicts)
        and not created
        and payload["repository_unchanged"]
    )
    return 0 if expected_block else 1


if __name__ == "__main__":
    sys.exit(main())
