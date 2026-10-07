from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

from engineering_ai.supervisor import CadWorker, CadWorkerRequest, Decision, Supervisor
from engineering_ai.tools import (
    CadBackendError,
    CadBox,
    CadCylinder,
    CadDesignSpec,
    CadPlacement,
    CadSpecError,
    ParametricCadAdapter,
    ToolAccessError,
    geometry_report_for_design,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def load_fixture(name: str) -> dict:
    with (FIXTURES / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sample_design() -> CadDesignSpec:
    return CadDesignSpec(
        project_id="engineering-ai",
        design_id="gate024-sample",
        entities=(
            CadBox(
                entity_id="Base",
                length_mm=20.0,
                width_mm=10.0,
                height_mm=4.0,
                placement=CadPlacement(1.0, 2.0, 3.0),
            ),
            CadCylinder(
                entity_id="Post",
                radius_mm=2.0,
                height_mm=8.0,
                placement=CadPlacement(15.0, 7.0, 4.0),
            ),
        ),
    )


def runtime_report_payload(design: CadDesignSpec, *, mismatch: bool = False) -> dict:
    report = geometry_report_for_design(design)
    entities = [item.as_dict() for item in report.entities]
    total = report.total_primitive_volume_mm3
    if mismatch:
        entities[0]["volume_mm3"] = float(entities[0]["volume_mm3"]) + 5.0
    return {
        "backend": "fake-freecad",
        "backend_version": "gate024-test",
        "design_sha256": design.design_sha256,
        "entities": entities,
        "assembly_aabb": report.assembly_aabb.as_dict(),
        "total_primitive_volume_mm3": total,
    }


class FakeCadRuntime:
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
        self.last_payload = design_payload
        self.last_timeout = timeout_seconds
        artifact_path.write_bytes(b"synthetic-fcstd-gate024")
        report_path.write_text(
            json.dumps(
                runtime_report_payload(self.design, mismatch=self.mismatch),
                sort_keys=True,
            ),
            encoding="utf-8",
        )


def make_policy() -> dict:
    policy = load_fixture("valid_policy.json")
    policy["mandatory_validators"] = []
    return policy


def make_state(*, allow_propose_patch: bool) -> dict:
    state = load_fixture("valid_state.json")
    state["current_gate"] = "024"
    state["active_job_id"] = None
    state["repository_ref"] = {
        "branch": "gate-024-controlled-parametric-cad-worker",
        "head_sha": "f3c826a434eca8e5d7163f5cf4166560717bdbc2",
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
    job["job_id"] = "gate-024-cad-test"
    job["gate_id"] = "024"
    job["objective"] = "Generate one bounded CAD proposal"
    job["scope"] = ["typed parametric CAD", "deterministic geometry"]
    job["out_of_scope"] = ["fabrication", "release", "physical validation"]
    job["requested_actions"] = ["propose_patch"]
    job["required_validators"] = []
    job["retry_limit"] = 1
    job["attempts"] = 0
    job["status"] = "QUEUED"
    job["blocker"] = None
    return job


class CadGeometryTests(unittest.TestCase):
    def test_design_hash_and_geometry_are_deterministic(self) -> None:
        design = sample_design()
        first = geometry_report_for_design(design)
        second = geometry_report_for_design(design)

        self.assertEqual(first, second)
        self.assertEqual(len(design.design_sha256), 64)
        self.assertEqual(first.design_sha256, design.design_sha256)
        self.assertEqual(len(first.report_sha256), 64)
        self.assertEqual(first.entities[0].volume_mm3, 20.0 * 10.0 * 4.0)
        self.assertTrue(
            math.isclose(
                first.entities[1].volume_mm3,
                math.pi * 2.0 * 2.0 * 8.0,
                rel_tol=1e-12,
            )
        )
        self.assertEqual(first.assembly_aabb.min_x_mm, 1.0)
        self.assertEqual(first.assembly_aabb.max_z_mm, 12.0)
        self.assertEqual(first.volume_semantics, "SUM_OF_PRIMITIVES_NOT_BOOLEAN_UNION")

    def test_invalid_or_ambiguous_design_fails_closed(self) -> None:
        with self.assertRaises(CadSpecError):
            CadBox(entity_id="bad id", length_mm=1, width_mm=1, height_mm=1)
        with self.assertRaises(CadSpecError):
            CadCylinder(entity_id="C", radius_mm=0, height_mm=1)
        with self.assertRaises(CadSpecError):
            CadBox(entity_id="B", length_mm=float("nan"), width_mm=1, height_mm=1)
        with self.assertRaises(CadSpecError):
            CadDesignSpec(
                project_id="engineering-ai",
                design_id="duplicate",
                entities=(
                    CadBox("Same", 1, 1, 1),
                    CadBox("Same", 2, 2, 2),
                ),
            )

    def test_primitive_kind_cannot_be_overridden_by_input(self) -> None:
        with self.assertRaises(TypeError):
            CadBox("B", 1, 1, 1, kind="CYLINDER")


class ParametricCadAdapterTests(unittest.TestCase):
    def test_valid_candidate_is_published_only_after_geometry_match(self) -> None:
        design = sample_design()
        runtime = FakeCadRuntime(design)
        with tempfile.TemporaryDirectory() as tmp:
            adapter = ParametricCadAdapter(tmp, runtime=runtime)
            result = adapter.generate(
                design=design,
                relative_path="cad/sample.FCStd",
                timeout_seconds=20,
            )
            target = Path(tmp) / "cad" / "sample.FCStd"

            self.assertEqual(runtime.calls, 1)
            self.assertTrue(target.is_file())
            self.assertEqual(target.read_bytes(), b"synthetic-fcstd-gate024")
            self.assertEqual(result.design_sha256, design.design_sha256)
            self.assertEqual(result.physical_validation, "PHYSICAL_NOT_EXECUTED")
            self.assertEqual(result.backend, "fake-freecad")
            self.assertEqual(len(result.artifact_sha256), 64)
            self.assertEqual(len(result.geometry_report_sha256), 64)

    def test_path_escape_and_wrong_extension_are_rejected_before_runtime(self) -> None:
        design = sample_design()
        runtime = FakeCadRuntime(design)
        with tempfile.TemporaryDirectory() as tmp:
            adapter = ParametricCadAdapter(tmp, runtime=runtime)
            with self.assertRaises(ToolAccessError):
                adapter.generate(design=design, relative_path="../escape.FCStd")
            with self.assertRaises(ToolAccessError):
                adapter.generate(design=design, relative_path="cad/model.step")
            self.assertEqual(runtime.calls, 0)

    def test_runtime_geometry_mismatch_fails_without_publishing_target(self) -> None:
        design = sample_design()
        runtime = FakeCadRuntime(design, mismatch=True)
        with tempfile.TemporaryDirectory() as tmp:
            adapter = ParametricCadAdapter(tmp, runtime=runtime)
            target = Path(tmp) / "cad" / "mismatch.FCStd"
            with self.assertRaises(CadBackendError):
                adapter.generate(design=design, relative_path="cad/mismatch.FCStd")
            self.assertEqual(runtime.calls, 1)
            self.assertFalse(target.exists())


class CadWorkerTests(unittest.TestCase):
    def test_policy_denial_makes_zero_backend_calls(self) -> None:
        design = sample_design()
        runtime = FakeCadRuntime(design)
        with tempfile.TemporaryDirectory() as tmp:
            worker = CadWorker(adapter=ParametricCadAdapter(tmp, runtime=runtime))
            supervisor = Supervisor(
                policy=make_policy(),
                state=make_state(allow_propose_patch=False),
            )
            result = worker.generate_proposal(
                CadWorkerRequest(
                    project_id="engineering-ai",
                    task_id="cad-denied",
                    design=design,
                    output_relative_path="cad/denied.FCStd",
                ),
                supervisor=supervisor,
                job=make_job(),
            )

            self.assertEqual(result.decision.decision, Decision.DENY)
            self.assertFalse(result.tool_called)
            self.assertFalse(result.outcome_ok)
            self.assertIsNone(result.artifact)
            self.assertEqual(runtime.calls, 0)
            self.assertEqual(result.physical_validation, "PHYSICAL_NOT_EXECUTED")

    def test_allowed_propose_patch_returns_bounded_nonphysical_artifact(self) -> None:
        design = sample_design()
        runtime = FakeCadRuntime(design)
        with tempfile.TemporaryDirectory() as tmp:
            worker = CadWorker(adapter=ParametricCadAdapter(tmp, runtime=runtime))
            supervisor = Supervisor(
                policy=make_policy(),
                state=make_state(allow_propose_patch=True),
            )
            result = worker.generate_proposal(
                CadWorkerRequest(
                    project_id="engineering-ai",
                    task_id="cad-allowed",
                    design=design,
                    output_relative_path="cad/allowed.FCStd",
                ),
                supervisor=supervisor,
                job=make_job(),
            )

            self.assertEqual(result.decision.decision, Decision.ALLOW)
            self.assertTrue(result.tool_called)
            self.assertTrue(result.outcome_ok)
            self.assertIsNotNone(result.artifact)
            self.assertEqual(runtime.calls, 1)
            self.assertEqual(result.authority, "PROPOSED_PATCH_ONLY")
            self.assertTrue(result.evidence_eligible_geometry)
            self.assertFalse(result.evidence_eligible_design_correctness)
            self.assertEqual(result.physical_validation, "PHYSICAL_NOT_EXECUTED")


if __name__ == "__main__":
    unittest.main()
