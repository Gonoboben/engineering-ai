from __future__ import annotations

import unittest

from engineering_ai.models import (
    DeterministicModelRouter,
    ModelCapability,
    ModelCapabilityRegistry,
    ModelTaskClass,
    RouteRequest,
    RouteStatus,
    accepted_registry,
)
from engineering_ai.supervisor import Supervisor


class ModelRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = accepted_registry()
        self.router = DeterministicModelRouter(self.registry)

    def test_accepted_registry_contains_only_evidence_backed_models(self) -> None:
        self.assertEqual(
            [(entry.provider, entry.model) for entry in self.registry.entries],
            [
                ("ollama", "qwen3.5:9b"),
                ("ollama", "qwen2.5-coder:7b-instruct"),
                ("ollama", "gpt-oss:20b"),
            ],
        )
        self.assertTrue(
            all(entry.evidence_refs for entry in self.registry.entries)
        )

    def test_general_planning_routes_to_qwen35(self) -> None:
        decision = self.router.route(
            RouteRequest(task_class=ModelTaskClass.GENERAL_PLANNING)
        )
        self.assertEqual(decision.status, RouteStatus.ROUTE)
        self.assertEqual(decision.model, "qwen3.5:9b")
        self.assertEqual(decision.provider, "ollama")
        self.assertEqual(decision.reasoning_effort, "none")

    def test_code_repository_routes_to_coder_with_supplied_context(self) -> None:
        decision = self.router.route(
            RouteRequest(task_class=ModelTaskClass.CODE_REPOSITORY)
        )
        self.assertEqual(decision.status, RouteStatus.ROUTE)
        self.assertEqual(decision.model, "qwen2.5-coder:7b-instruct")

    def test_coder_native_tool_requirement_is_hard_no_route(self) -> None:
        decision = self.router.route(
            RouteRequest(
                task_class=ModelTaskClass.CODE_REPOSITORY,
                requires_native_tool_proposals=True,
            )
        )
        self.assertEqual(decision.status, RouteStatus.NO_ROUTE)
        self.assertIsNone(decision.model)
        self.assertEqual(
            decision.considered_models, ("qwen2.5-coder:7b-instruct",)
        )
        self.assertIn("native tool proposals not qualified", decision.reason)

    def test_baseline_reasoning_routes_to_gpt_oss_without_new_specialist_claim(self) -> None:
        decision = self.router.route(
            RouteRequest(task_class=ModelTaskClass.BASELINE_REASONING)
        )
        self.assertEqual(decision.status, RouteStatus.ROUTE)
        self.assertEqual(decision.model, "gpt-oss:20b")
        self.assertEqual(decision.reasoning_effort, "medium")
        self.assertIn("ACCEPTED_BASELINE_RUNTIME_VALIDATED", decision.reason)

    def test_context_above_measured_gate_limit_is_no_route(self) -> None:
        decision = self.router.route(
            RouteRequest(
                task_class=ModelTaskClass.GENERAL_PLANNING,
                context_tokens=8193,
            )
        )
        self.assertEqual(decision.status, RouteStatus.NO_ROUTE)
        self.assertIn("context exceeds qualified limit 8192", decision.reason)

    def test_output_above_measured_gate_limit_is_no_route(self) -> None:
        decision = self.router.route(
            RouteRequest(
                task_class=ModelTaskClass.CODE_REPOSITORY,
                max_output_tokens=2049,
            )
        )
        self.assertEqual(decision.status, RouteStatus.NO_ROUTE)
        self.assertIn("output exceeds qualified limit 2048", decision.reason)

    def test_task_class_must_be_explicit_enum(self) -> None:
        with self.assertRaises(ValueError):
            RouteRequest(task_class="ELECTRONICS")  # type: ignore[arg-type]

    def test_no_electronics_or_kicad_task_class_exists(self) -> None:
        names = {item.value for item in ModelTaskClass}
        self.assertNotIn("ELECTRONICS", names)
        self.assertNotIn("PCB", names)
        self.assertNotIn("KICAD", names)
        self.assertNotIn("VISION", names)

    def test_registry_rejects_duplicate_model_identity(self) -> None:
        entry = self.registry.entries[0]
        with self.assertRaises(ValueError):
            ModelCapabilityRegistry((entry, entry))

    def test_tie_breaking_is_deterministic_priority_then_model_name(self) -> None:
        first = ModelCapability(
            model="z-model",
            provider="fake",
            task_classes=(ModelTaskClass.GENERAL_PLANNING,),
            qualification="QUALIFIED",
            max_qualified_context_tokens=8192,
            max_qualified_output_tokens=2048,
            reasoning_effort=None,
            supports_native_tool_proposals=False,
            evidence_refs=("ev-z",),
            priority=20,
        )
        second = ModelCapability(
            model="a-model",
            provider="fake",
            task_classes=(ModelTaskClass.GENERAL_PLANNING,),
            qualification="QUALIFIED",
            max_qualified_context_tokens=8192,
            max_qualified_output_tokens=2048,
            reasoning_effort=None,
            supports_native_tool_proposals=False,
            evidence_refs=("ev-a",),
            priority=10,
        )
        router = DeterministicModelRouter(ModelCapabilityRegistry((first, second)))
        decision = router.route(
            RouteRequest(task_class=ModelTaskClass.GENERAL_PLANNING)
        )
        self.assertEqual(decision.model, "a-model")

    def test_router_object_has_no_provider_or_tool_execution_dependency(self) -> None:
        self.assertEqual(set(vars(self.router)), {"_registry"})

    def test_supervisor_owns_routing_boundary_without_executing_anything(self) -> None:
        policy = {
            "schema_version": "1.0",
            "policy_version": "1.0",
            "project_id": "engineering-ai",
            "autonomous_actions": ["read_repository"],
            "approval_required_actions": [
                "architecture_change",
                "physics_change",
                "destructive_action",
                "fabrication_authorization",
                "release_authorization",
                "external_disclosure",
                "scope_expansion",
            ],
            "forbidden_actions": ["validator_weakening"],
            "mandatory_validators": [],
            "stop_conditions": ["approval boundary reached"],
            "retry_limit": 1,
        }
        state = {
            "schema_version": "1.0",
            "state_revision": 1,
            "project_id": "engineering-ai",
            "current_gate": "009",
            "active_job_id": None,
            "repository_ref": {
                "branch": "gate-009-model-capability-registry-router",
                "head_sha": "test",
            },
            "architecture_baseline": "Gate 007",
            "effective_permissions": {
                "autonomous": ["read_repository"],
                "approval_required": [
                    "architecture_change",
                    "physics_change",
                    "destructive_action",
                    "fabrication_authorization",
                    "release_authorization",
                    "external_disclosure",
                    "scope_expansion",
                ],
                "forbidden": ["validator_weakening"],
            },
            "pending_checks": [],
            "blockers": [],
            "validation_states": [
                {
                    "check_id": "physical-validation",
                    "validation_class": "PHYSICAL",
                    "state": "PHYSICAL_NOT_EXECUTED",
                    "evidence_refs": [],
                }
            ],
            "next_admissible_action": None,
        }
        supervisor = Supervisor(
            policy=policy,
            state=state,
            model_router=self.router,
        )
        decision = supervisor.route_model(
            RouteRequest(task_class=ModelTaskClass.GENERAL_PLANNING)
        )
        self.assertEqual(decision.status, RouteStatus.ROUTE)
        self.assertEqual(decision.model, "qwen3.5:9b")
        self.assertEqual(supervisor.audit_events, ())


if __name__ == "__main__":
    unittest.main()
