from __future__ import annotations

import json
import tempfile
from pathlib import Path

from engineering_ai.supervisor import CadWorker, CadWorkerRequest, Decision, Supervisor
from engineering_ai.tools import (
    CadBackendError,
    CadBox,
    CadCylinder,
    CadDesignSpec,
    CadPlacement,
    ParametricCadAdapter,
    geometry_report_for_design,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def load_fixture(name: str) -> dict:
    with (FIXTURES / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def make_design() -> CadDesignSpec:
    return CadDesignSpec(
        project_id="engineering-ai",
        design_id="gate024-smoke",
        entities=(
            CadBox("Base", 30.0, 20.0, 4.0, CadPlacement(0.0, 0.0, 0.0)),
            CadCylinder("Post", 3.0, 10.0, CadPlacement(12.0, 10.0, 4.0)),
        ),
    )


def report_payload(design: CadDesignSpec, *, mismatch: bool = False) -> dict:
    report = geometry_report_for_design(design)
    entities = [item.as_dict() for item in report.entities]
    if mismatch:
        entities[0]["aabb"]["max_x_mm"] = float(entities[0]["aabb"]["max_x_mm"]) + 1.0
    return {
        "backend": "synthetic-freecad",
        "backend_version": "gate024-smoke",
        "design_sha256": design.design_sha256,
        "entities": entities,
        "assembly_aabb": report.assembly_aabb.as_dict(),
        "total_primitive_volume_mm3": report.total_primitive_volume_mm3,
    }


class SyntheticCadRuntime:
    def __init__(self, design: CadDesignSpec, *, mismatch: bool = False) -> None:
        self.design = design
        self.mismatch = mismatch
        self.calls = 0

    def generate(
        self,
        *,
        design_payload: bytes,
        artifact_path: Path,
        report_path: Path,
        timeout_seconds: float,
    ) -> None:
        self.calls += 1
        assert design_payload == self.design.canonical_json_bytes()
        artifact_path.write_bytes(b"GATE024-SYNTHETIC-FCSTD")
        report_path.write_text(
            json.dumps(report_payload(self.design, mismatch=self.mismatch), sort_keys=True),
            encoding="utf-8",
        )


def make_policy() -> dict:
    return load_fixture("valid_policy.json")


def make_state(*, allow_propose_patch: bool) -> dict:
    state = load_fixture("valid_state.json")
    state["current_gate"] = "024"
    state["active_job_id"] = None
    state["repository_ref"] = {
        "branch": "gate-024-controlled-parametric-cad-worker",
        "head_sha": "synthetic-gate024-smoke",
    }
    state["pending_checks"] = []
    state["blockers"] = []
    state["next_admissible_action"] = "validate CAD proposal"
    autonomous = state["effective_permissions"]["autonomous"]
    if allow_propose_patch and "propose_patch" not in autonomous:
        autonomous.append("propose_patch")
    if not allow_propose_patch and "propose_patch" in autonomous:
        autonomous.remove("propose_patch")
    return state


def make_job() -> dict:
    job = load_fixture("valid_job.json")
    job["job_id"] = "gate-024-smoke"
    job["gate_id"] = "024"
    job["objective"] = "Exercise the bounded CAD proposal boundary"
    job["scope"] = ["typed CAD proposal", "deterministic geometry"]
    job["out_of_scope"] = ["fabrication", "release", "physical validation"]
    job["requested_actions"] = ["propose_patch"]
    job["required_validators"] = []
    job["retry_limit"] = 1
    job["attempts"] = 0
    job["status"] = "QUEUED"
    job["blocker"] = None
    return job


def main() -> int:
    design = make_design()
    geometry = geometry_report_for_design(design)

    denied_runtime = SyntheticCadRuntime(design)
    with tempfile.TemporaryDirectory() as tmp:
        denied_worker = CadWorker(
            adapter=ParametricCadAdapter(tmp, runtime=denied_runtime)
        )
        denied = denied_worker.generate_proposal(
            CadWorkerRequest(
                project_id="engineering-ai",
                task_id="gate024-denied",
                design=design,
                output_relative_path="cad/denied.FCStd",
            ),
            supervisor=Supervisor(
                policy=make_policy(),
                state=make_state(allow_propose_patch=False),
            ),
            job=make_job(),
        )
        assert denied.decision.decision is Decision.DENY
        assert denied.tool_called is False
        assert denied_runtime.calls == 0
        assert not (Path(tmp) / "cad" / "denied.FCStd").exists()

    allowed_runtime = SyntheticCadRuntime(design)
    with tempfile.TemporaryDirectory() as tmp:
        allowed_worker = CadWorker(
            adapter=ParametricCadAdapter(tmp, runtime=allowed_runtime)
        )
        allowed = allowed_worker.generate_proposal(
            CadWorkerRequest(
                project_id="engineering-ai",
                task_id="gate024-allowed",
                design=design,
                output_relative_path="cad/allowed.FCStd",
            ),
            supervisor=Supervisor(
                policy=make_policy(),
                state=make_state(allow_propose_patch=True),
            ),
            job=make_job(),
        )
        target = Path(tmp) / "cad" / "allowed.FCStd"
        assert allowed.decision.decision is Decision.ALLOW
        assert allowed.tool_called is True
        assert allowed.outcome_ok is True
        assert allowed.artifact is not None
        assert allowed_runtime.calls == 1
        assert target.is_file()
        assert allowed.artifact.design_sha256 == design.design_sha256
        assert allowed.artifact.geometry_report_sha256 == geometry.report_sha256
        assert allowed.authority == "PROPOSED_PATCH_ONLY"
        assert allowed.evidence_eligible_geometry is True
        assert allowed.evidence_eligible_design_correctness is False
        assert allowed.physical_validation == "PHYSICAL_NOT_EXECUTED"

    mismatch_runtime = SyntheticCadRuntime(design, mismatch=True)
    with tempfile.TemporaryDirectory() as tmp:
        adapter = ParametricCadAdapter(tmp, runtime=mismatch_runtime)
        mismatch_blocked = False
        try:
            adapter.generate(
                design=design,
                relative_path="cad/mismatch.FCStd",
            )
        except CadBackendError:
            mismatch_blocked = True
        assert mismatch_blocked
        assert mismatch_runtime.calls == 1
        assert not (Path(tmp) / "cad" / "mismatch.FCStd").exists()

    payload = {
        "gate": "024",
        "state": "PASS_CONTROLLED_PARAMETRIC_CAD_BOUNDARY",
        "policy_denial_backend_calls": denied_runtime.calls,
        "approved_propose_patch_backend_calls": allowed_runtime.calls,
        "geometry_mismatch_blocked": True,
        "mismatch_artifact_published": False,
        "design_sha256_preserved": True,
        "geometry_sha256_preserved": True,
        "artifact_authority": "PROPOSED_PATCH_ONLY",
        "geometry_evidence_eligible": True,
        "design_correctness_evidence_eligible": False,
        "arbitrary_model_script_surface": False,
        "shell_surface": False,
        "fabrication_authority": False,
        "release_authority": False,
        "real_freecad_runtime_required_for_ci": False,
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
