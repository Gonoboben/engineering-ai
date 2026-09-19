"""External engineering-project adapters and profiles."""

from engineering_ai.projects.buoycalc import (
    BuoyCalcCIState,
    BuoyCalcReadOnlyAdapter,
    BuoyCalcReadOnlySnapshot,
    SourceBoundaryClass,
    classify_ci_state as classify_buoycalc_ci_state,
)
from engineering_ai.projects.buoycalc_controlled import (
    BuoyCalcControlledEngineeringLoop,
    BuoyCalcControlledState,
    BuoyCalcPatchResult,
    BuoyCalcValidationResult,
    BuoyCalcWorktreePreparation,
    ValidationProfileEvidence,
    ValidationStepEvidence,
)
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
    "BuoyCalcControlledEngineeringLoop",
    "BuoyCalcControlledState",
    "BuoyCalcPatchResult",
    "BuoyCalcValidationResult",
    "BuoyCalcWorktreePreparation",
    "BuoyCalcCIState",
    "BuoyCalcReadOnlyAdapter",
    "BuoyCalcReadOnlySnapshot",
    "CIState",
    "ControlledLoopState",
    "ControlledPatchResult",
    "ControlledValidationResult",
    "GovernanceDocument",
    "PlataVMControlledEngineeringLoop",
    "PlataVMReadOnlyAdapter",
    "PlataVMReadOnlySnapshot",
    "PlataVMValidatorResult",
    "ValidationProfileEvidence",
    "ValidationStepEvidence",
    "ValidatorState",
    "SourceBoundaryClass",
    "WorktreePreparation",
    "classify_buoycalc_ci_state",
    "classify_ci_conclusion",
]
