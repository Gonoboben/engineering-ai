from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


class Gate008QualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        script_path = (
            Path(__file__).resolve().parents[1]
            / "scripts"
            / "gate008_model_qualification.py"
        )
        spec = importlib.util.spec_from_file_location(
            "gate008_model_qualification", script_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("could not load Gate 008 qualification script")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.module = module

    def test_general_suite_is_fixed_and_bounded(self) -> None:
        cases = self.module.build_general_cases(
            "candidate",
            context_tokens=8192,
            max_output_tokens=2048,
            reasoning_effort=None,
        )
        self.assertEqual(
            [case.case_id for case in cases],
            [
                "general-structured-math",
                "general-planner-contract",
                "general-validation-semantics",
                "general-tool-proposal",
            ],
        )
        self.assertTrue(all(case.request.context_tokens == 8192 for case in cases))
        self.assertTrue(
            all(case.request.max_output_tokens == 2048 for case in cases)
        )

    def test_code_suite_is_fixed_and_bounded(self) -> None:
        cases = self.module.build_code_cases(
            "candidate",
            context_tokens=8192,
            max_output_tokens=2048,
            reasoning_effort=None,
        )
        self.assertEqual(
            [case.case_id for case in cases],
            [
                "code-clamp-repair",
                "code-off-by-one-repair",
                "code-review-evidence",
                "code-tool-proposal",
            ],
        )
        self.assertTrue(all(case.request.context_tokens == 8192 for case in cases))

    def test_gate008_prompts_exclude_electronics_pcb_specialization(self) -> None:
        cases = (
            self.module.build_general_cases("candidate", 8192, 2048, None)
            + self.module.build_code_cases("candidate", 8192, 2048, None)
        )
        visible = []
        for case in cases:
            visible.append(case.description)
            visible.extend(message.content for message in case.request.messages)
        text = "\n".join(visible).lower()
        for forbidden in ("kicad", "pcb", "erc", "drc", "spice", "schematic"):
            self.assertNotIn(forbidden, text)

    def test_exit_code_semantics_match_existing_benchmark_contract(self) -> None:
        self.assertEqual(
            self.module._exit_code({"failed": 0, "unscored": 0}), 0
        )
        self.assertEqual(
            self.module._exit_code({"failed": 1, "unscored": 0}), 2
        )
        self.assertEqual(
            self.module._exit_code({"failed": 0, "unscored": 1}), 3
        )


if __name__ == "__main__":
    unittest.main()
