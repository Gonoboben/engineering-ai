"""Gate 006 narrow local runtime smoke test.

This script intentionally grants only one read-only repository action. The model
may propose that action; the deterministic Supervisor evaluates it and the
filesystem adapter performs the actual read.

Run from the repository root on the primary Windows workstation:
    python scripts/gate006_role_smoke.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping, Any

from engineering_ai.models import ModelToolSpec, OllamaProvider
from engineering_ai.supervisor import (
    PlannerExecutorReviewerLoop,
    RoleModelConfig,
    ToolOutcome,
)
from engineering_ai.tools import ReadOnlyFilesystemAdapter


ROOT = Path(__file__).resolve().parents[1]


def make_policy() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "policy_version": "1.0",
        "project_id": "engineering-ai",
        "autonomous_actions": ["read_repository"],
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
        "stop_conditions": [
            "authoritative source conflict",
            "approval boundary reached",
            "required validator failure",
        ],
        "retry_limit": 1,
    }


def make_state() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "state_revision": 1,
        "project_id": "engineering-ai",
        "current_gate": "006",
        "active_job_id": None,
        "repository_ref": {
            "branch": "gate-006-planner-executor-reviewer",
            "head_sha": None,
        },
        "architecture_baseline": "Gate 001",
        "effective_permissions": {
            "autonomous": ["read_repository"],
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
                "check_id": "gate006-local-role-smoke",
                "validation_class": "ADVISORY",
                "state": "NOT_RUN",
                "evidence_refs": [],
            },
            {
                "check_id": "physical-validation",
                "validation_class": "PHYSICAL",
                "state": "PHYSICAL_NOT_EXECUTED",
                "evidence_refs": [],
            },
        ],
        "next_admissible_action": "run Gate 006 local role-loop smoke",
    }


def make_job() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "job_id": "gate-006-local-role-smoke",
        "project_id": "engineering-ai",
        "gate_id": "006",
        "objective": "Read STATUS.md through the controlled Planner/Executor/Reviewer loop",
        "scope": ["read-only local role-loop smoke"],
        "out_of_scope": [
            "repository writes",
            "git mutation",
            "shell execution",
            "architecture changes",
        ],
        "requested_actions": ["read_repository"],
        "required_validators": [],
        "retry_limit": 1,
        "attempts": 0,
        "status": "QUEUED",
        "blocker": None,
    }


def main() -> int:
    filesystem = ReadOnlyFilesystemAdapter(ROOT, max_read_bytes=1_048_576)
    provider = OllamaProvider("http://127.0.0.1:11434")

    def read_repository(arguments: Mapping[str, Any]) -> ToolOutcome:
        path = arguments.get("path")
        if not isinstance(path, str) or not path.strip():
            return ToolOutcome(False, "read_repository requires a non-empty path")
        try:
            text = filesystem.read_text(path)
        except Exception as exc:
            return ToolOutcome(False, f"read_repository failed: {exc}")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return ToolOutcome(
            True,
            f"read {path} ({len(text)} characters)",
            (f"sha256:{path}:{digest}",),
        )

    loop = PlannerExecutorReviewerLoop(
        policy=make_policy(),
        state=make_state(),
        provider=provider,
        model_config=RoleModelConfig(
            model="gpt-oss:20b",
            reasoning_effort="medium",
            context_tokens=8192,
            max_output_tokens=2048,
            timeout_seconds=300.0,
        ),
        tool_specs={
            "read_repository": ModelToolSpec(
                name="read_repository",
                description=(
                    "Read one UTF-8 text file inside the configured repository root. "
                    "For this smoke test, inspect STATUS.md."
                ),
                parameters={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                    "additionalProperties": False,
                },
            )
        },
        tool_executors={"read_repository": read_repository},
        max_plan_steps=8,
        max_tool_calls=2,
        max_revisions=1,
    )

    result = loop.run(
        job=make_job(),
        user_task=(
            "Inspect STATUS.md using the read_repository tool. "
            "Base the review only on deterministic evidence and accept only if "
            "the controlled read completed successfully."
        ),
    )

    payload = {
        "state": result.state.value,
        "job_status": result.job["status"],
        "blocker": result.blocker,
        "revision_count": result.revision_count,
        "executed_actions": (
            list(result.execution.executed_actions) if result.execution else []
        ),
        "evidence_refs": (
            list(result.execution.evidence_refs) if result.execution else []
        ),
        "review_decision": (
            result.review.decision.value if result.review else None
        ),
        "model": "gpt-oss:20b",
        "reasoning": "medium",
        "context_tokens": 8192,
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2))

    return 0 if result.state.value == "COMPLETE" and result.job["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
