from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

from engineering_ai.projects import BuoyCalcReadOnlyAdapter
from engineering_ai.tools import GitReadOnlyAdapter


PREFIX = "engineering-ai/buoycalc/"


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "--no-pager", *args],
        cwd=repo,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
    )


def snapshot(adapter: BuoyCalcReadOnlyAdapter) -> dict[str, object]:
    snap = adapter.git_snapshot()
    return {
        "branch": snap.branch,
        "head_sha": snap.head_sha,
        "origin_main_sha": snap.origin_main_sha,
        "dirty": snap.dirty,
        "status_text": snap.status_text,
    }


def clear_readonly_and_retry(function, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    function(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recover a guarded stale Gate 015 disposable BuoyCalc worktree"
    )
    parser.add_argument("--repository", required=True)
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--base-sha", required=True)
    args = parser.parse_args()

    repo = Path(args.repository).resolve(strict=True)
    worktree = Path(args.worktree)
    branch = args.branch
    base_sha = args.base_sha.strip()

    if not branch.startswith(PREFIX):
        print(json.dumps({"state": "REFUSED", "reason": "branch prefix mismatch"}, indent=2))
        return 2
    if len(base_sha) != 40 or any(ch not in "0123456789abcdef" for ch in base_sha):
        print(json.dumps({"state": "REFUSED", "reason": "invalid base SHA"}, indent=2))
        return 2

    resolved_parent = worktree.parent.resolve(strict=True)
    if not resolved_parent.name.startswith("engineering-ai-gate015-buoycalc-"):
        print(
            json.dumps(
                {"state": "REFUSED", "reason": "unexpected disposable parent"},
                indent=2,
            )
        )
        return 2
    if not worktree.name.startswith("gate015-"):
        print(json.dumps({"state": "REFUSED", "reason": "unexpected worktree name"}, indent=2))
        return 2

    readonly = BuoyCalcReadOnlyAdapter(repo)
    before = snapshot(readonly)

    branch_ref = GitReadOnlyAdapter(repo).ref_sha(branch)
    if not branch_ref.ok or branch_ref.stdout.strip() != base_sha:
        print(
            json.dumps(
                {
                    "state": "REFUSED",
                    "reason": "controlled branch does not point to expected base SHA",
                    "branch_sha": branch_ref.stdout.strip() if branch_ref.ok else None,
                },
                indent=2,
            )
        )
        return 2

    listing = run_git(repo, "worktree", "list", "--porcelain")
    if listing.returncode != 0:
        print(
            json.dumps(
                {"state": "ERROR", "reason": listing.stderr.strip() or listing.stdout.strip()},
                indent=2,
            )
        )
        return 1
    normalized_worktree = str(worktree.resolve(strict=False)).replace("\\", "/")
    if normalized_worktree.casefold() not in listing.stdout.replace("\\", "/").casefold():
        print(
            json.dumps(
                {"state": "REFUSED", "reason": "worktree is not registered by Git"},
                indent=2,
            )
        )
        return 2

    if worktree.exists():
        wt = GitReadOnlyAdapter(worktree)
        head = wt.head_sha()
        diff = wt.diff_worktree()
        cached = wt.diff_cached()
        if not head.ok or head.stdout.strip() != base_sha:
            print(json.dumps({"state": "REFUSED", "reason": "worktree HEAD mismatch"}, indent=2))
            return 2
        if not diff.ok or not cached.ok or diff.stdout or cached.stdout:
            print(
                json.dumps(
                    {"state": "REFUSED", "reason": "tracked worktree state is not clean"},
                    indent=2,
                )
            )
            return 2

    errors: list[str] = []
    removed_by_git = False
    for attempt in range(3):
        result = run_git(repo, "worktree", "remove", "--force", str(worktree))
        if result.returncode == 0:
            removed_by_git = True
            break
        errors.append(result.stderr.strip() or result.stdout.strip())
        time.sleep(0.25 * (attempt + 1))

    fallback_used = False
    if not removed_by_git:
        fallback_used = True
        if worktree.exists():
            try:
                shutil.rmtree(worktree, onerror=clear_readonly_and_retry)
            except OSError as exc:
                print(
                    json.dumps(
                        {
                            "state": "ERROR",
                            "reason": f"filesystem cleanup failed: {exc}",
                            "git_remove_errors": errors,
                        },
                        indent=2,
                    )
                )
                return 1
        prune = run_git(repo, "worktree", "prune", "--expire", "now")
        if prune.returncode != 0:
            print(
                json.dumps(
                    {
                        "state": "ERROR",
                        "reason": prune.stderr.strip() or prune.stdout.strip(),
                        "git_remove_errors": errors,
                    },
                    indent=2,
                )
            )
            return 1

    branch_ref_after = GitReadOnlyAdapter(repo).ref_sha(branch)
    if branch_ref_after.ok:
        if branch_ref_after.stdout.strip() != base_sha:
            print(
                json.dumps(
                    {
                        "state": "REFUSED",
                        "reason": "branch moved after worktree cleanup",
                        "branch_sha": branch_ref_after.stdout.strip(),
                    },
                    indent=2,
                )
            )
            return 2
        delete = run_git(repo, "branch", "-D", branch)
        if delete.returncode != 0:
            print(
                json.dumps(
                    {
                        "state": "ERROR",
                        "reason": delete.stderr.strip() or delete.stdout.strip(),
                    },
                    indent=2,
                )
            )
            return 1

    after = snapshot(readonly)
    payload = {
        "gate": "015",
        "state": "STALE_DISPOSABLE_WORKTREE_CLEANED",
        "worktree_removed": not worktree.exists(),
        "branch_removed": not GitReadOnlyAdapter(repo).ref_sha(branch).ok,
        "fallback_used": fallback_used,
        "git_remove_errors": errors,
        "before": before,
        "after": after,
        "repository_unchanged": before == after,
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if (
        payload["worktree_removed"]
        and payload["branch_removed"]
        and payload["repository_unchanged"]
    ) else 1


if __name__ == "__main__":
    sys.exit(main())
