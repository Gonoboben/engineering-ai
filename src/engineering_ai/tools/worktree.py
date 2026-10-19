"""Controlled isolated Git worktree writes with exact-content preconditions."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import time
import subprocess
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
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
        # Bounded, non-authoritative cleanup diagnostics for Gate 036 evidence.
        self._cleanup_events: list[dict[str, object]] = []
        self._session_metadata: dict[str, Path] = {}
        self._disposable_proofs: dict[str, str] = {}
        common = self._run_git(
            ["rev-parse", "--path-format=absolute", "--git-common-dir"],
            operation="git.cleanup_common_dir",
        )
        if common.returncode:
            raise ToolExecutionError("unable to identify controlled Git metadata")
        self._common_git_dir = Path(common.stdout.strip()).resolve(strict=True)

    @property
    def branch_prefix(self) -> str:
        return self._branch_prefix

    @property
    def cleanup_events(self) -> tuple[dict[str, object], ...]:
        """Return bounded diagnostic snapshots; never infer acceptance from them."""
        return tuple(deepcopy(event) for event in self._cleanup_events)

    def _record_cleanup_event(self, **fields: object) -> None:
        fields.setdefault("utc", datetime.now(timezone.utc).isoformat())
        if len(self._cleanup_events) < 32:
            self._cleanup_events.append(deepcopy(fields))
        elif fields.get("stage") in {"cleanup_stopped", "create_stopped"}:
            self._cleanup_events[-1] = deepcopy(fields)

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

        started = time.monotonic()
        metadata = None
        try:
            resolved = destination.resolve(strict=True)
            self._assert_under_parent(resolved)
            session = WorktreeSession(
                repository_root=str(self._repo),
                worktree_root=str(resolved),
                branch=branch,
                base_sha=base_sha,
            )
            metadata = self._run_git(
                ["-C", str(resolved), "rev-parse", "--absolute-git-dir"],
                operation="git.worktree_metadata",
            )
            if metadata.returncode:
                raise ToolExecutionError("unable to identify created worktree metadata")
            git_dir = Path(metadata.stdout.strip()).resolve(strict=True)
            if git_dir.parent != self._common_git_dir / "worktrees":
                raise ToolAccessError("created worktree has unexpected metadata ownership")
        except Exception as exc:
            # Add succeeded, but metadata ownership is not established. Preserve
            # every object; this diagnostic record grants no cleanup authority.
            recovery = dict(
                stage="create_stopped", outcome="FAIL_PRESERVED",
                repository_root=str(self._repo), worktree_path=str(destination),
                branch_ref="refs/heads/" + branch, base_sha=base_sha,
                git_add=dict(argv=result.args, exit_code=result.returncode, stdout=result.stdout,
                             stderr=result.stderr),
                metadata_command=(dict(argv=metadata.args, exit_code=metadata.returncode,
                                       stdout=metadata.stdout, stderr=metadata.stderr)
                                  if metadata is not None else None),
                session_registered=False, automatic_cleanup=False,
                stop_reason=f"{type(exc).__name__}: {exc}",
                winerror=getattr(exc, "winerror", None), errno=getattr(exc, "errno", None),
                elapsed_ms=round((time.monotonic() - started) * 1000),
                recovery_required="Verify ownership, metadata, SHA and tracked state before removal",
                observations=self._created_worktree_observations(destination, branch),
                utc=datetime.now(timezone.utc).isoformat(),
            )
            self._record_cleanup_event(**recovery)
            exc.recovery_evidence = deepcopy(recovery)
            raise
        self._sessions[str(resolved)] = session
        self._session_metadata[str(resolved)] = git_dir
        return session

    def _created_worktree_observations(self, destination: Path, branch: str) -> dict[str, object]:
        """Best-effort read-only recovery evidence; errors remain explicit unknowns."""
        observations: dict[str, object] = {}
        def probe(name, action):
            try:
                observations[name] = dict(state="MEASURED", value=action())
            except Exception as error:
                observations[name] = dict(
                    state="ERROR", error_type=type(error).__name__, error=str(error),
                    winerror=getattr(error, "winerror", None),
                )
        def git_probe(args):
            result = self._run_git(args, operation="git.create_recovery_probe")
            return dict(argv=args, exit_code=result.returncode,
                        stdout=result.stdout, stderr=result.stderr)
        def pointer_probe():
            self._reject_reparse_points(destination / ".git")
            pointer = (destination / ".git").read_bytes()
            value = pointer.decode("utf-8").strip()
            metadata_path = None
            metadata_exists = None
            if value.startswith("gitdir: "):
                path = Path(value[8:])
                if not path.is_absolute():
                    path = destination / path
                path = path.resolve(strict=True)
                metadata_path = str(path)
                if path.parent == self._common_git_dir / "worktrees":
                    self._reject_reparse_points(path)
                    metadata_exists = path.is_dir()
            return dict(pointer_path=str(destination / ".git"), pointer_hex=pointer.hex(),
                        metadata_path=metadata_path, metadata_exists=metadata_exists)
        probe("physical_directory", destination.is_dir)
        probe("registration", lambda: git_probe(["worktree", "list", "--porcelain", "-z"]))
        # Keep both exit codes: an execution error must never become ref absence.
        probe("branch", lambda: git_probe(["show-ref", "--verify", "--quiet", "refs/heads/" + branch]))
        probe("branch_sha", lambda: git_probe(["rev-parse", "--verify", "refs/heads/" + branch]))
        probe("metadata_pointer", pointer_probe)
        return observations

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
        """Discard generated files only in a verified adapter-owned worktree.

        A saved clean/base proof permits resuming an empty deregistered residue.
        Unknown metadata or nonempty deregistered residues fail closed.
        """
        self._cleanup_events.clear()
        started = time.monotonic()
        worktree = Path(session.worktree_root)
        try:
            self._verify_disposable_path(worktree, session)
            initial = self._cleanup_state(worktree, session)
            self._record_cleanup_event(stage="cleanup_preflight", state=initial)
            self._verify_disposable_state(worktree, session, initial)
            remove_error = self._remove_disposable_worktree_with_retry(worktree)
            if remove_error is not None:
                self._remove_disposable_worktree_fallback(worktree, remove_error)

            final = self._cleanup_state(worktree, session)
            if final["worktree_exists"] or final["registered"] or final["metadata_exists"]:
                raise ToolExecutionError("disposable cleanup did not remove all owned objects")
            self._require_disposable_branch(session, final)
            delete = self._run_git(
                ["update-ref", "-d", "refs/heads/" + session.branch, session.base_sha],
                operation="git.branch_delete_disposable_controlled",
            )
            self._record_cleanup_event(
                stage="branch_delete", exit_code=delete.returncode,
                git_stderr=delete.stderr, branch=session.branch,
            )
            if delete.returncode:
                raise ToolExecutionError("disposable branch compare-and-delete failed")
            final = self._cleanup_state(worktree, session)
            if final["branch_exists"]:
                raise ToolExecutionError("disposable branch still exists after cleanup")
            self._sessions.pop(str(worktree), None)
            self._session_metadata.pop(str(worktree), None)
            self._disposable_proofs.pop(str(worktree), None)
            self._record_cleanup_event(
                stage="cleanup_complete", worktree_exists=False, state=final,
                elapsed_ms=round((time.monotonic() - started) * 1000),
            )
        except (ToolAccessError, ToolExecutionError, OSError, subprocess.SubprocessError) as exc:
            self._record_cleanup_event(
                stage="cleanup_stopped", stop_reason=f"{type(exc).__name__}: {exc}",
                worktree_exists=worktree.exists(),
                winerror=getattr(exc, "winerror", None),
                elapsed_ms=round((time.monotonic() - started) * 1000),
            )
            raise

    @staticmethod
    def _reject_reparse_points(path: Path, *, subtree: bool = False) -> None:
        paths = [path, *path.parents]
        if subtree and path.exists():
            paths.extend(path.rglob("*"))
        for item in paths:
            try:
                info = item.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ToolAccessError(f"reparse/symlink cleanup path is prohibited: {item}")

    def _verify_disposable_path(self, worktree: Path, session: WorktreeSession) -> None:
        self._reject_reparse_points(worktree, subtree=True)
        if (
            not worktree.is_absolute()
            or worktree.resolve() != worktree
            or worktree.parent != self._parent
            or worktree == self._repo
            or session.repository_root != str(self._repo)
            or self._sessions.get(str(worktree)) != session
            or str(worktree) not in self._session_metadata
        ):
            raise ToolAccessError("unknown or non-adapter-owned disposable path")
        self._assert_under_parent(worktree)

    def _cleanup_state(self, worktree: Path, session: WorktreeSession) -> dict[str, object]:
        """Read independent states; an absent ref is not a Git execution error."""
        started = time.monotonic()
        ref = "refs/heads/" + session.branch
        probe = self._run_git(["show-ref", "--verify", "--quiet", ref], operation="git.cleanup_ref")
        if probe.returncode not in (0, 1):
            self._record_cleanup_event(stage="ref_probe_error", branch_ref=ref,
                                       exit_code=probe.returncode, git_stderr=probe.stderr)
            raise ToolExecutionError(f"unable to inspect disposable ref: {probe.stderr}")
        branch_sha = None
        if probe.returncode == 0:
            sha = self._run_git(["rev-parse", "--verify", ref], operation="git.cleanup_ref_sha")
            if sha.returncode or not re.fullmatch(r"[0-9a-f]{40}", sha.stdout.strip()):
                raise ToolExecutionError("unable to resolve exact disposable branch SHA")
            branch_sha = sha.stdout.strip()
        listing = self._run_git(["worktree", "list", "--porcelain", "-z"], operation="git.cleanup_registration")
        if listing.returncode:
            self._record_cleanup_event(stage="registration_probe_error",
                                       exit_code=listing.returncode, git_stderr=listing.stderr)
            raise ToolExecutionError(f"unable to inspect Git registration: {listing.stderr}")
        registration: dict[str, str] | None = None
        active: dict[str, str] | None = None
        for field in listing.stdout.split("\0"):
            if field.startswith("worktree "):
                active = {}
                if Path(field[9:]).resolve() == worktree:
                    registration = active
            elif field and active is not None:
                key, _, value = field.partition(" ")
                active[key] = value
            elif not field:
                active = None
        metadata = self._session_metadata[str(worktree)]
        self._reject_reparse_points(metadata, subtree=True)
        metadata_exists = metadata.exists()
        known = False
        if registration is not None and metadata_exists and worktree.exists():
            try:
                pointer = (worktree / ".git").read_text(encoding="utf-8").strip()
                pointer_path = Path(pointer[8:]) if pointer.startswith("gitdir: ") else Path()
                if not pointer_path.is_absolute():
                    pointer_path = worktree / pointer_path
                known = (
                    pointer.startswith("gitdir: ")
                    and pointer_path.resolve() == metadata
                    and Path((metadata / "gitdir").read_text(encoding="utf-8").strip()).resolve() == worktree / ".git"
                    and (metadata / (metadata / "commondir").read_text(encoding="utf-8").strip()).resolve() == self._common_git_dir
                    and registration.get("branch") == ref
                    and (metadata / "HEAD").read_text(encoding="utf-8").strip() == "ref: " + ref
                )
            except (OSError, ValueError):
                known = False
        elif registration is None and not metadata_exists:
            known = True
        elif registration is not None and metadata_exists and not worktree.exists():
            # Only the previously verified missing path can reach targeted removal.
            try:
                known = (
                    self._disposable_proofs.get(str(worktree)) == session.base_sha
                    and registration.get("branch") == ref
                    and Path((metadata / "gitdir").read_text(encoding="utf-8").strip()).resolve() == worktree / ".git"
                    and (metadata / (metadata / "commondir").read_text(encoding="utf-8").strip()).resolve() == self._common_git_dir
                    and (metadata / "HEAD").read_text(encoding="utf-8").strip() == "ref: " + ref
                )
            except (OSError, ValueError):
                known = False
        return dict(
            utc=datetime.now(timezone.utc).isoformat(), worktree_path=str(worktree),
            worktree_exists=worktree.exists(), registered=registration is not None,
            metadata_path=str(metadata), metadata_exists=metadata_exists,
            metadata_known=known, branch=session.branch, branch_ref=ref,
            branch_exists=probe.returncode == 0, branch_sha=branch_sha,
            ref_exit_code=probe.returncode,
            elapsed_ms=round((time.monotonic() - started) * 1000),
        )

    @staticmethod
    def _require_disposable_branch(session: WorktreeSession, state: dict[str, object]) -> None:
        if not state["branch_exists"] or state["branch_sha"] != session.base_sha:
            raise ToolAccessError("refusing disposable branch cleanup: branch moved or absent")
        if not state["metadata_known"]:
            raise ToolAccessError("unknown disposable Git metadata state")

    def _verify_disposable_state(
        self, worktree: Path, session: WorktreeSession, state: dict[str, object],
    ) -> None:
        self._verify_disposable_path(worktree, session)
        self._require_disposable_branch(session, state)
        if state["registered"]:
            git = GitReadOnlyAdapter(worktree, git_executable=str(self._git))
            head, diff, cached = git.head_sha(), git.diff_worktree(), git.diff_cached()
            if not head.ok or head.stdout.strip() != session.base_sha:
                raise ToolAccessError("refusing disposable cleanup: worktree HEAD differs from base SHA")
            if not diff.ok or not cached.ok:
                raise ToolExecutionError("unable to verify tracked state before disposable cleanup")
            if diff.stdout or cached.stdout:
                raise ToolAccessError("refusing disposable cleanup: tracked worktree state is not clean")
            self._disposable_proofs[str(worktree)] = session.base_sha
        elif (
            self._disposable_proofs.get(str(worktree)) != session.base_sha
            or (worktree.exists() and any(worktree.iterdir()))
        ):
            raise ToolAccessError("unverified or nonempty deregistered disposable residue")

    def _remove_disposable_worktree_with_retry(
        self, worktree: Path, *, attempts: int = 3,
    ) -> str | None:
        session = self._sessions[str(worktree)]
        last_error = ""
        for index in range(attempts):
            before = self._cleanup_state(worktree, session)
            self._verify_disposable_state(worktree, session, before)
            if not before["registered"]:
                return "Git worktree already deregistered; physical cleanup required" if worktree.exists() else None
            self._record_cleanup_event(stage="git_worktree_remove_pending", before=before,
                                       attempt=index + 1)
            started = time.monotonic()
            result = self._run_git(
                ["worktree", "remove", "--force", str(worktree)],
                operation="git.worktree_remove_disposable",
            )
            self._record_cleanup_event(
                stage="git_worktree_remove_result", before=before,
                attempt=index + 1, exit_code=result.returncode,
                git_stderr=result.stderr,
                elapsed_ms=round((time.monotonic() - started) * 1000),
            )
            after = self._cleanup_state(worktree, session)
            self._record_cleanup_event(
                stage="git_worktree_remove", attempt=index + 1, before=before, after=after,
                elapsed_ms=round((time.monotonic() - started) * 1000),
                exit_code=result.returncode, git_stderr=result.stderr,
                worktree_exists=after["worktree_exists"],
                git_error=(result.stderr.strip() or result.stdout.strip()) if result.returncode else None,
                winerror=None,
            )
            self._require_disposable_branch(session, after)
            if not after["registered"]:
                return (result.stderr.strip() or "partial removal") if after["worktree_exists"] else None
            if result.returncode == 0:
                raise ToolExecutionError("Git reported success but worktree remains registered")
            last_error = result.stderr.strip() or result.stdout.strip()
            if index + 1 < attempts:
                time.sleep(0.25 * (index + 1))
        return last_error or "git worktree remove failed"

    def _remove_disposable_worktree_fallback(self, worktree: Path, remove_error: str) -> None:
        """Use the existing bounded filesystem fallback; never prune other entries."""
        session = self._sessions[str(worktree)]
        state = self._cleanup_state(worktree, session)
        self._verify_disposable_state(worktree, session, state)
        self._record_cleanup_event(stage="fallback_verified", state=state, base_sha=session.base_sha, tracked_clean=True)
        if worktree.exists():
            try:
                self._remove_disposable_filesystem_with_retry(worktree)
            except OSError as exc:
                raise ToolExecutionError(
                    f"disposable worktree cleanup failed after git remove error {remove_error!r}: {exc}"
                ) from exc
        after = self._cleanup_state(worktree, session)
        self._require_disposable_branch(session, after)
        if after["registered"]:
            # A Git remove failure may leave this registration. Remove only it.
            started = time.monotonic()
            result = self._run_git(
                ["worktree", "remove", "--force", str(worktree)],
                operation="git.worktree_remove_missing_disposable",
            )
            self._record_cleanup_event(
                stage="git_metadata_remove_result", before=after,
                exit_code=result.returncode, git_stderr=result.stderr,
                elapsed_ms=round((time.monotonic() - started) * 1000),
            )
            final = self._cleanup_state(worktree, session)
            self._record_cleanup_event(
                stage="git_metadata_remove", before=after, after=final,
                elapsed_ms=round((time.monotonic() - started) * 1000),
                exit_code=result.returncode, git_stderr=result.stderr,
                worktree_exists=final["worktree_exists"],
            )
            if result.returncode or final["registered"] or final["metadata_exists"]:
                raise ToolExecutionError("targeted disposable metadata cleanup failed")
        elif after["metadata_exists"]:
            raise ToolAccessError("unknown residual disposable metadata")

    def _remove_disposable_filesystem_with_retry(
        self,
        worktree: Path,
        *,
        attempts: int = 10,
    ) -> None:
        """Boundedly retry filesystem cleanup after Git worktree deregistration.

        Windows may release the directory handle slightly after Git has already
        removed the worktree registration. Retry only the already-verified
        adapter-owned disposable path; persistent locks still fail closed.
        """

        if attempts <= 0:
            raise ValueError("attempts must be positive")

        def _clear_readonly_and_retry(function, path, exc_info):
            try:
                os.chmod(path, stat.S_IWRITE)
                function(path)
            except OSError:
                raise exc_info[1]

        last_error: OSError | None = None
        for index in range(attempts):
            if not worktree.exists():
                return
            session = self._sessions.get(str(worktree))
            if session is None:
                raise ToolAccessError("filesystem fallback requires an adapter-owned session")
            state = self._cleanup_state(worktree, session)
            self._verify_disposable_state(worktree, session, state)
            started = time.monotonic()
            error: OSError | None = None
            try:
                shutil.rmtree(
                    worktree,
                    onerror=_clear_readonly_and_retry,
                )
            except OSError as exc:
                last_error = exc
                error = exc

            self._record_cleanup_event(
                stage="filesystem_remove",
                attempt=index + 1,
                elapsed_ms=round((time.monotonic() - started) * 1000),
                worktree_exists=worktree.exists(),
                error_type=type(error).__name__ if error is not None else None,
                winerror=getattr(error, "winerror", None),
                errno=getattr(error, "errno", None),
            )
            if not worktree.exists():
                return

            if index + 1 < attempts:
                time.sleep(min(0.25 * (index + 1), 1.0))

        if last_error is not None:
            raise last_error
        raise OSError(f"disposable worktree path still exists: {worktree}")

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
