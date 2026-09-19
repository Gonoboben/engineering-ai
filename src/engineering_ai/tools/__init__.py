"""Typed deterministic tool adapters."""

from engineering_ai.tools.common import ToolAccessError, ToolExecutionError, ToolResult
from engineering_ai.tools.filesystem import FileEntry, ReadOnlyFilesystemAdapter
from engineering_ai.tools.git import GitReadOnlyAdapter
from engineering_ai.tools.process import AllowListedProcessRunner, CommandSpec
from engineering_ai.tools.worktree import (
    ControlledWorktreeAdapter,
    PatchApplication,
    PatchProposal,
    WorktreeSession,
)

__all__ = [
    "AllowListedProcessRunner",
    "CommandSpec",
    "ControlledWorktreeAdapter",
    "FileEntry",
    "GitReadOnlyAdapter",
    "PatchApplication",
    "PatchProposal",
    "ReadOnlyFilesystemAdapter",
    "ToolAccessError",
    "ToolExecutionError",
    "ToolResult",
    "WorktreeSession",
]
