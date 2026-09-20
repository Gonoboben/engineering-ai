"""Bounded parametric CAD specification, geometry checks, and FreeCAD bridge.

Gate 024 deliberately exposes data, not executable CAD/Python source.  A caller
supplies an immutable parametric design and a root-bounded FCStd target.  The
trusted FreeCAD helper is repository-owned and fixed by this module; model-
supplied scripts, shell commands, macros, and arbitrary process arguments are
not accepted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Protocol

from engineering_ai.tools.common import ToolAccessError, ToolExecutionError


MAX_COORDINATE_MM = 1_000_000.0
MAX_DIMENSION_MM = 1_000_000.0
MAX_ENTITIES = 128
MAX_ARTIFACT_BYTES = 256 * 1024 * 1024
MAX_RUNTIME_REPORT_BYTES = 1 * 1024 * 1024
GEOMETRY_REL_TOL = 1e-7
GEOMETRY_ABS_TOL = 1e-6


class CadSpecError(ValueError):
    """Raised when a CAD specification is invalid or outside Gate 024 bounds."""


class CadBackendError(ToolExecutionError):
    """Raised when the trusted CAD runtime fails or violates its result contract."""


class CadPrimitiveKind(str, Enum):
    BOX = "BOX"
    CYLINDER = "CYLINDER"


def _bounded_number(value: float, *, name: str, positive: bool = False) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise CadSpecError(f"{name} must be finite")
    if positive and number <= 0:
        raise CadSpecError(f"{name} must be positive")
    limit = MAX_DIMENSION_MM if positive else MAX_COORDINATE_MM
    if abs(number) > limit:
        raise CadSpecError(f"{name} exceeds Gate 024 bound")
    return number


def _validate_entity_id(entity_id: str) -> str:
    value = entity_id.strip()
    if not value or len(value) > 64:
        raise CadSpecError("entity_id must contain 1..64 characters")
    ascii_letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    ascii_digits = "0123456789"
    if value[0] not in ascii_letters + "_":
        raise CadSpecError("entity_id must start with an ASCII letter or underscore")
    if any(ch not in ascii_letters + ascii_digits + "_" for ch in value):
        raise CadSpecError("entity_id accepts only ASCII letters, digits, and underscore")
    return value


@dataclass(frozen=True)
class CadPlacement:
    x_mm: float = 0.0
    y_mm: float = 0.0
    z_mm: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "x_mm", _bounded_number(self.x_mm, name="x_mm"))
        object.__setattr__(self, "y_mm", _bounded_number(self.y_mm, name="y_mm"))
        object.__setattr__(self, "z_mm", _bounded_number(self.z_mm, name="z_mm"))

    def as_dict(self) -> dict[str, float]:
        return {"x_mm": self.x_mm, "y_mm": self.y_mm, "z_mm": self.z_mm}


@dataclass(frozen=True)
class CadBox:
    entity_id: str
    length_mm: float
    width_mm: float
    height_mm: float
    placement: CadPlacement = CadPlacement()

    kind: CadPrimitiveKind = field(default=CadPrimitiveKind.BOX, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity_id", _validate_entity_id(self.entity_id))
        if not isinstance(self.placement, CadPlacement):
            raise CadSpecError("box placement must be CadPlacement")
        object.__setattr__(
            self, "length_mm", _bounded_number(self.length_mm, name="length_mm", positive=True)
        )
        object.__setattr__(
            self, "width_mm", _bounded_number(self.width_mm, name="width_mm", positive=True)
        )
        object.__setattr__(
            self, "height_mm", _bounded_number(self.height_mm, name="height_mm", positive=True)
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "entity_id": self.entity_id,
            "kind": self.kind.value,
            "length_mm": self.length_mm,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "placement": self.placement.as_dict(),
        }


@dataclass(frozen=True)
class CadCylinder:
    entity_id: str
    radius_mm: float
    height_mm: float
    placement: CadPlacement = CadPlacement()

    kind: CadPrimitiveKind = field(default=CadPrimitiveKind.CYLINDER, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity_id", _validate_entity_id(self.entity_id))
        if not isinstance(self.placement, CadPlacement):
            raise CadSpecError("cylinder placement must be CadPlacement")
        object.__setattr__(
            self, "radius_mm", _bounded_number(self.radius_mm, name="radius_mm", positive=True)
        )
        object.__setattr__(
            self, "height_mm", _bounded_number(self.height_mm, name="height_mm", positive=True)
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "entity_id": self.entity_id,
            "kind": self.kind.value,
            "radius_mm": self.radius_mm,
            "height_mm": self.height_mm,
            "placement": self.placement.as_dict(),
        }


CadEntity = CadBox | CadCylinder


@dataclass(frozen=True)
class CadDesignSpec:
    project_id: str
    design_id: str
    entities: tuple[CadEntity, ...]
    units: str = "mm"

    def __post_init__(self) -> None:
        project_id = self.project_id.strip()
        design_id = self.design_id.strip()
        if not project_id or len(project_id) > 128:
            raise CadSpecError("project_id must contain 1..128 characters")
        if not design_id or len(design_id) > 128:
            raise CadSpecError("design_id must contain 1..128 characters")
        if self.units != "mm":
            raise CadSpecError("Gate 024 CAD baseline supports millimetres only")
        entities = tuple(self.entities)
        if not entities:
            raise CadSpecError("CAD design requires at least one entity")
        if len(entities) > MAX_ENTITIES:
            raise CadSpecError("CAD entity count exceeds Gate 024 bound")
        if any(not isinstance(entity, (CadBox, CadCylinder)) for entity in entities):
            raise CadSpecError("Gate 024 accepts only typed box/cylinder entities")
        ids = [entity.entity_id for entity in entities]
        if len(ids) != len(set(ids)):
            raise CadSpecError("CAD entity_id values must be unique")
        object.__setattr__(self, "project_id", project_id)
        object.__setattr__(self, "design_id", design_id)
        object.__setattr__(self, "entities", entities)

    def as_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "design_id": self.design_id,
            "units": self.units,
            "entities": [entity.as_dict() for entity in self.entities],
        }

    def canonical_json_bytes(self) -> bytes:
        return json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")

    @property
    def design_sha256(self) -> str:
        return hashlib.sha256(self.canonical_json_bytes()).hexdigest()


@dataclass(frozen=True)
class CadAabb:
    min_x_mm: float
    min_y_mm: float
    min_z_mm: float
    max_x_mm: float
    max_y_mm: float
    max_z_mm: float

    def as_dict(self) -> dict[str, float]:
        return {
            "min_x_mm": self.min_x_mm,
            "min_y_mm": self.min_y_mm,
            "min_z_mm": self.min_z_mm,
            "max_x_mm": self.max_x_mm,
            "max_y_mm": self.max_y_mm,
            "max_z_mm": self.max_z_mm,
        }


@dataclass(frozen=True)
class CadEntityGeometry:
    entity_id: str
    kind: CadPrimitiveKind
    volume_mm3: float
    aabb: CadAabb

    def as_dict(self) -> dict[str, object]:
        return {
            "entity_id": self.entity_id,
            "kind": self.kind.value,
            "volume_mm3": self.volume_mm3,
            "aabb": self.aabb.as_dict(),
        }


@dataclass(frozen=True)
class CadGeometryReport:
    design_sha256: str
    entities: tuple[CadEntityGeometry, ...]
    assembly_aabb: CadAabb
    total_primitive_volume_mm3: float
    volume_semantics: str = "SUM_OF_PRIMITIVES_NOT_BOOLEAN_UNION"

    def as_dict(self) -> dict[str, object]:
        return {
            "design_sha256": self.design_sha256,
            "entities": [item.as_dict() for item in self.entities],
            "assembly_aabb": self.assembly_aabb.as_dict(),
            "total_primitive_volume_mm3": self.total_primitive_volume_mm3,
            "volume_semantics": self.volume_semantics,
        }

    @property
    def report_sha256(self) -> str:
        raw = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def geometry_report_for_design(design: CadDesignSpec) -> CadGeometryReport:
    geometries: list[CadEntityGeometry] = []
    for entity in design.entities:
        p = entity.placement
        if isinstance(entity, CadBox):
            aabb = CadAabb(
                min_x_mm=p.x_mm,
                min_y_mm=p.y_mm,
                min_z_mm=p.z_mm,
                max_x_mm=p.x_mm + entity.length_mm,
                max_y_mm=p.y_mm + entity.width_mm,
                max_z_mm=p.z_mm + entity.height_mm,
            )
            volume = entity.length_mm * entity.width_mm * entity.height_mm
        elif isinstance(entity, CadCylinder):
            aabb = CadAabb(
                min_x_mm=p.x_mm - entity.radius_mm,
                min_y_mm=p.y_mm - entity.radius_mm,
                min_z_mm=p.z_mm,
                max_x_mm=p.x_mm + entity.radius_mm,
                max_y_mm=p.y_mm + entity.radius_mm,
                max_z_mm=p.z_mm + entity.height_mm,
            )
            volume = math.pi * entity.radius_mm * entity.radius_mm * entity.height_mm
        else:  # pragma: no cover - union is closed by type + construction
            raise CadSpecError("unsupported CAD entity type")
        geometries.append(
            CadEntityGeometry(
                entity_id=entity.entity_id,
                kind=entity.kind,
                volume_mm3=volume,
                aabb=aabb,
            )
        )

    assembly = CadAabb(
        min_x_mm=min(item.aabb.min_x_mm for item in geometries),
        min_y_mm=min(item.aabb.min_y_mm for item in geometries),
        min_z_mm=min(item.aabb.min_z_mm for item in geometries),
        max_x_mm=max(item.aabb.max_x_mm for item in geometries),
        max_y_mm=max(item.aabb.max_y_mm for item in geometries),
        max_z_mm=max(item.aabb.max_z_mm for item in geometries),
    )
    return CadGeometryReport(
        design_sha256=design.design_sha256,
        entities=tuple(geometries),
        assembly_aabb=assembly,
        total_primitive_volume_mm3=sum(item.volume_mm3 for item in geometries),
    )


@dataclass(frozen=True)
class CadRuntimeReport:
    backend: str
    backend_version: str
    design_sha256: str
    entities: tuple[CadEntityGeometry, ...]
    assembly_aabb: CadAabb
    total_primitive_volume_mm3: float


@dataclass(frozen=True)
class CadArtifactResult:
    relative_path: str
    artifact_sha256: str
    artifact_size_bytes: int
    design_sha256: str
    geometry_report_sha256: str
    backend: str
    backend_version: str
    physical_validation: str = "PHYSICAL_NOT_EXECUTED"


class CadRuntime(Protocol):
    def generate(
        self,
        *,
        design_payload: bytes,
        artifact_path: Path,
        report_path: Path,
        timeout_seconds: float,
    ) -> None: ...


class FreeCadRuntime:
    """Invoke only the repository-owned FreeCAD helper with data-only JSON input."""

    def __init__(self, executable: str = "FreeCADCmd") -> None:
        if not executable.strip():
            raise ValueError("FreeCAD executable is required")
        self._executable = executable
        self._helper_script = (
            Path(__file__).resolve().parents[3] / "scripts" / "freecad_parametric_worker.py"
        ).resolve(strict=True)

    def _resolve_executable(self) -> Path:
        candidate = Path(self._executable)
        if candidate.is_absolute():
            resolved = candidate.resolve(strict=True)
        else:
            found = shutil.which(self._executable)
            if found is None:
                raise CadBackendError("FreeCADCmd is not available")
            resolved = Path(found).resolve(strict=True)
        if not resolved.is_file():
            raise CadBackendError("configured FreeCADCmd is not a file")
        return resolved

    def generate(
        self,
        *,
        design_payload: bytes,
        artifact_path: Path,
        report_path: Path,
        timeout_seconds: float,
    ) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 300:
            raise CadBackendError("CAD runtime timeout must be in (0, 300]")
        executable = self._resolve_executable()
        input_path = artifact_path.with_suffix(".design.json")
        input_path.write_bytes(design_payload)
        argv = [
            str(executable),
            str(self._helper_script),
            "--input",
            str(input_path),
            "--artifact",
            str(artifact_path),
            "--report",
            str(report_path),
        ]
        try:
            completed = subprocess.run(
                argv,
                cwd=artifact_path.parent,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise CadBackendError("FreeCAD runtime timed out") from exc
        if completed.returncode != 0:
            raise CadBackendError(f"FreeCAD runtime exited with code {completed.returncode}")


class ParametricCadAdapter:
    """Generate one root-bounded FCStd proposal after deterministic verification."""

    def __init__(
        self,
        root: str | Path,
        *,
        runtime: CadRuntime | None = None,
        max_artifact_bytes: int = MAX_ARTIFACT_BYTES,
    ) -> None:
        self._root = Path(root).resolve(strict=True)
        if not self._root.is_dir():
            raise ValueError("CAD root must be a directory")
        if max_artifact_bytes <= 0:
            raise ValueError("max_artifact_bytes must be positive")
        self._runtime = runtime or FreeCadRuntime()
        self._max_artifact_bytes = max_artifact_bytes

    def generate(
        self,
        *,
        design: CadDesignSpec,
        relative_path: str,
        timeout_seconds: float = 120.0,
    ) -> CadArtifactResult:
        expected = geometry_report_for_design(design)
        target = self._resolve_target(relative_path)
        if timeout_seconds <= 0 or timeout_seconds > 300:
            raise CadBackendError("CAD timeout must be in (0, 300]")

        with tempfile.TemporaryDirectory(prefix=".engineering-ai-cad-", dir=self._root) as tmp:
            tmp_dir = Path(tmp)
            temp_artifact = tmp_dir / "candidate.FCStd"
            report_path = tmp_dir / "runtime-report.json"
            self._runtime.generate(
                design_payload=design.canonical_json_bytes(),
                artifact_path=temp_artifact,
                report_path=report_path,
                timeout_seconds=timeout_seconds,
            )
            self._validate_candidate_artifact(temp_artifact)
            runtime_report = self._load_runtime_report(report_path)
            self._verify_runtime_geometry(expected, runtime_report)

            artifact_bytes = temp_artifact.read_bytes()
            artifact_sha = hashlib.sha256(artifact_bytes).hexdigest()
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(temp_artifact, target)
            except OSError as exc:
                raise CadBackendError("CAD artifact publication failed") from exc

        return CadArtifactResult(
            relative_path=relative_path.replace("\\", "/"),
            artifact_sha256=artifact_sha,
            artifact_size_bytes=len(artifact_bytes),
            design_sha256=design.design_sha256,
            geometry_report_sha256=expected.report_sha256,
            backend=runtime_report.backend,
            backend_version=runtime_report.backend_version,
        )

    def _resolve_target(self, relative_path: str) -> Path:
        if not relative_path.strip():
            raise ToolAccessError("CAD artifact path is required")
        relative = Path(relative_path)
        if relative.is_absolute():
            raise ToolAccessError("absolute CAD artifact paths are not allowed")
        if relative.suffix.lower() != ".fcstd":
            raise ToolAccessError("Gate 024 publishes FCStd artifacts only")
        candidate = self._root / relative
        if candidate.is_symlink():
            raise ToolAccessError("CAD artifact target symlink is not allowed")
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(self._root)
        except ValueError as exc:
            raise ToolAccessError("CAD artifact path escapes configured root") from exc
        return resolved

    def _validate_candidate_artifact(self, artifact_path: Path) -> None:
        if artifact_path.is_symlink():
            raise CadBackendError("CAD runtime FCStd artifact symlink is not allowed")
        if not artifact_path.is_file():
            raise CadBackendError("CAD runtime did not produce an FCStd artifact")
        size = artifact_path.stat().st_size
        if size <= 0:
            raise CadBackendError("CAD runtime produced an empty FCStd artifact")
        if size > self._max_artifact_bytes:
            raise CadBackendError("CAD artifact exceeds configured size bound")

    @staticmethod
    def _load_runtime_report(report_path: Path) -> CadRuntimeReport:
        if report_path.is_symlink():
            raise CadBackendError("CAD runtime geometry report symlink is not allowed")
        if not report_path.is_file():
            raise CadBackendError("CAD runtime did not produce a geometry report")
        raw = report_path.read_bytes()
        if len(raw) > MAX_RUNTIME_REPORT_BYTES:
            raise CadBackendError("CAD runtime geometry report exceeds size bound")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CadBackendError("CAD runtime geometry report is invalid JSON") from exc
        return _runtime_report_from_payload(payload)

    @staticmethod
    def _verify_runtime_geometry(
        expected: CadGeometryReport,
        actual: CadRuntimeReport,
    ) -> None:
        if actual.design_sha256 != expected.design_sha256:
            raise CadBackendError("CAD runtime design hash does not match requested design")
        if len(actual.entities) != len(expected.entities):
            raise CadBackendError("CAD runtime entity count mismatch")
        expected_by_id = {item.entity_id: item for item in expected.entities}
        actual_by_id = {item.entity_id: item for item in actual.entities}
        if set(actual_by_id) != set(expected_by_id):
            raise CadBackendError("CAD runtime entity identity mismatch")
        for entity_id, exp in expected_by_id.items():
            got = actual_by_id[entity_id]
            if got.kind is not exp.kind:
                raise CadBackendError("CAD runtime entity kind mismatch")
            _assert_close(got.volume_mm3, exp.volume_mm3, "entity volume")
            _assert_aabb_close(got.aabb, exp.aabb, "entity AABB")
        _assert_aabb_close(actual.assembly_aabb, expected.assembly_aabb, "assembly AABB")
        _assert_close(
            actual.total_primitive_volume_mm3,
            expected.total_primitive_volume_mm3,
            "total primitive volume",
        )


def _assert_close(actual: float, expected: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=GEOMETRY_REL_TOL, abs_tol=GEOMETRY_ABS_TOL):
        raise CadBackendError(f"CAD runtime {label} mismatch")


def _assert_aabb_close(actual: CadAabb, expected: CadAabb, label: str) -> None:
    for field in (
        "min_x_mm",
        "min_y_mm",
        "min_z_mm",
        "max_x_mm",
        "max_y_mm",
        "max_z_mm",
    ):
        _assert_close(getattr(actual, field), getattr(expected, field), f"{label} {field}")


def _runtime_report_from_payload(payload: object) -> CadRuntimeReport:
    if not isinstance(payload, dict):
        raise CadBackendError("CAD runtime report must be an object")
    required = {
        "backend",
        "backend_version",
        "design_sha256",
        "entities",
        "assembly_aabb",
        "total_primitive_volume_mm3",
    }
    if set(payload) != required:
        raise CadBackendError("CAD runtime report has unexpected fields")
    backend = payload["backend"]
    backend_version = payload["backend_version"]
    design_sha = payload["design_sha256"]
    if not isinstance(backend, str) or not backend.strip() or len(backend) > 128:
        raise CadBackendError("CAD runtime backend identity is invalid")
    if not isinstance(backend_version, str) or not backend_version.strip() or len(backend_version) > 128:
        raise CadBackendError("CAD runtime backend version is invalid")
    if not isinstance(design_sha, str) or len(design_sha) != 64:
        raise CadBackendError("CAD runtime design SHA-256 is invalid")

    raw_entities = payload["entities"]
    if not isinstance(raw_entities, list) or not raw_entities or len(raw_entities) > MAX_ENTITIES:
        raise CadBackendError("CAD runtime entities are invalid")
    entities: list[CadEntityGeometry] = []
    ids: set[str] = set()
    for raw in raw_entities:
        if not isinstance(raw, dict) or set(raw) != {"entity_id", "kind", "volume_mm3", "aabb"}:
            raise CadBackendError("CAD runtime entity record is invalid")
        entity_id = _validate_entity_id(str(raw["entity_id"]))
        if entity_id in ids:
            raise CadBackendError("CAD runtime entity identities are duplicated")
        ids.add(entity_id)
        try:
            kind = CadPrimitiveKind(raw["kind"])
        except (ValueError, TypeError) as exc:
            raise CadBackendError("CAD runtime entity kind is invalid") from exc
        volume = _report_number(raw["volume_mm3"], "volume_mm3", positive=True)
        entities.append(
            CadEntityGeometry(
                entity_id=entity_id,
                kind=kind,
                volume_mm3=volume,
                aabb=_aabb_from_payload(raw["aabb"]),
            )
        )

    total = _report_number(
        payload["total_primitive_volume_mm3"],
        "total_primitive_volume_mm3",
        positive=True,
    )
    return CadRuntimeReport(
        backend=backend,
        backend_version=backend_version,
        design_sha256=design_sha,
        entities=tuple(entities),
        assembly_aabb=_aabb_from_payload(payload["assembly_aabb"]),
        total_primitive_volume_mm3=total,
    )


def _aabb_from_payload(payload: object) -> CadAabb:
    keys = {
        "min_x_mm",
        "min_y_mm",
        "min_z_mm",
        "max_x_mm",
        "max_y_mm",
        "max_z_mm",
    }
    if not isinstance(payload, dict) or set(payload) != keys:
        raise CadBackendError("CAD runtime AABB record is invalid")
    values = {key: _report_number(payload[key], key) for key in keys}
    if (
        values["max_x_mm"] < values["min_x_mm"]
        or values["max_y_mm"] < values["min_y_mm"]
        or values["max_z_mm"] < values["min_z_mm"]
    ):
        raise CadBackendError("CAD runtime AABB ordering is invalid")
    return CadAabb(**values)


def _report_number(value: object, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CadBackendError(f"CAD runtime {name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise CadBackendError(f"CAD runtime {name} must be finite")
    if positive and number <= 0:
        raise CadBackendError(f"CAD runtime {name} must be positive")
    return number
