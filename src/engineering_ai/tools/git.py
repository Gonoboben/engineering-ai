"""Narrow read-only Git inspection adapter."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from engineering_ai.tools.common import ToolExecutionError, ToolResult


_SAFE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")


class GitReadOnlyAdapter:
    """Expose a fixed read-only Git command set; no generic command execution."""

    def __init__(
        self,
        repository_root: str | Path,
        *,
        git_executable: str = "git",
        timeout_seconds: float = 10.0,
        max_output_bytes: int = 262_144,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_output_bytes <= 0:
            raise ValueError("max_output_bytes must be positive")
        found = shutil.which(git_executable)
        if found is None:
            raise ToolExecutionError(f"git executable not found: {git_executable}")
        self._git = Path(found).resolve(strict=True)
        self._root = Path(repository_root).resolve(strict=True)
        self._timeout = timeout_seconds
        self._max_output = max_output_bytes
        top = self._run_raw(["rev-parse", "--show-toplevel"], operation="git.repo_root")
        if not top.ok:
            raise ToolExecutionError(f"not a Git repository: {top.stderr or top.stdout}")
        actual = Path(top.stdout.strip()).resolve(strict=True)
        if actual != self._root:
            raise ToolExecutionError(
                f"configured root is not repository top-level: configured={self._root}, actual={actual}"
            )

    @property
    def root(self) -> Path:
        return self._root

    def status(self) -> ToolResult:
        return self._run_raw(
            ["status", "--porcelain=v1", "--branch", "--untracked-files=normal"],
            operation="git.status",
        )

    def current_branch(self) -> ToolResult:
        return self._run_raw(["branch", "--show-current"], operation="git.current_branch")

    def head_sha(self) -> ToolResult:
        return self._run_raw(["rev-parse", "--verify", "HEAD"], operation="git.head_sha")

    def ref_sha(self, ref: str) -> ToolResult:
        safe_ref = self._validate_ref(ref)
        return self._run_raw(
            ["rev-parse", "--verify", safe_ref],
            operation="git.ref_sha",
        )

    def log(self, *, max_count: int = 20) -> ToolResult:
        if not 1 <= max_count <= 100:
            raise ValueError("max_count must be between 1 and 100")
        return self._run_raw(
            ["log", f"--max-count={max_count}", "--no-decorate", "--format=%H%x09%s"],
            operation="git.log",
        )

    def diff_worktree(self) -> ToolResult:
        return self._run_raw(
            ["diff", "--no-ext-diff", "--no-textconv"], operation="git.diff_worktree"
        )

    def diff_cached(self) -> ToolResult:
        return self._run_raw(
            ["diff", "--cached", "--no-ext-diff", "--no-textconv"],
            operation="git.diff_cached",
        )

    def diff_between(self, base_ref: str, head_ref: str) -> ToolResult:
        base = self._validate_ref(base_ref)
        head = self._validate_ref(head_ref)
        return self._run_raw(
            ["diff", "--no-ext-diff", "--no-textconv", f"{base}...{head}"],
            operation="git.diff_between",
        )

    @staticmethod
    def _validate_ref(value: str) -> str:
        if value.startswith("-") or ".." in value or not _SAFE_REF.fullmatch(value):
            raise ValueError(f"unsafe Git ref: {value!r}")
        return value

    def _run_raw(self, args: list[str], *, operation: str) -> ToolResult:
        argv = [str(self._git), "--no-pager", *args]
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            process = subprocess.Popen(
                argv,
                cwd=self._root,
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                shell=False,
            )
            timed_out = False
            try:
                exit_code = process.wait(timeout=self._timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                exit_code = process.wait()
            stdout, stdout_truncated = self._read_bounded(stdout_file)
            stderr, stderr_truncated = self._read_bounded(stderr_file)
            ok = (exit_code == 0) and not timed_out
            return ToolResult(
                ok=ok,
                operation=operation,
                summary=(
                    "git command timed out"
                    if timed_out
                    else ("git command completed" if ok else f"git exited with code {exit_code}")
                ),
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                timed_out=timed_out,
                truncated=stdout_truncated or stderr_truncated,
            )

    def _read_bounded(self, file_obj) -> tuple[str, bool]:
        file_obj.seek(0)
        data = file_obj.read(self._max_output + 1)
        truncated = len(data) > self._max_output
        if truncated:
            data = data[: self._max_output]
        return data.decode("utf-8", errors="replace"), truncated
