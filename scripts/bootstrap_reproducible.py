from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed with exit {completed.returncode}: {command!r}"
        )
    return completed.stdout


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def one_wheel(directory: Path) -> Path:
    wheels = sorted(directory.glob("engineering_ai-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(
            f"expected exactly one engineering-ai wheel in {directory}, got {wheels}"
        )
    return wheels[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create the Gate 026 canonical reproducible local installation."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--venv",
        type=Path,
        required=True,
        help="New virtual-environment path. Existing paths are refused.",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run the full deterministic unittest regression in the installed environment.",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    venv_dir = args.venv.resolve()

    if sys.version_info[:2] != (3, 12):
        raise RuntimeError(
            f"bootstrap interpreter must be Python 3.12.x, got {sys.version.split()[0]}"
        )
    if venv_dir.exists():
        raise RuntimeError(f"refusing existing virtual-environment path: {venv_dir}")

    status = run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo_root,
    ).strip()
    if status:
        raise RuntimeError(
            "canonical reproducible bootstrap requires a clean Git working tree"
        )

    commit = run(["git", "rev-parse", "HEAD"], cwd=repo_root).strip()
    if len(commit) != 40:
        raise RuntimeError(f"unexpected Git revision: {commit!r}")
    source_date_epoch = run(
        ["git", "show", "-s", "--format=%ct", "HEAD"],
        cwd=repo_root,
    ).strip()
    if not source_date_epoch.isdigit():
        raise RuntimeError("could not derive SOURCE_DATE_EPOCH from Git HEAD")

    print(f"Creating clean virtual environment: {venv_dir}")
    venv.EnvBuilder(with_pip=True, clear=False).create(venv_dir)
    python = venv_python(venv_dir)
    if not python.is_file():
        raise RuntimeError(f"virtual-environment Python not found: {python}")

    toolchain_lock = repo_root / "requirements" / "toolchain.lock"
    runtime_lock = repo_root / "requirements" / "runtime.lock"

    run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "--upgrade",
            "--only-binary=:all:",
            "-r",
            str(toolchain_lock),
        ],
        cwd=repo_root,
    )
    run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "--only-binary=:all:",
            "-r",
            str(runtime_lock),
        ],
        cwd=repo_root,
    )

    build_env = os.environ.copy()
    build_env["SOURCE_DATE_EPOCH"] = source_date_epoch
    build_env["PYTHONHASHSEED"] = "0"

    with tempfile.TemporaryDirectory(prefix="engineering-ai-gate026-wheel-a-") as a_tmp, tempfile.TemporaryDirectory(prefix="engineering-ai-gate026-wheel-b-") as b_tmp:
        wheel_a_dir = Path(a_tmp)
        wheel_b_dir = Path(b_tmp)
        base_command = [
            str(python),
            "-m",
            "pip",
            "wheel",
            "--disable-pip-version-check",
            "--no-input",
            "--no-deps",
            "--no-build-isolation",
        ]
        run(base_command + ["--wheel-dir", str(wheel_a_dir), "."], cwd=repo_root, env=build_env)
        run(base_command + ["--wheel-dir", str(wheel_b_dir), "."], cwd=repo_root, env=build_env)

        wheel_a = one_wheel(wheel_a_dir)
        wheel_b = one_wheel(wheel_b_dir)
        hash_a = sha256_file(wheel_a)
        hash_b = sha256_file(wheel_b)
        if wheel_a.name != wheel_b.name:
            raise RuntimeError(
                f"repeated wheel filenames differ: {wheel_a.name} vs {wheel_b.name}"
            )
        if hash_a != hash_b:
            raise RuntimeError(
                f"repeated wheel SHA-256 differs: {hash_a} vs {hash_b}"
            )

        run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "--no-deps",
                str(wheel_a),
            ],
            cwd=repo_root,
        )

    run([str(python), "-m", "pip", "check"], cwd=repo_root)
    run(
        [
            str(python),
            str(repo_root / "scripts" / "gate026_verify_install.py"),
            "--repo-root",
            str(repo_root),
            "--expected-wheel-sha256",
            hash_a,
        ],
        cwd=repo_root,
    )

    if args.run_tests:
        run(
            [
                str(python),
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-v",
            ],
            cwd=repo_root,
        )

    payload = {
        "gate": "026",
        "state": "PASS_REPRODUCIBLE_LOCAL_INSTALL",
        "repository_head": commit,
        "python": sys.version.split()[0],
        "venv": str(venv_dir),
        "wheel_filename": wheel_a.name,
        "wheel_sha256": hash_a,
        "wheel_repeat_sha256_match": True,
        "pip_check": "PASS",
        "deterministic_regression": "PASS" if args.run_tests else "NOT_RUN",
        "offline_dependency_acquisition": "NOT_CLAIMED_GATE_026",
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
