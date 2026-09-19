"""External engineering-project adapters and profiles."""

from engineering_ai.projects.platavm import (
    CIState,
    GovernanceDocument,
    PlataVMReadOnlyAdapter,
    PlataVMReadOnlySnapshot,
    PlataVMValidatorResult,
    ValidatorState,
    classify_ci_conclusion,
)
from engineering_ai.projects.platavm_controlled import (
    ControlledLoopState,
    ControlledPatchResult,
    ControlledValidationResult,
    PlataVMControlledEngineeringLoop,
    WorktreePreparation,
)

__all__ = [
    "CIState",
    "ControlledLoopState",
    "ControlledPatchResult",
    "ControlledValidationResult",
    "GovernanceDocument",
    "PlataVMControlledEngineeringLoop",
    "PlataVMReadOnlyAdapter",
    "PlataVMReadOnlySnapshot",
    "PlataVMValidatorResult",
    "ValidatorState",
    "WorktreePreparation",
    "classify_ci_conclusion",
]
