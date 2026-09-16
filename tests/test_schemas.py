from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import ValidationError

import engineering_ai
from engineering_ai.validation import (
    SemanticValidationError,
    check_all_schemas,
    validate_instance,
)


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(name: str) -> dict:
    with (FIXTURE_DIR / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class SchemaValidationTests(unittest.TestCase):
    def test_package_import_smoke(self) -> None:
        self.assertEqual(engineering_ai.__version__, "0.1.0")

    def test_all_schema_documents_are_valid_draft_2020_12(self) -> None:
        check_all_schemas()

    def test_positive_fixtures(self) -> None:
        fixtures = {
            "project-profile.schema.json": "valid_project_profile.json",
            "project-policy.schema.json": "valid_policy.json",
            "job.schema.json": "valid_job.json",
            "project-state.schema.json": "valid_state.json",
            "evidence.schema.json": "valid_evidence.json",
            "audit-event.schema.json": "valid_audit.json",
        }
        for schema_name, fixture_name in fixtures.items():
            with self.subTest(schema=schema_name, fixture=fixture_name):
                validate_instance(schema_name, load_fixture(fixture_name))

    def test_policy_cannot_make_architecture_change_autonomous(self) -> None:
        with self.assertRaises(SemanticValidationError):
            validate_instance(
                "project-policy.schema.json",
                load_fixture("invalid_policy_autonomous_architecture.json"),
            )

    def test_state_cannot_make_physics_change_autonomous(self) -> None:
        with self.assertRaises(SemanticValidationError):
            validate_instance(
                "project-state.schema.json",
                load_fixture("invalid_state_autonomous_physics.json"),
            )

    def test_simulation_cannot_claim_physical_pass(self) -> None:
        with self.assertRaises(ValidationError):
            validate_instance(
                "evidence.schema.json",
                load_fixture("invalid_evidence_simulation_physical_pass.json"),
            )

    def test_audit_record_cannot_declare_secrets_present(self) -> None:
        with self.assertRaises(ValidationError):
            validate_instance(
                "audit-event.schema.json",
                load_fixture("invalid_audit_contains_secrets.json"),
            )

    def test_job_attempts_cannot_exceed_retry_limit(self) -> None:
        with self.assertRaises(SemanticValidationError):
            validate_instance(
                "job.schema.json",
                load_fixture("invalid_job_retry_exceeded.json"),
            )


if __name__ == "__main__":
    unittest.main()
