from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from engineering_ai.projects.buoycalc import BuoyCalcReadOnlyAdapter
from engineering_ai.projects.buoycalc_controlled import (
    BuoyCalcControlledEngineeringLoop,
    BuoyCalcControlledState,
    RuntimePrerequisiteStatus,
    _VALIDATOR_PROFILES,
    _VALIDATOR_SPECS,
)
from engineering_ai.projects.platavm import PlataVMReadOnlyAdapter
from engineering_ai.projects.platavm_controlled import (
    ControlledLoopState,
    PlataVMControlledEngineeringLoop,
)
from engineering_ai.tools import NetworkRequirement


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def init_repo(root: Path, origin: Path, files: dict[str, str]) -> None:
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
    git(root, "config", "user.email", "gate027@example.invalid")
    git(root, "config", "user.name", "Gate 027")
    git(root, "remote", "add", "origin", str(origin))
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))
    git(root, "add", ".")
    git(root, "commit", "-m", "gate027 offline fixture")
    git(root, "push", "-u", "origin", "main")


def platavm_fixture() -> dict[str, str]:
    return {
        "AGENTS.md": "# fixture governance\n",
        "Docs/PROJECT_STATUS.md": "# fixture status without stale pointers\n",
        "Docs/PROJECT_CONTROL.md": "# control\n",
        "Docs/PROJECT_MASTER.md": "# master\n",
        "Docs/ARCHITECTURE_BASELINE.md": "# V1.9\n",
        "Docs/OPEN_QUESTIONS.md": "# questions\n",
        "Docs/TRACEABILITY_V1_9.md": "# traceability\n",
        "Docs/CHRONOLOGY.md": "# chronology\n",
        "Docs/chronology/2026-09-20-gate027.md": "fixture\n",
        "Hardware/KiCad/PlataVM.kicad_pro": "(project)\n",
        "Hardware/KiCad/PlataVM.kicad_sch": "(schematic)\n",
        "Tools/repository_integrity.py": "print('Repository integrity: PASS')\n",
        "Tools/run_all_gates.py": "print('All registered semantic Gates: PASS')\n",
    }


