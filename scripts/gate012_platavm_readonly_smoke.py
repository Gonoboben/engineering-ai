from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from engineering_ai.projects.platavm import PlataVMReadOnlyAdapter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gate 012 PlataVM read-only adapter smoke"
    )
    parser.add_argument(
        "--repository",
        default=os.environ.get("PLATAVM_REPO", r"C:\workspace\repos\plataVM"),
    )
    parser.add_argument(
        "--run-validators",
        action="store_true",
        help="Run only the two fixed PlataVM read-only validator profiles.",
    )
    args = parser.parse_args()

    adapter = PlataVMReadOnlyAdapter(Path(args.repository))
    snapshot = adapter.snapshot()

    payload = {
        "gate": "012",
        "adapter": "platavm-readonly",
        "repository_root": snapshot.repository_root,
        "git": {
            "branch": snapshot.git.branch,
            "head_sha": snapshot.git.head_sha,
            "origin_main_sha": snapshot.git.origin_main_sha,
            "dirty": snapshot.git.dirty,
        },
        "governance": [
            {"path": doc.path, "sha256": doc.sha256}
            for doc in snapshot.governance_documents
        ],
        "latest_chronology": {
            "path": snapshot.latest_chronology.path,
            "sha256": snapshot.latest_chronology.sha256,
        },
        "kicad_asset_count": len(snapshot.kicad_assets),
        "kicad_assets": list(snapshot.kicad_assets),
        "conflicts": list(snapshot.conflicts),
        "snapshot_state": (
            "SOURCE_CONFLICT" if snapshot.conflicts else "READ_ONLY_SNAPSHOT_OK"
        ),
        "validators": [],
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
    }

    exit_code = 0
    if args.run_validators:
        for profile_id in adapter.validator_profiles:
            result = adapter.run_validator(profile_id)
            payload["validators"].append(
                {
                    "profile_id": result.profile_id,
                    "state": result.state.value,
                    "operation": result.result.operation,
                    "summary": result.result.summary,
                    "exit_code": result.result.exit_code,
                    "timed_out": result.result.timed_out,
                    "truncated": result.result.truncated,
                    "stdout": result.result.stdout,
                    "stderr": result.result.stderr,
                }
            )
            if result.state.value != "PASS":
                exit_code = 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
