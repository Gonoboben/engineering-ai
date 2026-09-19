from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from engineering_ai.projects.platavm import (
    CIState,
    REQUIRED_GOVERNANCE_FILES,
    PlataVMReadOnlyAdapter,
    ValidatorState,
    classify_ci_conclusion,
)
from engineering_ai.tools import ToolExecutionError


@unittest.skipIf(shutil.which("git") is None, "git executable is required")
class PlataVMReadOnlyAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.origin_tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.origin = Path(self.origin_tmp.name) / "origin.git"

        subprocess.run(
            ["git", "init", "--bare", str(self.origin)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.invalid"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Engineering AI Test"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "remote", "add", "origin", str(self.origin)],
            cwd=self.root,
            check=True,
        )

        docs = {
            "AGENTS.md": "# PlataVM test rules\n",
            "Docs/PROJECT_STATUS.md": (
                "# status\n\n"
                "| Поле | Значение |\n"
                "|---|---|\n"
                "| Подтверждённый base `main` | `0000000000000000000000000000000000000000` |\n"
                "| Активная ветка | `agent/stale` |\n"
            ),
            "Docs/PROJECT_CONTROL.md": "# control\n",
            "Docs/PROJECT_MASTER.md": "# master\n",
            "Docs/ARCHITECTURE_BASELINE.md": "# V1.9\n",
            "Docs/OPEN_QUESTIONS.md": "# open questions\n",
            "Docs/TRACEABILITY_V1_9.md": "# traceability\n",
            "Docs/CHRONOLOGY.md": "# chronology\n",
            "Docs/chronology/2026-09-18.md": "older\n",
            "Docs/chronology/2026-09-19.md": "latest\n",
            "Hardware/KiCad/PlataVM.kicad_pro": "(project)\n",
            "Hardware/KiCad/PlataVM.kicad_sch": "(schematic)\n",
            "Hardware/KiCad/Footprints.pretty/Test.kicad_mod": "(module)\n",
            "Tools/repository_integrity.py": (
                "import sys\n"
                "print('repository-integrity-pass', ' '.join(sys.argv[1:]))\n"
            ),
            "Tools/run_all_gates.py": "print('semantic-gates-pass')\n",
        }
        for relative, content in docs.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "fixture"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "switch", "-c", "agent/current"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()
        self.origin_tmp.cleanup()

    def adapter(self, **kwargs) -> PlataVMReadOnlyAdapter:
        return PlataVMReadOnlyAdapter(
            self.root,
            python_executable=sys.executable,
            **kwargs,
        )

    def test_resolves_governance_in_required_order_and_latest_chronology(self) -> None:
        adapter = self.adapter()
        snapshot = adapter.snapshot()
        self.assertEqual(
            tuple(doc.path for doc in snapshot.governance_documents),
            REQUIRED_GOVERNANCE_FILES,
        )
        self.assertEqual(
            snapshot.latest_chronology.path,
            "Docs/chronology/2026-09-19.md",
        )
        self.assertIn("Hardware/KiCad/PlataVM.kicad_pro", snapshot.kicad_assets)
        self.assertIn("Hardware/KiCad/PlataVM.kicad_sch", snapshot.kicad_assets)
        self.assertIn(
            "Hardware/KiCad/Footprints.pretty/Test.kicad_mod",
            snapshot.kicad_assets,
        )

    def test_missing_mandatory_governance_file_is_hard_error(self) -> None:
        (self.root / "Docs/OPEN_QUESTIONS.md").unlink()
        with self.assertRaises(ToolExecutionError):
            self.adapter().governance_documents()

    def test_stale_project_status_is_surfaced_as_conflict(self) -> None:
        snapshot = self.adapter().snapshot()
        self.assertEqual(snapshot.git.branch, "agent/current")
        self.assertTrue(snapshot.git.origin_main_sha)
        self.assertGreaterEqual(len(snapshot.conflicts), 2)
        self.assertTrue(
            any("origin/main" in conflict for conflict in snapshot.conflicts)
        )
        self.assertTrue(
            any("checked-out branch" in conflict for conflict in snapshot.conflicts)
        )

    def test_cancelled_ci_is_preserved_as_non_pass_state(self) -> None:
        self.assertEqual(
            classify_ci_conclusion("cancelled", status="completed"),
            CIState.CANCELLED,
        )
        self.assertNotEqual(
            classify_ci_conclusion("cancelled", status="completed"),
            CIState.PASS,
        )
        self.assertEqual(
            classify_ci_conclusion("success", status="completed"),
            CIState.PASS,
        )
        self.assertEqual(
            classify_ci_conclusion("failure", status="completed"),
            CIState.FAIL,
        )
        self.assertEqual(
            classify_ci_conclusion(None, status="in_progress"),
            CIState.IN_PROGRESS,
        )

    def test_only_fixed_validator_profiles_are_exposed(self) -> None:
        adapter = self.adapter()
        self.assertEqual(
            adapter.validator_profiles,
            (
                "platavm.repository_integrity",
                "platavm.semantic_gates",
            ),
        )
        repo = adapter.run_validator("platavm.repository_integrity")
        gates = adapter.run_validator("platavm.semantic_gates")
        self.assertEqual(repo.state, ValidatorState.PASS)
        self.assertEqual(gates.state, ValidatorState.PASS)
        self.assertIn("--base-ref origin/main", repo.result.stdout)
        self.assertIn("semantic-gates-pass", gates.result.stdout)

    def test_validator_git_visible_mutation_is_rejected(self) -> None:
        script = self.root / "Tools/run_all_gates.py"
        script.write_text(
            "from pathlib import Path\n"
            "Path('unexpected.txt').write_text('mutation', encoding='utf-8')\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "Tools/run_all_gates.py"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "mutating validator fixture"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )

        with self.assertRaises(ToolExecutionError):
            self.adapter().run_validator("platavm.semantic_gates")

    def test_adapter_exposes_no_write_delete_or_git_mutation_api(self) -> None:
        adapter = self.adapter()
        forbidden = {
            "write",
            "write_text",
            "delete",
            "remove",
            "commit",
            "push",
            "merge",
            "checkout",
            "create_branch",
            "open_pr",
            "execute",
            "run",
        }
        self.assertTrue(all(not hasattr(adapter, name) for name in forbidden))

    def test_kicad_inventory_scan_is_bounded(self) -> None:
        with self.assertRaises(ToolExecutionError):
            self.adapter(max_scan_entries=1).kicad_assets()


if __name__ == "__main__":
    unittest.main()