def buoycalc_fixture() -> dict[str, str]:
    return {
        "AGENTS.md": (
            "# BuoyCalc fixture\n"
            "The only user-facing geometry with engineering meaning is the selected calculated X/Z shape.\n"
        ),
        "docs/OPTIMIZATION_PLAN.md": (
            "# Optimization\n"
            "Engineering physics lives only in the calculation/solver domain.\n"
            "UI, PDF, 2D and report layers render calculated data; they do not invent coordinates.\n"
        ),
        "RELEASE.md": (
            "# Release\n"
            "Запрещено создавать git tag `v1.0.0` или GitHub Release до явного подтверждения пользователя.\n"
            "segmentation = 0.20 m\n"
            "signed feedback budget = 64\n"
            "signed WeightWaterKgM semantics = unchanged\n"
            "Accepted signed candidate = exact deterministic fixed point\n"
            "renderers = presentation only\n"
            "3D = post-v1\n"
        ),
        "docs/note.md": "offline fixture\n",
        "Views/InfoPanel.cs": "presentation\n",
        "Services/MooringShapeSolver.cs": "solver fixture\n",
        "tools/scan-selected-shape-consumers.ps1": "Write-Host PASS\n",
        "tools/scan-report-store-consumers.ps1": "Write-Host PASS\n",
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="gate027-") as tmp:
        base = Path(tmp)
        pv_root = base / "platavm"
        pv_origin = base / "platavm-origin.git"
        pv_worktrees = base / "platavm-worktrees"
        pv_root.mkdir()
        pv_worktrees.mkdir()
        init_repo(pv_root, pv_origin, platavm_fixture())

        pv_before = git(pv_root, "rev-parse", "HEAD")
        pv_adapter = PlataVMReadOnlyAdapter(
            pv_root,
            python_executable=sys.executable,
            offline=True,
        )
        pv_snapshot = pv_adapter.snapshot()
        pv_validator_states = tuple(
            pv_adapter.run_validator(profile).state.value
            for profile in pv_adapter.validator_profiles
        )

        pv_loop = PlataVMControlledEngineeringLoop(
            pv_root,
            pv_worktrees,
            python_executable=sys.executable,
            offline=True,
        )
        pv_prep = pv_loop.prepare(
            worktree_name="offline",
            branch="engineering-ai/gate027-offline",
            base_ref="HEAD",
        )
        if pv_prep.state is not ControlledLoopState.WORKTREE_READY or pv_prep.session is None:
            raise RuntimeError(f"PlataVM offline prepare failed: {pv_prep}")
        pv_validation = pv_loop.validate(session=pv_prep.session)
        pv_loop.cleanup(pv_prep.session)
        pv_after = git(pv_root, "rev-parse", "HEAD")
        pv_status = git(pv_root, "status", "--porcelain")

        bc_root = base / "buoycalc"
        bc_origin = base / "buoycalc-origin.git"
        bc_worktrees = base / "buoycalc-worktrees"
        bc_root.mkdir()
        bc_worktrees.mkdir()
        init_repo(bc_root, bc_origin, buoycalc_fixture())

        bc_before = git(bc_root, "rev-parse", "HEAD")
        bc_snapshot = BuoyCalcReadOnlyAdapter(bc_root).snapshot()
        bc_loop = BuoyCalcControlledEngineeringLoop(
            bc_root,
            bc_worktrees,
            offline=True,
        )
        bc_prep = bc_loop.prepare(
            worktree_name="offline",
            branch="engineering-ai/buoycalc/gate027-offline",
            base_ref="HEAD",
        )
        if bc_prep.state is not BuoyCalcControlledState.WORKTREE_READY or bc_prep.session is None:
            raise RuntimeError(f"BuoyCalc offline prepare failed: {bc_prep}")

        bc_loop.runtime_prerequisites = lambda: RuntimePrerequisiteStatus(
            dotnet_executable=sys.executable,
            pwsh_executable=sys.executable,
            dotnet_sdk8_available=True,
            dotnet_sdks=("8.0.999 [synthetic]",),
            blockers=(),
        )
        bc_validation = bc_loop.validate(
            session=bc_prep.session,
            profiles=("buoycalc.dotnet_build",),
        )
        bc_loop.cleanup(bc_prep.session)
        bc_after = git(bc_root, "rev-parse", "HEAD")
        bc_status = git(bc_root, "status", "--porcelain")

        by_id = {spec.command_id: spec for spec in _VALIDATOR_SPECS}
        network_capable = sorted(
            command_id
            for command_id, spec in by_id.items()
            if spec.network_requirement is NetworkRequirement.NETWORK_CAPABLE
        )
        local_scan_profiles = {
            profile_id: all(
                by_id[step_id].network_requirement is NetworkRequirement.LOCAL_ONLY
                for step_id in _VALIDATOR_PROFILES[profile_id]
            )
            for profile_id in (
                "buoycalc.selected_shape_consumer_scan",
                "buoycalc.report_store_consumer_scan",
            )
        }

        blocked_step = bc_validation.profiles[0].steps[0]
        assertions = {
            "platavm_snapshot_no_conflict": not pv_snapshot.conflicts,
            "platavm_validators_pass": pv_validator_states == ("PASS", "PASS"),
            "platavm_controlled_offline_pass": (
                pv_validation.state is ControlledLoopState.READY_FOR_HUMAN_APPROVAL
            ),
            "platavm_primary_unchanged": pv_before == pv_after and not pv_status,
            "buoycalc_snapshot_invariants_pass": not bc_snapshot.invariant_violations,
            "buoycalc_restore_blocked": (
                bc_validation.state is BuoyCalcControlledState.BLOCKED_RUNTIME_PREREQUISITE
                and blocked_step.blocked
                and blocked_step.block_reason == "OFFLINE_NETWORK_REQUIRED"
                and blocked_step.exit_code is None
            ),
            "buoycalc_primary_unchanged": bc_before == bc_after and not bc_status,
            "buoycalc_local_scan_profiles_available": all(local_scan_profiles.values()),
            "restore_steps_network_classified": network_capable == [
                "buoycalc.restore_app",
                "buoycalc.restore_engineering_regression",
                "buoycalc.restore_validation_601",
            ],
        }
        if not all(assertions.values()):
            raise RuntimeError(f"Gate 027 smoke assertion failed: {assertions}")

        payload = {
            "gate": "027",
            "state": "PASS_OFFLINE_CONTINUATION_BOUNDARY",
            "assertions": assertions,
            "platavm": {
                "offline": True,
                "validator_states": pv_validator_states,
                "controlled_state": pv_validation.state.value,
                "primary_repository_unchanged": True,
            },
            "buoycalc": {
                "offline": True,
                "read_only_invariants_pass": True,
                "network_block_state": bc_validation.state.value,
                "blocked_step": blocked_step.step_id,
                "blocked_reason": blocked_step.block_reason,
                "blocked_exit_code": blocked_step.exit_code,
                "local_scan_profiles": local_scan_profiles,
                "primary_repository_unchanged": True,
            },
            "network_capable_commands": network_capable,
            "external_network_exercised": False,
            "release_authority": False,
            "fabrication_authority": False,
            "physical_validation": "PHYSICAL_NOT_EXECUTED",
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
