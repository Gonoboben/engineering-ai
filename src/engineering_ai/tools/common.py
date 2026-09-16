"""Common typed results and errors for bounded local tool adapters."""

from __future__ import annotations

from dataclasses import dataclass


class ToolAccessError(PermissionError):
    """Raised when an adapter request crosses an explicit access boundary."""


class ToolExecutionError(RuntimeError):
    """Raised when an adapter cannot safely execute its configured operation."""


@dataclass(frozen=True)
class ToolResult:
    """Bounded, serializable-style result returned by local process-like tools."""

    ok: bool
    operation: str
    summary: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    timed_out: bool = False
    truncated: bool = False
