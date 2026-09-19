from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from engineering_ai.projects import BuoyCalcReadOnlyAdapter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gate 014 BuoyCalc strict read-only adapter smoke"
    )
    parser.add_argument(
        "--repository",
        default=os.environ.get(
            "BUOYCALC_REPO",
            r"C:\workspace\repos\buoycalc-windows",
        ),
    )
    args = parser.parse_args()

    repository = Path(args.repository)
    if not repository.exists():
        print(
            json.dumps(
                {
                    "gate": "014",
                    "adapter": "buoycalc-readonly",
                    "repository_root": str(repository),
                    "snapshot_state": "LOCAL_REPOSITORY_NOT_FOUND",
                    "release_state": "NOT_AUTHORIZED",
                    "physical_validation": "PHYSICAL_NOT_EXECUTED",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    adapter = BuoyCalcReadOnlyAdapter(repository)
    before = adapter.git_snapshot()
    snapshot = adapter.snapshot()
    after = adapter.git_snapshot()

    counts: dict[str, int] = {}
    for item in snapshot.source_inventory:
        counts[item.boundary_class.value] = counts.get(item.boundary_class.value, 0) + 1

    presentation_physics_violation = any(
        item.boundary_class.value == "CALCULATION_CORE_CANDIDATE"
        and (
            "report" in Path(item.path).name.casefold()
            or "pdf" in Path(item.path).name.casefold()
            or "mainwindow" in Path(item.path).name.casefold()
            or "/views/" in f"/{item.path.replace(chr(92), '/').casefold()}"
        )
        for item in snapshot.source_inventory
    )

    repository_unchanged = (
        before.head_sha == after.head_sha
        and before.status_text == after.status_text
    )
    baseline_aligned = (
        snapshot.git.branch == "main"
        and snapshot.git.origin_main_sha is not None
        and snapshot.git.head_sha == snapshot.git.origin_main_sha
    )

    payload = {
        "gate": "014",
        "adapter": "buoycalc-readonly",
        "repository_root": snapshot.repository_root,
        "git": {
            "branch": snapshot.git.branch,
            "head_sha": snapshot.git.head_sha,
            "origin_main_sha": snapshot.git.origin_main_sha,
            "dirty": snapshot.git.dirty,
            "baseline_aligned": baseline_aligned,
        },
        "governance": [
            {"path": doc.path, "sha256": doc.sha256}
            for doc in snapshot.governance_documents
        ],
        "invariant_checks": [
            {
                "id": check.invariant_id,
                "source_path": check.source_path,
                "passed": check.passed,
            }
            for check in snapshot.invariant_checks
        ],
        "invariant_violations": list(snapshot.invariant_violations),
        "source_inventory_count": len(snapshot.source_inventory),
        "source_boundary_counts": counts,
        "presentation_physics_violation": presentation_physics_violation,
        "governance_required_checks": list(snapshot.governance_required_checks),
        "release_required_checks": list(snapshot.release_required_checks),
        "release_state": snapshot.release_state,
        "physical_validation": snapshot.physical_validation,
        "repository_unchanged": repository_unchanged,
        "snapshot_state": (
            "READ_ONLY_BASELINE_OK"
            if (
                baseline_aligned
                and not snapshot.git.dirty
                and not snapshot.invariant_violations
                and not presentation_physics_violation
                and repository_unchanged
            )
            else "READ_ONLY_BASELINE_BLOCKED"
        ),
    }

    print(json.dumps(payload, ensure_ascii=False, indent=2))

    ok = (
        payload["snapshot_state"] == "READ_ONLY_BASELINE_OK"
        and snapshot.release_state.startswith("NOT_AUTHORIZED")
        and snapshot.physical_validation == "PHYSICAL_NOT_EXECUTED"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
