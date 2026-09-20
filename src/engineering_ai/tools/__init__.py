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
from engineering_ai.tools.image_artifact import (
    PngArtifactPublisher,
    PngInfo,
    PngValidationError,
    PublishedImageArtifact,
    validate_png,
)
from engineering_ai.tools.filesystem import FileEntry, ReadOnlyFilesystemAdapter
from engineering_ai.tools.git import GitReadOnlyAdapter
from engineering_ai.tools.process import AllowListedProcessRunner, CommandSpec, NetworkRequirement
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
    "NetworkRequirement",
    "ControlledWorktreeAdapter",
    "FileEntry",
    "FreeCadRuntime",
    "GitReadOnlyAdapter",
    "PatchApplication",
    "PngArtifactPublisher",
    "PngInfo",
    "PngValidationError",
    "PublishedImageArtifact",
    "ParametricCadAdapter",
    "PatchProposal",
    "ReadOnlyFilesystemAdapter",
    "ToolAccessError",
    "ToolExecutionError",
    "ToolResult",
    "WorktreeSession",
    "geometry_report_for_design",
    "validate_png",
]
