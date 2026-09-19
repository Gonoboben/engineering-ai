"""Controlled PlataVM engineering loop built on Gate 012 read-only evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from engineering_ai.projects.platavm import PlataVMReadOnlyAdapter, PlataVMValidatorResult
from engineering_ai.tools import (
    ControlledWorktreeAdapter,
    PatchApplication,
    PatchProposal,
    ToolAccessError,
    WorktreeSession,
)


class ControlledLoopState(str, Enum):
    BLOCKED_SOURCE_CONFLICT = "BLOCKED_SOURCE_CONFLICT"
    WORKTREE_READY = "WORKTREE_READY"
    PATCH_APPLIED = "PATCH_APPLIED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    READY_FOR_HUMAN_APPROVAL = "READY_FOR_HUMAN_APPROVAL"


@dataclass(frozen=True)
class WorktreePreparation:
    state: ControlledLoopState
    source_conflicts: tuple[str, ...]
    session: WorktreeSession | None = None


@dataclass(frozen=True)
class ControlledPatchResult:
    state: ControlledLoopState
    application: PatchApplication


@dataclass(frozen=True)
class ControlledValidationResult:
    state: ControlledLoopState
    validators: tuple[PlataVMValidatorResult, ...]


class PlataVMControlledEngineeringLoop:
    """Gate 013 controlled local loop.

    It never commits, pushes, opens PRs, merges, or changes release/fabrication
    state. All writes are limited to adapter-created isolated worktrees.
    """

    def __init__(
        self,
        repository_root: str | Path,
        worktree_parent: str | Path,
        *,
        python_executable: str,
        git_executable: str = "git",
    ) -> None:
        self._repository_root = Path(repository_root).resolve(strict=True)
        self._worktree_parent = Path(worktree_parent).resolve(strict=True)
        self._python = python_executable
        self._git_executable = git_executable
        self._readonly = PlataVMReadOnlyAdapter(
            self._repository_root,
            python_executable=python_executable,
            git_executable=git_executable,
        )
        self._worktrees = ControlledWorktreeAdapter(
            self._repository_root,
            self._worktree_parent,
            git_executable=git_executable,
            branch_prefix="engineering-ai/",
        )

    def prepare(
        self,
        *,
        worktree_name: str,
        branch: str,
        base_ref: str = "HEAD",
    ) -> WorktreePreparation:
        snapshot = self._readonly.snapshot()
        if snapshot.conflicts:
            return WorktreePreparation(
                state=ControlledLoopState.BLOCKED_SOURCE_CONFLICT,
                source_conflicts=snapshot.conflicts,
                session=None,
            )

        session = self._worktrees.create_worktree(
            worktree_name=worktree_name,
            branch=branch,
            base_ref=base_ref,
        )
        return WorktreePreparation(
            state=ControlledLoopState.WORKTREE_READY,
            source_conflicts=(),
            session=session,
        )

    def apply_patch(
        self,
        *,
        session: WorktreeSession,
        proposal: PatchProposal,
        allowed_paths: tuple[str, ...],
    ) -> ControlledPatchResult:
        application = self._worktrees.apply_exact_replacement(
            session=session,
            proposal=proposal,
            allowed_paths=allowed_paths,
        )
        return ControlledPatchResult(
            state=ControlledLoopState.PATCH_APPLIED,
            application=application,
        )

    def validate(
        self,
        *,
        session: WorktreeSession,
    ) -> ControlledValidationResult:
        adapter = PlataVMReadOnlyAdapter(
            session.worktree_root,
            python_executable=self._python,
            git_executable=self._git_executable,
        )
        results = tuple(
            adapter.run_validator(profile_id)
            for profile_id in adapter.validator_profiles
        )
        if all(result.state.value == "PASS" for result in results):
            state = ControlledLoopState.READY_FOR_HUMAN_APPROVAL
        else:
            state = ControlledLoopState.VALIDATION_FAILED
        return ControlledValidationResult(state=state, validators=results)

    def cleanup(self, session: WorktreeSession) -> None:
        self._worktrees.cleanup(session)

    @property
    def branch_prefix(self) -> str:
        return self._worktrees.branch_prefix

    def assert_no_remote_mutation_api(self) -> None:
        forbidden = (
            "commit",
            "push",
            "open_pr",
            "merge_pr",
            "release",
            "fabricate",
        )
        for name in forbidden:
            if hasattr(self, name):
                raise ToolAccessError(f"forbidden Gate 013 API exposed: {name}")
