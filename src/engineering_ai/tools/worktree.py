"""Controlled isolated Git worktree writes with exact-content preconditions."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from engineering_ai.tools.common import ToolAccessError, ToolExecutionError
from engineering_ai.tools.git import GitReadOnlyAdapter


_BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")


@dataclass(frozen=True)
class PatchProposal:
    relative_path: str
    expected_sha256: str
    new_content: str
    rationale: str

    def __post_init__(self) -> None:
        if not self.relative_path.strip():
            raise ValueError("relative_path must be non-empty")
        if not re.fullmatch(r"[0-9a-f]{64}", self.expected_sha256):
            raise ValueError("expected_sha256 must be lowercase 64-hex SHA-256")
        if not self.rationale.strip():
            raise ValueError("rationale must be non-empty")


@dataclass(frozen=True)
class WorktreeSession:
    repository_root: str
    worktree_root: str
    branch: str
    base_sha: str


@dataclass(frozen=True)
class PatchApplication:
    relative_path: str
    before_sha256: str
    after_sha256: str
    diff: str


class ControlledWorktreeAdapter:
    """Narrow local write adapter limited to adapter-created isolated worktrees."""

    def __init__(
        self,
        repository_root: str | Path,
        worktree_parent: str | Path,
        *,
        git_executable: str = "git",
        branch_prefix: str = "engineering-ai/",
        max_write_bytes: int = 1_048_576,
    ) -> None:
        if not branch_prefix or not branch_prefix.endswith("/"):
            raise ValueError("branch_prefix must be non-empty and end with '/'")
        if max_write_bytes <= 0:
            raise ValueError("max_write_bytes must be positive")

        self._repo = Path(repository_root).resolve(strict=True)
        self._parent = Path(worktree_parent).resolve(strict=True)
        if not self._repo.is_dir() or not self._parent.is_dir():
            raise ValueError("repository_root and worktree_parent must be directories")

        found = shutil.which(git_executable)
        if found is None:
            raise ToolExecutionError(f"git executable not found: {git_executable}")
        self._git = Path(found).resolve(strict=True)
        self._branch_prefix = branch_prefix
        self._max_write_bytes = max_write_bytes
        self._primary_git = GitReadOnlyAdapter(self._repo, git_executable=git_executable)
        self._sessions: dict[str, WorktreeSession] = {}

    @property
    def branch_prefix(self) -> str:
        return self._branch_prefix

    def create_worktree(
        self,
        *,
        worktree_name: str,
        branch: str,
        base_ref: str = "HEAD",
    ) -> WorktreeSession:
        self._validate_branch(branch)
        if not branch.startswith(self._branch_prefix):
            raise ToolAccessError(
                f"branch must start with controlled prefix {self._branch_prefix!r}"
            )
        name = self._validate_worktree_name(worktree_name)
        self._require_primary_clean()

        base = self._primary_git.ref_sha(base_ref)
        if not base.ok:
            raise ToolExecutionError(f"cannot resolve base ref: {base_ref}")
        base_sha = base.stdout.strip()

        destination = self._parent / name
        if destination.exists() or destination.is_symlink():
            raise ToolAccessError(f"worktree destination already exists: {destination}")
        self._assert_under_parent(destination.parent.resolve(strict=True))

        result = self._run_git(
            ["worktree", "add", "-b", branch, str(destination), base_sha],
            operation="git.worktree_add",
        )
        if result.returncode != 0:
            raise ToolExecutionError(
                f"git worktree add failed: {result.stderr.strip() or result.stdout.strip()}"
            )

        resolved = destination.resolve(strict=True)
        self._assert_under_parent(resolved)
        session = WorktreeSession(
            repository_root=str(self._repo),
            worktree_root=str(resolved),
            branch=branch,
            base_sha=base_sha,
        )
        self._sessions[str(resolved)] = session
        return session

    def apply_exact_replacement(
        self,
        *,
        session: WorktreeSession,
        proposal: PatchProposal,
        allowed_paths: tuple[str, ...],
    ) -> PatchApplication:
        worktree = self._require_session(session)
        allowed = {self._normalize_relative_path(item) for item in allowed_paths}
        target_rel = self._normalize_relative_path(proposal.relative_path)
        if target_rel not in allowed:
            raise ToolAccessError(f"patch target is not allow-listed: {target_rel}")

        new_bytes = proposal.new_content.encode("utf-8")
        if len(new_bytes) > self._max_write_bytes:
            raise ToolAccessError("new content exceeds max_write_bytes")

        target = worktree / Path(target_rel)
        if not target.exists():
            raise ToolExecutionError("Gate 013 replacement target must already exist")
        if target.is_symlink():
            raise ToolAccessError("symlink patch targets are prohibited")
        resolved = target.resolve(strict=True)
        self._assert_under_worktree(resolved, worktree)
        if not resolved.is_file():
            raise ToolExecutionError("patch target must be a regular file")

        before_bytes = resolved.read_bytes()
        before_sha = hashlib.sha256(before_bytes).hexdigest()
        if before_sha != proposal.expected_sha256:
            raise ToolAccessError(
                f"stale patch proposal: expected {proposal.expected_sha256}, actual {before_sha}"
            )

        fd, temp_name = tempfile.mkstemp(
            prefix=f".{resolved.name}.engineering-ai-",
            dir=str(resolved.parent),
        )
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(new_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            temp_path = Path(temp_name)
            if temp_path.is_symlink():
                raise ToolAccessError("temporary patch path unexpectedly became a symlink")
            os.replace(temp_path, resolved)
        finally:
            temp_path = Path(temp_name)
            if temp_path.exists():
                temp_path.unlink()

        after_sha = hashlib.sha256(resolved.read_bytes()).hexdigest()
        diff = GitReadOnlyAdapter(worktree).diff_worktree()
        if not diff.ok:
            raise ToolExecutionError("unable to capture worktree diff after patch")
        return PatchApplication(
            relative_path=target_rel,
            before_sha256=before_sha,
            after_sha256=after_sha,
            diff=diff.stdout,
        )

    def cleanup(self, session: WorktreeSession) -> None:
        """Remove an adapter-created worktree only when it is restored clean.

        The controlled branch is deleted only when it still points exactly to
        the original base SHA, proving it contains no unique commit.
        """

        worktree = self._require_session(session)
        git = GitReadOnlyAdapter(worktree)
        status = git.status()
        if not status.ok or self._status_is_dirty(status.stdout):
            raise ToolAccessError("refusing cleanup of dirty controlled worktree")
        head = git.head_sha()
        if not head.ok or head.stdout.strip() != session.base_sha:
            raise ToolAccessError("refusing cleanup: worktree HEAD differs from base SHA")

        result = self._run_git(
            ["worktree", "remove", str(worktree)],
            operation="git.worktree_remove",
        )
        if result.returncode != 0:
            raise ToolExecutionError(
                f"git worktree remove failed: {result.stderr.strip() or result.stdout.strip()}"
            )

        branch_sha = self._primary_git.ref_sha(session.branch)
        if not branch_sha.ok or branch_sha.stdout.strip() != session.base_sha:
            raise ToolAccessError("refusing controlled branch cleanup: branch moved")
        delete = self._run_git(
            ["branch", "-D", session.branch],
            operation="git.branch_delete_controlled",
        )
        if delete.returncode != 0:
            raise ToolExecutionError(
                f"controlled branch delete failed: {delete.stderr.strip() or delete.stdout.strip()}"
            )
        self._sessions.pop(str(worktree), None)

    def cleanup_disposable_generated(self, session: WorktreeSession) -> None:
        """Remove an adapter-owned disposable worktree with generated untracked files.

        This is permitted only when HEAD remains exactly at the original base SHA
        and both tracked worktree/cached diffs are empty. It may discard generated
        untracked build artifacts, but never tracked project changes or commits.
        """

        worktree = self._require_session(session)
        git = GitReadOnlyAdapter(worktree)
        head = git.head_sha()
        diff = git.diff_worktree()
        cached = git.diff_cached()
        if not head.ok or head.stdout.strip() != session.base_sha:
            raise ToolAccessError(
                "refusing disposable cleanup: worktree HEAD differs from base SHA"
            )
        if not diff.ok or not cached.ok:
            raise ToolExecutionError(
                "unable to verify tracked state before disposable cleanup"
            )
        if diff.stdout or cached.stdout:
            raise ToolAccessError(
                "refusing disposable cleanup: tracked worktree state is not clean"
            )

        result = self._run_git(
            ["worktree", "remove", "--force", str(worktree)],
            operation="git.worktree_remove_disposable",
        )
        if result.returncode != 0:
            raise ToolExecutionError(
                "git disposable worktree remove failed: "
                + (result.stderr.strip() or result.stdout.strip())
            )

        branch_sha = self._primary_git.ref_sha(session.branch)
        if not branch_sha.ok or branch_sha.stdout.strip() != session.base_sha:
            raise ToolAccessError(
                "refusing disposable branch cleanup: branch moved"
            )
        delete = self._run_git(
            ["branch", "-D", session.branch],
            operation="git.branch_delete_disposable_controlled",
        )
        if delete.returncode != 0:
            raise ToolExecutionError(
                "disposable controlled branch delete failed: "
                + (delete.stderr.strip() or delete.stdout.strip())
            )
        self._sessions.pop(str(worktree), None)

    def _require_primary_clean(self) -> None:
        result = self._primary_git.status()
        if not result.ok:
            raise ToolExecutionError("unable to inspect primary repository status")
        if self._status_is_dirty(result.stdout):
            raise ToolAccessError("primary repository must be clean before worktree creation")

    @staticmethod
    def _status_is_dirty(status_text: str) -> bool:
        return any(
            line.strip() and not line.startswith("## ")
            for line in status_text.splitlines()
        )

    def _require_session(self, session: WorktreeSession) -> Path:
        root = Path(session.worktree_root).resolve(strict=True)
        known = self._sessions.get(str(root))
        if known != session:
            raise ToolAccessError("unknown or non-adapter-created worktree session")
        self._assert_under_parent(root)
        return root

    def _validate_branch(self, branch: str) -> None:
        if (
            not _BRANCH_RE.fullmatch(branch)
            or branch.startswith("-")
            or ".." in branch
            or branch.endswith("/")
        ):
            raise ToolAccessError(f"unsafe controlled branch name: {branch!r}")

    @staticmethod
    def _validate_worktree_name(name: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name):
            raise ToolAccessError(f"unsafe worktree name: {name!r}")
        return name

    @staticmethod
    def _normalize_relative_path(value: str) -> str:
        path = Path(value)
        if path.is_absolute() or not value.strip():
            raise ToolAccessError("patch path must be a non-empty relative path")
        if any(part in {"", ".", ".."} for part in path.parts):
            raise ToolAccessError(f"unsafe patch path: {value!r}")
        return path.as_posix()

    def _assert_under_parent(self, path: Path) -> None:
        try:
            path.relative_to(self._parent)
        except ValueError as exc:
            raise ToolAccessError(f"worktree path escapes configured parent: {path}") from exc

    @staticmethod
    def _assert_under_worktree(path: Path, worktree: Path) -> None:
        try:
            path.relative_to(worktree)
        except ValueError as exc:
            raise ToolAccessError(f"patch path escapes worktree root: {path}") from exc

    def _run_git(self, args: list[str], *, operation: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self._git), "--no-pager", *args],
            cwd=self._repo,
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
