"""Deterministic schema and semantic validation for Engineering AI records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPOSITORY_ROOT / "schemas"

GLOBAL_APPROVAL_OR_FORBID_ACTIONS = {
    "architecture_change",
    "physics_change",
    "destructive_action",
    "fabrication_authorization",
    "release_authorization",
    "external_disclosure",
    "validator_weakening",
    "scope_expansion",
}


class SemanticValidationError(ValueError):
    """Raised when a structurally valid record violates control-plane semantics."""


def load_schema(schema_name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / schema_name
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def check_all_schemas() -> None:
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        with path.open("r", encoding="utf-8") as handle:
            Draft202012Validator.check_schema(json.load(handle))


def validate_instance(schema_name: str, instance: dict[str, Any]) -> None:
    schema = load_schema(schema_name)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(instance)

    if schema_name == "project-policy.schema.json":
        _validate_policy_semantics(instance)
    elif schema_name == "job.schema.json":
        _validate_job_semantics(instance)
    elif schema_name == "project-state.schema.json":
        _validate_state_semantics(instance)


def _validate_disjoint_permissions(
    autonomous: set[str], approval_required: set[str], forbidden: set[str]
) -> None:
    overlaps = {
        "autonomous/approval_required": autonomous & approval_required,
        "autonomous/forbidden": autonomous & forbidden,
        "approval_required/forbidden": approval_required & forbidden,
    }
    conflicts = {name: values for name, values in overlaps.items() if values}
    if conflicts:
        raise SemanticValidationError(f"permission classes overlap: {conflicts}")


def _validate_policy_semantics(policy: dict[str, Any]) -> None:
    autonomous = set(policy["autonomous_actions"])
    approval_required = set(policy["approval_required_actions"])
    forbidden = set(policy["forbidden_actions"])

    _validate_disjoint_permissions(autonomous, approval_required, forbidden)

    unsafe_autonomous = autonomous & GLOBAL_APPROVAL_OR_FORBID_ACTIONS
    if unsafe_autonomous:
        raise SemanticValidationError(
            "global approval-boundary actions cannot be autonomous: "
            f"{sorted(unsafe_autonomous)}"
        )

    uncovered = GLOBAL_APPROVAL_OR_FORBID_ACTIONS - (approval_required | forbidden)
    if uncovered:
        raise SemanticValidationError(
            "global approval-boundary actions must be approval-required or forbidden: "
            f"{sorted(uncovered)}"
        )


def _validate_job_semantics(job: dict[str, Any]) -> None:
    if job["attempts"] > job["retry_limit"]:
        raise SemanticValidationError(
            f"attempts ({job['attempts']}) exceed retry_limit ({job['retry_limit']})"
        )


def _validate_state_semantics(state: dict[str, Any]) -> None:
    permissions = state["effective_permissions"]
    autonomous = set(permissions["autonomous"])
    approval_required = set(permissions["approval_required"])
    forbidden = set(permissions["forbidden"])

    _validate_disjoint_permissions(autonomous, approval_required, forbidden)

    unsafe_autonomous = autonomous & GLOBAL_APPROVAL_OR_FORBID_ACTIONS
    if unsafe_autonomous:
        raise SemanticValidationError(
            "effective state cannot make approval-boundary actions autonomous: "
            f"{sorted(unsafe_autonomous)}"
        )
