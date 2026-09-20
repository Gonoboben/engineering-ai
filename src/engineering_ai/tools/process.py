"""Allow-listed local process execution without a shell."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping

from engineering_ai.tools.common import ToolAccessError, ToolExecutionError, ToolResult


class NetworkRequirement(str, Enum):
    LOCAL_ONLY = "LOCAL_ONLY"
    NETWORK_CAPABLE = "NETWORK_CAPABLE"


@dataclass(frozen=True)
class CommandSpec:
    command_id: str
    executable: str
    fixed_args: tuple[str, ...] = ()
    timeout_seconds: float = 10.0
    max_output_bytes: int = 65_536
    network_requirement: NetworkRequirement = NetworkRequirement.LOCAL_ONLY

    def __post_init__(self) -> None:
        if not self.command_id:
            raise ValueError("command_id is required")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_output_bytes <= 0:
            raise ValueError("max_output_bytes must be positive")


class AllowListedProcessRunner:
    """Execute only predeclared fixed command profiles with shell disabled."""

    def __init__(
        self,
        specs: Mapping[str, CommandSpec],
        *,
        root: str | Path,
        offline: bool = False,
    ) -> None:
        self._root = Path(root).resolve(strict=True)
        if not self._root.is_dir():
            raise ValueError("process root must be a directory")
        self._specs = dict(specs)
        self._offline = offline
        if set(self._specs) != {spec.command_id for spec in self._specs.values()}:
            raise ValueError("spec mapping keys must match command_id")

    def run(self, command_id: str, *, cwd: str | Path = ".") -> ToolResult:
        spec = self._specs.get(command_id)
        if spec is None:
            raise ToolAccessError(f"command is not allow-listed: {command_id}")
        if self._offline and spec.network_requirement is NetworkRequirement.NETWORK_CAPABLE:
            raise ToolAccessError(
                f"offline mode blocks network-capable command: {command_id}"
            )
        executable = self._resolve_executable(spec.executable)
        workdir = self._resolve_cwd(cwd)
        argv = [str(executable), *spec.fixed_args]

        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            timed_out = False
            exit_code: int | None = None
            try:
                completed = subprocess.run(
                    argv,
                    cwd=workdir,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    shell=False,
                    timeout=spec.timeout_seconds,
                    check=False,
                )
                exit_code = completed.returncode
            except subprocess.TimeoutExpired:
                # subprocess.run owns the Popen lifecycle and, on timeout,
                # kills and fully reaps the child before returning control.
                # This matters on Windows where an incompletely reaped child
                # can retain its current-directory handle and block cleanup.
                timed_out = True

            stdout, stdout_truncated = self._read_bounded(stdout_file, spec.max_output_bytes)
            stderr, stderr_truncated = self._read_bounded(stderr_file, spec.max_output_bytes)
            truncated = stdout_truncated or stderr_truncated
            ok = (exit_code == 0) and not timed_out
            summary = (
                "process timed out"
                if timed_out
                else ("process completed" if ok else f"process exited with code {exit_code}")
            )
            return ToolResult(
                ok=ok,
                operation=command_id,
                summary=summary,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                timed_out=timed_out,
                truncated=truncated,
            )

    def _resolve_executable(self, executable: str) -> Path:
        candidate = Path(executable)
        if candidate.is_absolute():
            resolved = candidate.resolve(strict=True)
        else:
            found = shutil.which(executable)
            if found is None:
                raise ToolExecutionError(f"allow-listed executable not found: {executable}")
            resolved = Path(found).resolve(strict=True)
        if not resolved.is_file():
            raise ToolExecutionError(f"executable is not a file: {resolved}")
        return resolved

    def _resolve_cwd(self, cwd: str | Path) -> Path:
        relative = Path(cwd)
        if relative.is_absolute():
            raise ToolAccessError("absolute cwd is not allowed")
        resolved = (self._root / relative).resolve(strict=True)
        try:
            resolved.relative_to(self._root)
        except ValueError as exc:
            raise ToolAccessError(f"cwd escapes configured root: {resolved}") from exc
        if not resolved.is_dir():
            raise ToolExecutionError(f"cwd is not a directory: {resolved}")
        return resolved

    @staticmethod
    def _read_bounded(file_obj, max_bytes: int) -> tuple[str, bool]:
        file_obj.seek(0)
        data = file_obj.read(max_bytes + 1)
        truncated = len(data) > max_bytes
        if truncated:
            data = data[:max_bytes]
        return data.decode("utf-8", errors="replace"), truncated
