"""Typed deterministic tool adapters."""

from engineering_ai.tools.cad import (
    CadAabb,
    CadArtifactResult,
    CadBackendError,
    CadBox,
    CadCylinder,
    CadDesignSpec,
    CadEntityGeometry,
    CadGeometryReport,
    CadPlacement,
    CadPrimitiveKind,
    CadRuntimeReport,
    CadSpecError,
    FreeCadRuntime,
    ParametricCadAdapter,
    geometry_report_for_design,
)
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
    "CadAabb",
    "CadArtifactResult",
    "CadBackendError",
    "CadBox",
    "CadCylinder",
    "CadDesignSpec",
    "CadEntityGeometry",
    "CadGeometryReport",
    "CadPlacement",
    "CadPrimitiveKind",
    "CadRuntimeReport",
    "CadSpecError",
    "CommandSpec",
    "ControlledWorktreeAdapter",
    "FileEntry",
    "FreeCadRuntime",
    "GitReadOnlyAdapter",
    "PatchApplication",
    "ParametricCadAdapter",
    "PatchProposal",
    "ReadOnlyFilesystemAdapter",
    "ToolAccessError",
    "ToolExecutionError",
    "ToolResult",
    "WorktreeSession",
    "geometry_report_for_design",
]
