"""Supervisor-controlled proposal-only CAD worker for Gate 024."""

from __future__ import annotations

from dataclasses import dataclass

from engineering_ai.supervisor.core import ProposalExecutionResult, Supervisor, ToolOutcome
from engineering_ai.supervisor.policy import PolicyDecision
from engineering_ai.tools.cad import (
    CadArtifactResult,
    CadBackendError,
    CadDesignSpec,
    CadGeometryReport,
    ParametricCadAdapter,
    geometry_report_for_design,
)
from engineering_ai.tools.common import ToolAccessError


@dataclass(frozen=True)
class CadWorkerRequest:
    project_id: str
    task_id: str
    design: CadDesignSpec
    output_relative_path: str
    timeout_seconds: float = 120.0

    def __post_init__(self) -> None:
        project_id = self.project_id.strip()
        task_id = self.task_id.strip()
        output = self.output_relative_path.strip()
        if not project_id or len(project_id) > 128:
            raise ValueError("project_id must contain 1..128 characters")
        if not task_id or len(task_id) > 128:
            raise ValueError("task_id must contain 1..128 characters")
        if not output or len(output) > 512:
            raise ValueError("output_relative_path must contain 1..512 characters")
        if self.design.project_id != project_id:
            raise ValueError("CAD design project_id must match request project_id")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 300:
            raise ValueError("CAD worker timeout must be in (0, 300]")
        object.__setattr__(self, "project_id", project_id)
        object.__setattr__(self, "task_id", task_id)
        object.__setattr__(self, "output_relative_path", output)


@dataclass(frozen=True)
class CadWorkerResult:
    project_id: str
    task_id: str
    decision: PolicyDecision
    tool_called: bool
    outcome_ok: bool
    geometry: CadGeometryReport
    artifact: CadArtifactResult | None
    failure_class: str | None
    authority: str = "PROPOSED_PATCH_ONLY"
    evidence_eligible_geometry: bool = True
    evidence_eligible_design_correctness: bool = False
    physical_validation: str = "PHYSICAL_NOT_EXECUTED"


class CadWorker:
    """Validate a typed CAD design and publish only a Supervisor-approved proposal.

    Gate 024 maps CAD artifact generation to the already accepted
    propose_patch action. The worker does not add a new permission and does not
    call the CAD backend unless the current Supervisor policy allows that exact
    action.
    """

    ACTION = "propose_patch"

    def __init__(self, *, adapter: ParametricCadAdapter) -> None:
        self._adapter = adapter

    def generate_proposal(
        self,
        request: CadWorkerRequest,
        *,
        supervisor: Supervisor,
        job: dict,
    ) -> CadWorkerResult:
        if job.get("project_id") != request.project_id:
            raise ValueError("CAD request project_id must match job project_id")

        geometry = geometry_report_for_design(request.design)
        holder: dict[str, object] = {}

        def tool(action: str) -> ToolOutcome:
            if action != self.ACTION:
                return ToolOutcome(False, "unexpected CAD action")
            try:
                artifact = self._adapter.generate(
                    design=request.design,
                    relative_path=request.output_relative_path,
                    timeout_seconds=request.timeout_seconds,
                )
            except ToolAccessError:
                holder["failure_class"] = "CAD_ACCESS_REJECTED"
                return ToolOutcome(
                    False,
                    "CAD artifact access boundary rejected the proposal",
                    (
                        f"cad-design-sha256:{request.design.design_sha256}",
                        f"cad-geometry-sha256:{geometry.report_sha256}",
                    ),
                )
            except CadBackendError:
                holder["failure_class"] = "CAD_BACKEND_REJECTED"
                return ToolOutcome(
                    False,
                    "CAD backend failed closed",
                    (
                        f"cad-design-sha256:{request.design.design_sha256}",
                        f"cad-geometry-sha256:{geometry.report_sha256}",
                    ),
                )

            holder["artifact"] = artifact
            return ToolOutcome(
                True,
                "CAD proposed artifact generated and deterministic geometry matched",
                (
                    f"cad-design-sha256:{artifact.design_sha256}",
                    f"cad-geometry-sha256:{artifact.geometry_report_sha256}",
                    f"cad-artifact-sha256:{artifact.artifact_sha256}",
                ),
            )

        proposal: ProposalExecutionResult = supervisor.evaluate_tool_proposal(
            job=job,
            action=self.ACTION,
            tool=tool,
        )
        artifact = holder.get("artifact")
        if artifact is not None and not isinstance(artifact, CadArtifactResult):
            raise TypeError("internal CAD artifact capture is invalid")
        failure_class = holder.get("failure_class")
        if failure_class is not None and not isinstance(failure_class, str):
            raise TypeError("internal CAD failure classification is invalid")
        outcome_ok = bool(proposal.outcome is not None and proposal.outcome.ok)

        return CadWorkerResult(
            project_id=request.project_id,
            task_id=request.task_id,
            decision=proposal.decision,
            tool_called=proposal.tool_called,
            outcome_ok=outcome_ok,
            geometry=geometry,
            artifact=artifact,
            failure_class=failure_class,
        )
