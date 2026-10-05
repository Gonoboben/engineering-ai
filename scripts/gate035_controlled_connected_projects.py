from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


OPENING_PASS = "PASS_GATE035_OPENING_CONTRACT"
OPENING_FAIL = "FAIL_GATE035_OPENING_CONTRACT"

PLATAVM_MAIN = "dcba77466d4800c0e7a336a2771684e066f845db"
PLATAVM_HEAD = "11e746cfea7f9200415cf817b6cde928b6a2651a"
BUOYCALC_MAIN = "325aee5ee3a9f64413e416a1206fc4e296d9723f"


def opening_fixture() -> dict[str, Any]:
    return {
        "control": {
            "hidden_chat_context_required": False,
            "connected_project_remote_mutations": 0,
            "connected_project_primary_state_changed": False,
            "project_cross_contamination": False,
            "architecture_changed": False,
            "physics_changed": False,
            "validator_weakened": False,
            "authority_expanded": False,
            "core_runtime_changed": False,
            "automatic_approval": False,
        },
        "platavm": {
            "project_id": "platavm",
            "main_sha": PLATAVM_MAIN,
            "issue": 99,
            "pr": 100,
            "branch": "agent/pcb-e-aux-hardware-current-v1-9",
            "head_sha": PLATAVM_HEAD,
            "local_repository_integrity": "PASS",
            "local_semantic_gates": "PASS",
            "tracked_state_unchanged": True,
            "native_current_head": "CANCELLED",
            "native_promoted_to_pass": False,
            "ready_for_review": False,
            "ready_for_merge": False,
            "package_set": "NOT_READY",
            "fabrication": "NOT_GRANTED",
            "physical": "NOT_EXECUTED",
            "population": "PROTOTYPE_BASIS_ONLY_NOT_RELEASED / UNDECIDED",
            "series": "NOT_GRANTED",
            "expected_disposition":
                "CONTROLLED_USE_PASS / PRODUCT_STATE_BLOCKED_NATIVE_EVIDENCE",
        },
        "buoycalc": {
            "project_id": "buoycalc",
            "main_sha": BUOYCALC_MAIN,
            "main_matches_origin": True,
            "local_profiles": "PASS",
            "tracked_state_unchanged": True,
            "release_status": "NOT READY FOR v1.0",
            "release_authorized": False,
            "manual_windows_rc_smoke": False,
            "physics_changed": False,
            "pr628_modified": False,
            "handoff_mode": "EXPERIMENTAL_VALIDATION_ONLY",
            "operational_handoff_authorized": False,
            "expected_disposition":
                "CONTROLLED_USE_PASS / PRODUCT_RELEASE_NOT_READY",
        },
    }


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    control = payload["control"]
    platavm = payload["platavm"]
    buoycalc = payload["buoycalc"]

    if control["hidden_chat_context_required"]:
        errors.append("hidden chat context is required")
    if control["connected_project_remote_mutations"] != 0:
        errors.append("connected-project remote mutation observed")
    for key in (
        "connected_project_primary_state_changed",
        "project_cross_contamination",
        "architecture_changed",
        "physics_changed",
        "validator_weakened",
        "authority_expanded",
        "core_runtime_changed",
        "automatic_approval",
    ):
        if control[key]:
            errors.append(f"forbidden control transition: {key}")

    if platavm["project_id"] != "platavm":
        errors.append("PlataVM project identity lost")
    if buoycalc["project_id"] != "buoycalc":
        errors.append("BuoyCalc project identity lost")
    if platavm["project_id"] == buoycalc["project_id"]:
        errors.append("project identities cross-contaminated")

    if platavm["main_sha"] != PLATAVM_MAIN:
        errors.append("PlataVM audited main snapshot changed")
    if platavm["head_sha"] != PLATAVM_HEAD:
        errors.append("PlataVM audited active head changed")
    if platavm["issue"] != 99 or platavm["pr"] != 100:
        errors.append("PlataVM active Issue/PR identity changed")
    if platavm["local_repository_integrity"] != "PASS":
        errors.append("PlataVM repository-integrity local result is not PASS")
    if platavm["local_semantic_gates"] != "PASS":
        errors.append("PlataVM semantic local result is not PASS")
    if not platavm["tracked_state_unchanged"]:
        errors.append("PlataVM validation changed tracked state")

    native_state = platavm["native_current_head"]
    if native_state != "PASS":
        if platavm["native_promoted_to_pass"]:
            errors.append("PlataVM non-PASS native evidence was promoted")
        if platavm["ready_for_review"] or platavm["ready_for_merge"]:
            errors.append("PlataVM readiness promoted without native PASS")

    expected_platavm = {
        "package_set": "NOT_READY",
        "fabrication": "NOT_GRANTED",
        "physical": "NOT_EXECUTED",
        "population": "PROTOTYPE_BASIS_ONLY_NOT_RELEASED / UNDECIDED",
        "series": "NOT_GRANTED",
    }
    for key, expected in expected_platavm.items():
        if platavm[key] != expected:
            errors.append(f"PlataVM authority barrier changed: {key}")

    if buoycalc["main_sha"] != BUOYCALC_MAIN:
        errors.append("BuoyCalc audited main snapshot changed")
    if not buoycalc["main_matches_origin"]:
        errors.append("BuoyCalc main no longer matches origin/main")
    if buoycalc["local_profiles"] != "PASS":
        errors.append("BuoyCalc controlled local profiles are not PASS")
    if not buoycalc["tracked_state_unchanged"]:
        errors.append("BuoyCalc validation changed tracked state")
    if buoycalc["release_status"] != "NOT READY FOR v1.0":
        errors.append("BuoyCalc release disposition was promoted")
    if buoycalc["release_authorized"]:
        errors.append("BuoyCalc release authority was granted")
    if buoycalc["manual_windows_rc_smoke"]:
        errors.append("BuoyCalc manual RC smoke was invented")
    if buoycalc["physics_changed"]:
        errors.append("BuoyCalc physics changed inside Gate 035")
    if buoycalc["pr628_modified"]:
        errors.append("BuoyCalc PR #628 was modified by Gate 035")
    if buoycalc["handoff_mode"] != "EXPERIMENTAL_VALIDATION_ONLY":
        errors.append("BuoyCalc Gate 035 use exceeded experimental scope")
    if buoycalc["operational_handoff_authorized"]:
        errors.append("BuoyCalc operational handoff was invented")

    passed = not errors
    return {
        "state": OPENING_PASS if passed else OPENING_FAIL,
        "passed": passed,
        "errors": errors,
        "project_dispositions": {
            "platavm": platavm["expected_disposition"],
            "buoycalc": buoycalc["expected_disposition"],
        },
        "false_pass": bool(errors),
        "connected_project_remote_mutations":
            control["connected_project_remote_mutations"],
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
        "release_authorization": "NOT_GRANTED",
        "fabrication_authorization": "NOT_GRANTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        help="optional observed Gate 035 JSON payload; defaults to opening self-test fixture",
    )
    args = parser.parse_args()

    payload = (
        json.loads(args.input.read_text(encoding="utf-8"))
        if args.input
        else opening_fixture()
    )
    result = evaluate(copy.deepcopy(payload))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
