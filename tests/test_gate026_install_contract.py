from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def exact_lock(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.count("==") != 1:
            raise AssertionError(f"non-exact lock entry: {line}")
        name, version = line.split("==", 1)
        values[name] = version
    return values


class Gate026InstallContractTests(unittest.TestCase):
    def test_pyproject_matches_gate026_python_and_direct_dependency_contract(self) -> None:
        with (ROOT / "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)

        self.assertEqual(project["project"]["requires-python"], ">=3.12,<3.13")
        self.assertEqual(project["project"]["dependencies"], ["jsonschema==4.26.0"])
        self.assertEqual(
            project["build-system"]["requires"],
            ["setuptools==84.0.0"],
        )

    def test_toolchain_lock_is_exact_measured_contract(self) -> None:
        self.assertEqual(
            exact_lock(ROOT / "requirements" / "toolchain.lock"),
            {
                "packaging": "26.3",
                "pip": "26.2.1",
                "setuptools": "84.0.0",
                "wheel": "0.48.0",
            },
        )

    def test_runtime_lock_is_exact_gate025_observed_closure(self) -> None:
        self.assertEqual(
            exact_lock(ROOT / "requirements" / "runtime.lock"),
            {
                "attrs": "26.1.0",
                "jsonschema": "4.26.0",
                "jsonschema-specifications": "2025.9.1",
                "referencing": "0.37.0",
                "rpds-py": "2026.6.3",
                "typing-extensions": "4.16.0",
            },
        )

    def test_install_document_does_not_claim_offline_continuation(self) -> None:
        text = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("does **not** claim offline dependency acquisition", text)
        self.assertIn("network/package-index access", text)
        self.assertIn("non-editably", text)


if __name__ == "__main__":
    unittest.main()
