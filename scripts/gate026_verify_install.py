from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import sys


EXPECTED_PROJECT_VERSION = "0.1.0"


def parse_lock(path: Path) -> dict[str, str]:
    expected: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.count("==") != 1:
            raise RuntimeError(f"non-exact lock entry: {line}")
        name, version = (part.strip() for part in line.split("==", 1))
        if not name or not version:
            raise RuntimeError(f"invalid lock entry: {line}")
        key = name.lower().replace("_", "-")
        if key in expected:
            raise RuntimeError(f"duplicate lock entry: {name}")
        expected[key] = version
    if not expected:
        raise RuntimeError(f"lock file is empty: {path}")
    return expected


def installed_version(name: str) -> str:
    return importlib.metadata.version(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--expected-wheel-sha256", required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    runtime_lock = parse_lock(repo_root / "requirements" / "runtime.lock")
    toolchain_lock = parse_lock(repo_root / "requirements" / "toolchain.lock")

    if sys.version_info[:2] != (3, 12):
        raise RuntimeError(
            f"Gate 026 requires Python 3.12.x, got {platform.python_version()}"
        )

    mismatches: list[str] = []
    observed: dict[str, str] = {}

    for name, expected in {**toolchain_lock, **runtime_lock}.items():
        actual = installed_version(name)
        observed[name] = actual
        if actual != expected:
            mismatches.append(f"{name}: expected {expected}, got {actual}")

    project_version = installed_version("engineering-ai")
    if project_version != EXPECTED_PROJECT_VERSION:
        mismatches.append(
            "engineering-ai: "
            f"expected {EXPECTED_PROJECT_VERSION}, got {project_version}"
        )

    import engineering_ai

    package_file = Path(engineering_ai.__file__).resolve()
    source_tree = (repo_root / "src").resolve()
    try:
        package_file.relative_to(source_tree)
    except ValueError:
        imported_from_source_tree = False
    else:
        imported_from_source_tree = True

    if imported_from_source_tree:
        mismatches.append(
            f"engineering_ai imported from source tree instead of installed wheel: {package_file}"
        )

    if len(args.expected_wheel_sha256) != 64 or any(
        ch not in "0123456789abcdef" for ch in args.expected_wheel_sha256.lower()
    ):
        mismatches.append("expected wheel SHA-256 is not a 64-character hex digest")

    payload = {
        "gate": "026",
        "state": "PASS_REPRODUCIBLE_INSTALLED_ENVIRONMENT" if not mismatches else "FAIL",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "engineering_ai": project_version,
        "package_file": str(package_file),
        "imported_from_source_tree": imported_from_source_tree,
        "expected_wheel_sha256": args.expected_wheel_sha256.lower(),
        "observed_versions": dict(sorted(observed.items())),
        "mismatches": mismatches,
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))

    if mismatches:
        raise RuntimeError("Gate 026 installed environment verification failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
