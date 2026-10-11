"""Controlled BuoyCalc engineering loop with fixed deterministic validation profiles."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from engineering_ai.projects.buoycalc import (
    BuoyCalcReadOnlyAdapter,
    RELEASE_STATE,
    SourceBoundaryClass,
)
from engineering_ai.tools import (
    AllowListedProcessRunner,
    CommandSpec,
    ControlledWorktreeAdapter,
    GitReadOnlyAdapter,
    NetworkRequirement,
    PatchApplication,
    PatchProposal,
    ToolAccessError,
    ToolExecutionError,
    WorktreeSession,
)


class BuoyCalcControlledState(str, Enum):
    BLOCKED_BASELINE = "BLOCKED_BASELINE"
    BLOCKED_RUNTIME_PREREQUISITE = "BLOCKED_RUNTIME_PREREQUISITE"
    WORKTREE_READY = "WORKTREE_READY"
    PATCH_APPLIED = "PATCH_APPLIED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    READY_FOR_HUMAN_APPROVAL = "READY_FOR_HUMAN_APPROVAL"


@dataclass(frozen=True)
class BuoyCalcWorktreePreparation:
    state: BuoyCalcControlledState
    blockers: tuple[str, ...]
    session: WorktreeSession | None = None


@dataclass(frozen=True)
class RuntimePrerequisiteStatus:
    dotnet_executable: str | None
    pwsh_executable: str | None
    dotnet_sdk8_available: bool
    dotnet_sdks: tuple[str, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class BuoyCalcPatchResult:
    state: BuoyCalcControlledState
    application: PatchApplication


@dataclass(frozen=True)
class ValidationStepEvidence:
    step_id: str
    ok: bool
    exit_code: int | None
    timed_out: bool
    truncated: bool
    stdout_sha256: str
    stderr_sha256: str
    network_requirement: str
    blocked: bool = False
    block_reason: str | None = None
    validation_class: str = "SOFTWARE_DETERMINISTIC"


@dataclass(frozen=True)
class ValidationProfileEvidence:
    profile_id: str
    steps: tuple[ValidationStepEvidence, ...]
    passed: bool


@dataclass(frozen=True)
class BuoyCalcValidationResult:
    state: BuoyCalcControlledState
    base_sha: str
    profiles: tuple[ValidationProfileEvidence, ...]
    tracked_state_unchanged: bool
    release_state: str
    offline: bool = False
    physical_validation: str = "PHYSICAL_NOT_EXECUTED"


def _pwsh_spec(command_id: str, script: str, *, timeout: float = 90.0) -> CommandSpec:
    return CommandSpec(
        command_id=command_id,
        executable="pwsh",
        fixed_args=(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            script,
        ),
        timeout_seconds=timeout,
        max_output_bytes=262_144,
        network_requirement=NetworkRequirement.LOCAL_ONLY,
    )


def _dotnet_spec(
    command_id: str,
    args: tuple[str, ...],
    *,
    network_requirement: NetworkRequirement,
    timeout: float = 300.0,
) -> CommandSpec:
    return CommandSpec(
        command_id=command_id,
        executable="dotnet",
        fixed_args=args,
        timeout_seconds=timeout,
        max_output_bytes=524_288,
        network_requirement=network_requirement,
    )


_VALIDATOR_SPECS: tuple[CommandSpec, ...] = (
    _dotnet_spec(
        "buoycalc.restore_app",
        ("restore", "BuoyCalc.Windows.csproj"),
        network_requirement=NetworkRequirement.NETWORK_CAPABLE,
    ),
    _dotnet_spec(
        "buoycalc.restore_engineering_regression",
        (
            "restore",
            "validation/BuoyCalc.EngineeringRegression/BuoyCalc.EngineeringRegression.csproj",
        ),
        network_requirement=NetworkRequirement.NETWORK_CAPABLE,
    ),
    _dotnet_spec(
        "buoycalc.build_release",
        (
            "build",
            "BuoyCalc.Windows.csproj",
            "--configuration",
            "Release",
            "--no-restore",
        ),
        network_requirement=NetworkRequirement.LOCAL_ONLY,
    ),
    _pwsh_spec("buoycalc.check_reportbuilder_usage", "tools/check-reportbuilder-usage.ps1"),
    _pwsh_spec("buoycalc.check_technical_report_path", "tools/check-technical-report-path.ps1"),
    _pwsh_spec(
        "buoycalc.check_selected_technical_report_boundary",
        "tools/check-selected-technical-report-boundary.ps1",
    ),
    _pwsh_spec("buoycalc.check_v1_release_freeze", "tools/check-v1-release-freeze.ps1"),
    _pwsh_spec(
        "buoycalc.check_windows_rc_packaging",
        "tools/check-windows-rc-packaging.ps1",
    ),
    _pwsh_spec("buoycalc.check_readmodel_boundary", "tools/check-readmodel-boundary.ps1"),
    _pwsh_spec(
        "buoycalc.check_user_engineering_report_read_model",
        "tools/check-user-engineering-report-read-model.ps1",
    ),
    _pwsh_spec(
        "buoycalc.check_user_pdf_typed_renderer",
        "tools/check-user-pdf-typed-renderer.ps1",
    ),
    _pwsh_spec("buoycalc.check_rc_smoke_ui_polish", "tools/check-rc-smoke-ui-polish.ps1"),
    _pwsh_spec("buoycalc.check_rc_smoke_round2", "tools/check-rc-smoke-round2.ps1"),
    _pwsh_spec(
        "buoycalc.check_repository_governance",
        "tools/check-repository-governance.ps1",
    ),
    _pwsh_spec(
        "buoycalc.scan_report_store_consumers_build",
        "tools/scan-report-store-consumers.ps1",
    ),
    _pwsh_spec(
        "buoycalc.check_report_store_consumer_map",
        "tools/check-report-store-consumer-map.ps1",
    ),
    _pwsh_spec(
        "buoycalc.check_selected_shape_consumer_map",
        "tools/check-selected-shape-consumer-map.ps1",
    ),
    _dotnet_spec(
        "buoycalc.engineering_regression",
        (
            "run",
            "--project",
            "validation/BuoyCalc.EngineeringRegression/BuoyCalc.EngineeringRegression.csproj",
            "--configuration",
            "Release",
            "--no-restore",
            "--",
            "--verify",
            "validation/BuoyCalc.EngineeringRegression/baselines/engineering-baseline.json",
        ),
        network_requirement=NetworkRequirement.LOCAL_ONLY,
        timeout=300.0,
    ),
    _pwsh_spec(
        "buoycalc.selected_shape_consumer_scan",
        "tools/scan-selected-shape-consumers.ps1",
    ),
    _pwsh_spec(
        "buoycalc.report_store_consumer_scan",
        "tools/scan-report-store-consumers.ps1",
    ),
    _dotnet_spec(
        "buoycalc.restore_validation_601",
        (
            "restore",
            "validation/BuoyCalc.PhysicalRejectionValidation/BuoyCalc.PhysicalRejectionValidation.csproj",
        ),
        network_requirement=NetworkRequirement.NETWORK_CAPABLE,
    ),
    _dotnet_spec(
        "buoycalc.build_validation_601",
        (
            "build",
            "validation/BuoyCalc.PhysicalRejectionValidation/BuoyCalc.PhysicalRejectionValidation.csproj",
            "--configuration",
            "Release",
            "--no-restore",
        ),
        network_requirement=NetworkRequirement.LOCAL_ONLY,
    ),
    _dotnet_spec(
        "buoycalc.run_validation_601",
        (
            "run",
            "--project",
            "validation/BuoyCalc.PhysicalRejectionValidation/BuoyCalc.PhysicalRejectionValidation.csproj",
            "--configuration",
            "Release",
            "--no-build",
            "--",
            "--output",
            "artifacts/validation-601-physical-rejection",
        ),
        network_requirement=NetworkRequirement.LOCAL_ONLY,
        timeout=300.0,
    ),
)

_VALIDATOR_PROFILES: dict[str, tuple[str, ...]] = {
    "buoycalc.dotnet_build": (
        "buoycalc.restore_app",
        "buoycalc.restore_engineering_regression",
        "buoycalc.build_release",
        "buoycalc.check_reportbuilder_usage",
        "buoycalc.check_technical_report_path",
        "buoycalc.check_selected_technical_report_boundary",
        "buoycalc.check_v1_release_freeze",
        "buoycalc.check_windows_rc_packaging",
        "buoycalc.check_readmodel_boundary",
        "buoycalc.check_user_engineering_report_read_model",
        "buoycalc.check_user_pdf_typed_renderer",
        "buoycalc.check_rc_smoke_ui_polish",
        "buoycalc.check_rc_smoke_round2",
        "buoycalc.check_repository_governance",
        "buoycalc.scan_report_store_consumers_build",
        "buoycalc.check_report_store_consumer_map",
        "buoycalc.check_selected_shape_consumer_map",
        "buoycalc.engineering_regression",
    ),
    "buoycalc.selected_shape_consumer_scan": (
        "buoycalc.selected_shape_consumer_scan",
    ),
    "buoycalc.report_store_consumer_scan": (
        "buoycalc.report_store_consumer_scan",
    ),
    "buoycalc.validation_601": (
        "buoycalc.restore_validation_601",
        "buoycalc.build_validation_601",
        "buoycalc.run_validation_601",
    ),
}


class BuoyCalcControlledEngineeringLoop:
    """Gate 015 controlled loop.

    No API for commit, push, PR creation/merge, release, packaging or physics
    changes is exposed.
    """

    def __init__(
        self,
        repository_root: str | Path,
        worktree_parent: str | Path,
        *,
        git_executable: str = "git",
        offline: bool = False,
    ) -> None:
        self._repository_root = Path(repository_root).resolve(strict=True)
        self._worktree_parent = Path(worktree_parent).resolve(strict=True)
        self._git_executable = git_executable
        self._offline = offline
        self._readonly = BuoyCalcReadOnlyAdapter(
            self._repository_root,
            git_executable=git_executable,
        )
        self._worktrees = ControlledWorktreeAdapter(
            self._repository_root,
            self._worktree_parent,
            git_executable=git_executable,
            branch_prefix="engineering-ai/buoycalc/",
        )

    @property
    def validator_profiles(self) -> tuple[str, ...]:
        return tuple(_VALIDATOR_PROFILES)

    @property
    def branch_prefix(self) -> str:
        return self._worktrees.branch_prefix

    @property
    def cleanup_events(self) -> tuple[dict[str, object], ...]:
        """Expose adapter-owned cleanup diagnostics without granting new authority."""
        return self._worktrees.cleanup_events

    def prepare(
        self,
        *,
        worktree_name: str,
        branch: str,
        base_ref: str = "HEAD",
    ) -> BuoyCalcWorktreePreparation:
        snapshot = self._readonly.snapshot()
        blockers: list[str] = []

        if snapshot.invariant_violations:
            blockers.append(
                "invariant violations: " + ", ".join(snapshot.invariant_violations)
            )
        if snapshot.git.branch != "main":
            blockers.append(f"primary branch must be main, got {snapshot.git.branch!r}")
        if snapshot.git.dirty:
            blockers.append("primary repository is dirty")
        if snapshot.git.origin_main_sha is None:
            blockers.append("origin/main is unavailable")
        elif snapshot.git.head_sha != snapshot.git.origin_main_sha:
            blockers.append(
                f"primary HEAD {snapshot.git.head_sha} != origin/main {snapshot.git.origin_main_sha}"
            )

        if blockers:
            return BuoyCalcWorktreePreparation(
                state=BuoyCalcControlledState.BLOCKED_BASELINE,
                blockers=tuple(blockers),
                session=None,
            )

        session = self._worktrees.create_worktree(
            worktree_name=worktree_name,
            branch=branch,
            base_ref=base_ref,
        )
        return BuoyCalcWorktreePreparation(
            state=BuoyCalcControlledState.WORKTREE_READY,
            blockers=(),
            session=session,
        )

    def apply_patch(
        self,
        *,
        session: WorktreeSession,
        proposal: PatchProposal,
        allowed_paths: tuple[str, ...],
    ) -> BuoyCalcPatchResult:
        boundary = BuoyCalcReadOnlyAdapter.classify_path(proposal.relative_path)
        if boundary is SourceBoundaryClass.GOVERNANCE:
            raise ToolAccessError(
                "Gate 015 ordinary controlled patch cannot modify BuoyCalc governance"
            )
        if boundary is SourceBoundaryClass.CALCULATION_CORE_CANDIDATE:
            raise ToolAccessError(
                "Gate 015 ordinary controlled patch cannot modify calculation-core/physics candidate paths"
            )

        application = self._worktrees.apply_exact_replacement(
            session=session,
            proposal=proposal,
            allowed_paths=allowed_paths,
        )
        return BuoyCalcPatchResult(
            state=BuoyCalcControlledState.PATCH_APPLIED,
            application=application,
        )

    def validate(
        self,
        *,
        session: WorktreeSession,
        profiles: tuple[str, ...] | None = None,
    ) -> BuoyCalcValidationResult:
        worktree = Path(session.worktree_root).resolve(strict=True)
        git = GitReadOnlyAdapter(worktree, git_executable=self._git_executable)
        runtime = self.runtime_prerequisites()
        if runtime.blockers:
            raise ToolExecutionError(
                "runtime prerequisites not satisfied: " + "; ".join(runtime.blockers)
            )

        before_head = self._required_output(git.head_sha(), "before HEAD")
        before_diff = self._required_output(git.diff_worktree(), "before worktree diff")
        before_cached = self._required_output(git.diff_cached(), "before cached diff")

        selected = profiles or self.validator_profiles
        unknown = tuple(profile for profile in selected if profile not in _VALIDATOR_PROFILES)
        if unknown:
            raise ToolAccessError(f"validator profile is not allow-listed: {unknown[0]}")

        specs = self._resolved_validator_specs(runtime)
        runner = AllowListedProcessRunner(
            specs,
            root=worktree,
            offline=self._offline,
        )
        profile_evidence: list[ValidationProfileEvidence] = []
        all_steps_pass = True
        offline_blocked = False

        for profile_id in selected:
            steps: list[ValidationStepEvidence] = []
            profile_pass = True
            for step_id in _VALIDATOR_PROFILES[profile_id]:
                spec = specs[step_id]
                try:
                    result = runner.run(step_id)
                except ToolAccessError:
                    if (
                        self._offline
                        and spec.network_requirement
                        is NetworkRequirement.NETWORK_CAPABLE
                    ):
                        empty_sha = hashlib.sha256(b"").hexdigest()
                        steps.append(
                            ValidationStepEvidence(
                                step_id=step_id,
                                ok=False,
                                exit_code=None,
                                timed_out=False,
                                truncated=False,
                                stdout_sha256=empty_sha,
                                stderr_sha256=empty_sha,
                                network_requirement=spec.network_requirement.value,
                                blocked=True,
                                block_reason="OFFLINE_NETWORK_REQUIRED",
                            )
                        )
                        profile_pass = False
                        all_steps_pass = False
                        offline_blocked = True
                        break
                    raise

                step = ValidationStepEvidence(
                    step_id=step_id,
                    ok=result.ok,
                    exit_code=result.exit_code,
                    timed_out=result.timed_out,
                    truncated=result.truncated,
                    stdout_sha256=hashlib.sha256(
                        result.stdout.encode("utf-8")
                    ).hexdigest(),
                    stderr_sha256=hashlib.sha256(
                        result.stderr.encode("utf-8")
                    ).hexdigest(),
                    network_requirement=spec.network_requirement.value,
                )
                steps.append(step)
                if not result.ok:
                    profile_pass = False
                    all_steps_pass = False
                    break

            profile_evidence.append(
                ValidationProfileEvidence(
                    profile_id=profile_id,
                    steps=tuple(steps),
                    passed=profile_pass,
                )
            )
            if not profile_pass:
                break

        after_head = self._required_output(git.head_sha(), "after HEAD")
        after_diff = self._required_output(git.diff_worktree(), "after worktree diff")
        after_cached = self._required_output(git.diff_cached(), "after cached diff")
        tracked_state_unchanged = (
            before_head == after_head
            and before_diff == after_diff
            and before_cached == after_cached
        )

        if offline_blocked:
            state = BuoyCalcControlledState.BLOCKED_RUNTIME_PREREQUISITE
        elif all_steps_pass and tracked_state_unchanged:
            state = BuoyCalcControlledState.READY_FOR_HUMAN_APPROVAL
        else:
            state = BuoyCalcControlledState.VALIDATION_FAILED

        return BuoyCalcValidationResult(
            state=state,
            base_sha=session.base_sha,
            profiles=tuple(profile_evidence),
            tracked_state_unchanged=tracked_state_unchanged,
            release_state=RELEASE_STATE,
            offline=self._offline,
        )

    def runtime_prerequisites(self) -> RuntimePrerequisiteStatus:
        dotnet = self._resolve_runtime_executable("dotnet")
        pwsh = self._resolve_runtime_executable("pwsh")
        blockers: list[str] = []
        sdks: tuple[str, ...] = ()

        if dotnet is None:
            blockers.append("dotnet executable not found")
        else:
            result = subprocess.run(
                [dotnet, "--list-sdks"],
                cwd=self._repository_root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                timeout=30.0,
                check=False,
            )
            if result.returncode != 0:
                blockers.append("dotnet --list-sdks failed")
            else:
                sdks = tuple(
                    line.strip()
                    for line in result.stdout.splitlines()
                    if line.strip()
                )
                if not any(line.startswith("8.") for line in sdks):
                    blockers.append(".NET 8 SDK not found")

        if pwsh is None:
            blockers.append("pwsh executable not found")

        return RuntimePrerequisiteStatus(
            dotnet_executable=dotnet,
            pwsh_executable=pwsh,
            dotnet_sdk8_available=any(line.startswith("8.") for line in sdks),
            dotnet_sdks=sdks,
            blockers=tuple(blockers),
        )

    def _resolved_validator_specs(
        self,
        runtime: RuntimePrerequisiteStatus,
    ) -> dict[str, CommandSpec]:
        if runtime.blockers:
            raise ToolExecutionError(
                "runtime prerequisites not satisfied: " + "; ".join(runtime.blockers)
            )
        assert runtime.dotnet_executable is not None
        assert runtime.pwsh_executable is not None
        specs: dict[str, CommandSpec] = {}
        for spec in _VALIDATOR_SPECS:
            executable = spec.executable
            if executable == "dotnet":
                executable = runtime.dotnet_executable
            elif executable == "pwsh":
                executable = runtime.pwsh_executable
            specs[spec.command_id] = CommandSpec(
                command_id=spec.command_id,
                executable=executable,
                fixed_args=spec.fixed_args,
                timeout_seconds=spec.timeout_seconds,
                max_output_bytes=spec.max_output_bytes,
                network_requirement=spec.network_requirement,
            )
        return specs

    @staticmethod
    def _resolve_runtime_executable(name: str) -> str | None:
        found = shutil.which(name)
        if found:
            return str(Path(found).resolve(strict=True))

        candidates: list[Path] = []
        if os.name == "nt":
            program_files = os.environ.get("ProgramFiles")
            if program_files:
                if name == "dotnet":
                    candidates.append(Path(program_files) / "dotnet" / "dotnet.exe")
                elif name == "pwsh":
                    candidates.append(
                        Path(program_files) / "PowerShell" / "7" / "pwsh.exe"
                    )

        for candidate in candidates:
            if candidate.is_file():
                return str(candidate.resolve(strict=True))
        return None

    def cleanup(self, session: WorktreeSession) -> None:
        self._worktrees.cleanup(session)

    def cleanup_disposable_generated(self, session: WorktreeSession) -> None:
        self._worktrees.cleanup_disposable_generated(session)

    @staticmethod
    def assert_no_remote_or_release_api(instance: object) -> None:
        forbidden = (
            "commit",
            "push",
            "open_pr",
            "merge_pr",
            "release",
            "package_release",
            "publish",
            "create_tag",
            "authorize_release",
            "fabricate",
        )
        for name in forbidden:
            if hasattr(instance, name):
                raise ToolAccessError(f"forbidden Gate 015 API exposed: {name}")

    @staticmethod
    def _required_output(result, label: str) -> str:
        if not result.ok:
            raise ToolExecutionError(f"unable to capture {label}")
        return result.stdout
