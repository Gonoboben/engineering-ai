"""Trusted data-only FreeCAD helper for Gate 024.

This file is executed by FreeCADCmd. It accepts only a JSON design produced by
engineering_ai.tools.cad and writes one FCStd artifact plus a bounded geometry
report. It intentionally contains no eval/exec, dynamic imports, macros, or
model-provided source execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--report", required=True)
    return parser.parse_args()


def _require_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not (-1.0e12 < number < 1.0e12):
        raise ValueError(f"{name} outside helper bound")
    return number


def _placement(entity):
    raw = entity.get("placement")
    if not isinstance(raw, dict) or set(raw) != {"x_mm", "y_mm", "z_mm"}:
        raise ValueError("invalid placement")
    return (
        _require_number(raw["x_mm"], "x_mm"),
        _require_number(raw["y_mm"], "y_mm"),
        _require_number(raw["z_mm"], "z_mm"),
    )


def _aabb(shape):
    bb = shape.BoundBox
    return {
        "min_x_mm": float(bb.XMin),
        "min_y_mm": float(bb.YMin),
        "min_z_mm": float(bb.ZMin),
        "max_x_mm": float(bb.XMax),
        "max_y_mm": float(bb.YMax),
        "max_z_mm": float(bb.ZMax),
    }


def main() -> int:
    args = _parse_args()
    input_path = Path(args.input).resolve(strict=True)
    artifact_path = Path(args.artifact).resolve(strict=False)
    report_path = Path(args.report).resolve(strict=False)
    if artifact_path.suffix.lower() != ".fcstd":
        raise ValueError("artifact must be FCStd")

    raw = input_path.read_bytes()
    design_sha256 = hashlib.sha256(raw).hexdigest()
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("design must be an object")
    if set(payload) != {"project_id", "design_id", "units", "entities"}:
        raise ValueError("design has unexpected fields")
    if payload["units"] != "mm":
        raise ValueError("only millimetres are supported")
    entities = payload["entities"]
    if not isinstance(entities, list) or not entities or len(entities) > 128:
        raise ValueError("invalid entity list")

    import FreeCAD as App

    document = App.newDocument("EngineeringAI_Gate024")
    created = []
    seen = set()
    try:
        for entity in entities:
            if not isinstance(entity, dict):
                raise ValueError("entity must be an object")
            entity_id = entity.get("entity_id")
            kind = entity.get("kind")
            if not isinstance(entity_id, str) or not entity_id or entity_id in seen:
                raise ValueError("invalid or duplicate entity_id")
            seen.add(entity_id)
            x_mm, y_mm, z_mm = _placement(entity)

            if kind == "BOX":
                expected_keys = {
                    "entity_id",
                    "kind",
                    "length_mm",
                    "width_mm",
                    "height_mm",
                    "placement",
                }
                if set(entity) != expected_keys:
                    raise ValueError("BOX has unexpected fields")
                obj = document.addObject("Part::Box", entity_id)
                obj.Length = _require_number(entity["length_mm"], "length_mm")
                obj.Width = _require_number(entity["width_mm"], "width_mm")
                obj.Height = _require_number(entity["height_mm"], "height_mm")
            elif kind == "CYLINDER":
                expected_keys = {
                    "entity_id",
                    "kind",
                    "radius_mm",
                    "height_mm",
                    "placement",
                }
                if set(entity) != expected_keys:
                    raise ValueError("CYLINDER has unexpected fields")
                obj = document.addObject("Part::Cylinder", entity_id)
                obj.Radius = _require_number(entity["radius_mm"], "radius_mm")
                obj.Height = _require_number(entity["height_mm"], "height_mm")
                obj.Angle = 360.0
            else:
                raise ValueError("unsupported primitive kind")

            obj.Placement.Base = App.Vector(x_mm, y_mm, z_mm)
            created.append((entity_id, kind, obj))

        document.recompute()
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        document.saveAs(str(artifact_path))

        report_entities = []
        for entity_id, kind, obj in created:
            shape = obj.Shape
            report_entities.append(
                {
                    "entity_id": entity_id,
                    "kind": kind,
                    "volume_mm3": float(shape.Volume),
                    "aabb": _aabb(shape),
                }
            )

        assembly = {
            "min_x_mm": min(item["aabb"]["min_x_mm"] for item in report_entities),
            "min_y_mm": min(item["aabb"]["min_y_mm"] for item in report_entities),
            "min_z_mm": min(item["aabb"]["min_z_mm"] for item in report_entities),
            "max_x_mm": max(item["aabb"]["max_x_mm"] for item in report_entities),
            "max_y_mm": max(item["aabb"]["max_y_mm"] for item in report_entities),
            "max_z_mm": max(item["aabb"]["max_z_mm"] for item in report_entities),
        }
        version_parts = [str(part) for part in App.Version()[:3]]
        report = {
            "backend": "FreeCAD",
            "backend_version": ".".join(version_parts),
            "design_sha256": design_sha256,
            "entities": report_entities,
            "assembly_aabb": assembly,
            "total_primitive_volume_mm3": sum(
                item["volume_mm3"] for item in report_entities
            ),
        }
        report_path.write_text(
            json.dumps(
                report,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ),
            encoding="utf-8",
        )
    finally:
        App.closeDocument(document.Name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
