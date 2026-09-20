from __future__ import annotations

import itertools
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from engineering_ai.supervisor import (
    CapabilityBinding,
    CapabilityDefinition,
    CapabilityRegistry,
    CapabilityResult,
    CapabilitySideEffect,
    ControlledToolBridge,
    ControlledToolBridgeIntegrityError,
    ControlledToolBridgePolicyError,
    ToolBridgeStatus,
    ToolInvocationEventType,
    ToolInvocationLedger,
    ToolInvocationRequest,
    Supervisor,
    filesystem_read_text_binding,
    git_status_binding,
)
from engineering_ai.tools.filesystem import ReadOnlyFilesystemAdapter
from engineering_ai.tools.git import GitReadOnlyAdapter
from engineering_ai.validation import validate_instance


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def load_fixture(name: str) -> dict:
    with (FIXTURES / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def make_policy() -> dict:
    return load_fixture("valid_policy.json")


def make_state() -> dict:
    state = load_fixture("valid_state.json")
    state["current_gate"] = "022"
    state["active_job_id"] = None
    state["repository_ref"] = {
        "branch": "gate-022-controlled-mcp-tool-exposure",
        "head_sha": "0123456789abcdef0123456789abcdef01234567",
    }
    state["pending_checks"] = []
    state["blockers"] = []
    state["next_admissible_action"] = None
    return state


class IdFactory:
    def __init__(self) -> None:
        self._counter = itertools.count(1)

    def __call__(self) -> str:
        return f"tevt-test-{next(self._counter):04d}"


class CountingHandler:
    def __init__(
        self,
        *,
        result: CapabilityResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or CapabilityResult(
            ok=True,
            payload={"value": "ok"},
            summary="fake capability completed",
        )
        self.error = error
        self.calls: list[tuple[dict, int]] = []

    def __call__(self, arguments, *, timeout_seconds: int) -> CapabilityResult:
        self.calls.append((dict(arguments), timeout_seconds))
        if self.error is not None:
            raise self.error
        return self.result


def fake_binding(
    capability_id: str,
    action: str,
    handler: CountingHandler,
    *,
    project_id: str = "engineering-ai",
    max_request_chars: int = 8192,
    max_response_chars: int = 65536,
) -> CapabilityBinding:
    return CapabilityBinding(
        definition=CapabilityDefinition(
            capability_id=capability_id,
            project_id=project_id,
            action=action,
            description=f"Test capability {capability_id}",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["value"],
                "properties": {"value": {"type": "string", "maxLength": 4096}},
            },
            output_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["value"],
                "properties": {"value": {"type": "string"}},
            },
            side_effect=CapabilitySideEffect.READ_ONLY,
            timeout_seconds=7,
            max_request_chars=max_request_chars,
            max_response_chars=max_response_chars,
        ),
        handler=handler,
    )


class ControlledToolBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "tool-invocations.sqlite3"
        self.ledger = ToolInvocationLedger(
            self.db,
            event_id_factory=IdFactory(),
        )
        self.supervisor = Supervisor(
            policy=make_policy(),
            state=make_state(),
        )

    def tearDown(self) -> None:
        try:
            self.ledger.close()
        except Exception:
            pass
        self.tmp.cleanup()

    def bridge(self, *bindings: CapabilityBinding) -> ControlledToolBridge:
        return ControlledToolBridge(
            supervisor=self.supervisor,
            registry=CapabilityRegistry(tuple(bindings)),
            ledger=self.ledger,
        )

    def request(
        self,
        invocation_id: str,
        capability_id: str,
        arguments: dict | None = None,
        *,
        project_id: str = "engineering-ai",
    ) -> ToolInvocationRequest:
        return ToolInvocationRequest(
            invocation_id=invocation_id,
            project_id=project_id,
            capability_id=capability_id,
            arguments=arguments or {"value": "input"},
        )

    def test_registry_listing_is_metadata_only_and_deeply_immutable(self) -> None:
        handler = CountingHandler()
        bridge = self.bridge(
            fake_binding("test.read", "read_repository", handler)
        )
        listed = bridge.list_capabilities()
        self.assertEqual(len(listed), 1)
        descriptor = listed[0]
        self.assertEqual(descriptor["capability_id"], "test.read")
        self.assertNotIn("handler", descriptor)
        self.assertNotIn("callable", descriptor)
        with self.assertRaises(TypeError):
            descriptor["action"] = "architecture_change"
        self.assertIsInstance(descriptor["input_schema"]["required"], tuple)

    def test_duplicate_capability_id_is_rejected(self) -> None:
        handler = CountingHandler()
        one = fake_binding("test.duplicate", "read_repository", handler)
        with self.assertRaises(ValueError):
            CapabilityRegistry((one, one))

    def test_gate022_rejects_non_read_only_capability_metadata(self) -> None:
        with self.assertRaises(ControlledToolBridgePolicyError):
            CapabilityDefinition(
                capability_id="test.write",
                project_id="engineering-ai",
                action="read_repository",
                description="must reject",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                side_effect="WRITE",  # type: ignore[arg-type]
            )

    def test_real_filesystem_read_capability_is_policy_gated_and_audited(self) -> None:
        project = self.root / "project"
        project.mkdir()
        secret_payload = "EXPLICIT-READ-RESULT-NOT-STORED-IN-AUDIT"
        (project / "note.txt").write_text(secret_payload, encoding="utf-8")
        binding = filesystem_read_text_binding(
            project_id="engineering-ai",
            adapter=ReadOnlyFilesystemAdapter(project),
            allowed_paths=("note.txt",),
        )
        bridge = self.bridge(binding)
        req = ToolInvocationRequest(
            invocation_id="invoke-read-file",
            project_id="engineering-ai",
            capability_id="filesystem.read_text",
            arguments={"path": "note.txt"},
        )

        outcome = bridge.invoke(
            req,
            approval_obtained=True,
            approver="human-owner",
        )

        self.assertEqual(outcome.status, ToolBridgeStatus.PASS)
        self.assertTrue(outcome.handler_called)
        self.assertIsNotNone(outcome.result)
        assert outcome.result is not None
        self.assertEqual(outcome.result.payload, {"text": secret_payload})

        history = self.ledger.history(
            project_id="engineering-ai",
            invocation_id=req.invocation_id,
        )
        self.assertEqual(
            tuple(item.event_type for item in history),
            (
                ToolInvocationEventType.REQUEST_RECORDED,
                ToolInvocationEventType.RESULT_ACCEPTED,
            ),
        )
        validate_instance(
            "controlled-tool-invocation-snapshot.schema.json",
            history[-1].as_dict(),
        )
        raw = self.db.read_bytes()
        self.assertNotIn(secret_payload.encode("utf-8"), raw)
        self.assertIsNotNone(history[-1].response_sha256)

    def test_filesystem_capability_rejects_non_allowlisted_path_before_adapter(self) -> None:
        project = self.root / "allowlist-project"
        project.mkdir()
        (project / "allowed.txt").write_text("allowed", encoding="utf-8")
        (project / "not-allowed.txt").write_text("sensitive", encoding="utf-8")
        binding = filesystem_read_text_binding(
            project_id="engineering-ai",
            adapter=ReadOnlyFilesystemAdapter(project),
            allowed_paths=("allowed.txt",),
        )
        bridge = self.bridge(binding)
        outcome = bridge.invoke(
            ToolInvocationRequest(
                invocation_id="invoke-non-allowlisted-path",
                project_id="engineering-ai",
                capability_id="filesystem.read_text",
                arguments={"path": "not-allowed.txt"},
            ),
            approval_obtained=True,
            approver="human-owner",
        )
        self.assertEqual(outcome.status, ToolBridgeStatus.BLOCKED)
        self.assertFalse(outcome.handler_called)
        latest = self.ledger.get(
            project_id="engineering-ai",
            invocation_id="invoke-non-allowlisted-path",
        )
        self.assertEqual(latest.failure_class, "INPUT_SCHEMA_REJECTED")

    def test_unregistered_capability_is_blocked_and_audited(self) -> None:
        handler = CountingHandler()
        bridge = self.bridge(
            fake_binding("test.registered", "read_repository", handler)
        )
        outcome = bridge.invoke(
            self.request("invoke-unregistered", "test.missing")
        )
        self.assertEqual(outcome.status, ToolBridgeStatus.BLOCKED)
        self.assertFalse(outcome.handler_called)
        self.assertEqual(handler.calls, [])
        latest = self.ledger.get(
            project_id="engineering-ai",
            invocation_id="invoke-unregistered",
        )
        self.assertEqual(latest.failure_class, "UNREGISTERED_CAPABILITY")
        self.assertIsNone(latest.action)

    def test_project_mismatch_is_blocked_before_handler(self) -> None:
        handler = CountingHandler()
        bridge = self.bridge(
            fake_binding("test.project", "read_repository", handler)
        )
        outcome = bridge.invoke(
            self.request(
                "invoke-project-mismatch",
                "test.project",
                project_id="buoycalc",
            )
        )
        self.assertEqual(outcome.status, ToolBridgeStatus.BLOCKED)
        self.assertFalse(outcome.handler_called)
        self.assertEqual(handler.calls, [])

    def test_external_disclosure_boundary_blocks_autonomous_read_without_approval(self) -> None:
        handler = CountingHandler()
        bridge = self.bridge(
            fake_binding("test.disclosure", "read_repository", handler)
        )
        outcome = bridge.invoke(
            self.request("invoke-disclosure-missing", "test.disclosure")
        )
        self.assertEqual(
            outcome.status,
            ToolBridgeStatus.NEEDS_HUMAN_APPROVAL,
        )
        self.assertFalse(outcome.handler_called)
        self.assertEqual(handler.calls, [])
        latest = self.ledger.get(
            project_id="engineering-ai",
            invocation_id="invoke-disclosure-missing",
        )
        self.assertEqual(
            latest.failure_class,
            "EXTERNAL_DISCLOSURE_NEEDS_HUMAN_APPROVAL",
        )
        self.assertIn("external_disclosure:NEEDS_HUMAN_APPROVAL", latest.policy_decision)
        self.assertIn("read_repository:ALLOW", latest.policy_decision)

    def test_approval_required_capability_needs_named_approval(self) -> None:
        no_approval_handler = CountingHandler()
        bridge = self.bridge(
            fake_binding(
                "test.architecture-review",
                "architecture_change",
                no_approval_handler,
            )
        )
        outcome = bridge.invoke(
            self.request(
                "invoke-approval-missing",
                "test.architecture-review",
            )
        )
        self.assertEqual(
            outcome.status,
            ToolBridgeStatus.NEEDS_HUMAN_APPROVAL,
        )
        self.assertFalse(outcome.handler_called)
        self.assertEqual(no_approval_handler.calls, [])

        named_handler = CountingHandler()
        named_bridge = self.bridge(
            fake_binding(
                "test.architecture-approved",
                "architecture_change",
                named_handler,
            )
        )
        approved = named_bridge.invoke(
            self.request(
                "invoke-approval-named",
                "test.architecture-approved",
            ),
            approval_obtained=True,
            approver="human-owner",
        )
        self.assertEqual(approved.status, ToolBridgeStatus.PASS)
        self.assertEqual(len(named_handler.calls), 1)

    def test_asserted_approval_without_identity_calls_no_handler(self) -> None:
        handler = CountingHandler()
        bridge = self.bridge(
            fake_binding(
                "test.approver-identity",
                "architecture_change",
                handler,
            )
        )
        outcome = bridge.invoke(
            self.request(
                "invoke-approval-no-name",
                "test.approver-identity",
            ),
            approval_obtained=True,
        )
        self.assertEqual(
            outcome.status,
            ToolBridgeStatus.NEEDS_HUMAN_APPROVAL,
        )
        self.assertEqual(handler.calls, [])

    def test_forbidden_action_never_calls_handler(self) -> None:
        handler = CountingHandler()
        bridge = self.bridge(
            fake_binding(
                "test.forbidden",
                "validator_weakening",
                handler,
            )
        )
        outcome = bridge.invoke(
            self.request("invoke-forbidden", "test.forbidden"),
            approval_obtained=True,
            approver="human-owner",
        )
        self.assertEqual(outcome.status, ToolBridgeStatus.BLOCKED)
        self.assertFalse(outcome.handler_called)
        self.assertEqual(handler.calls, [])

    def test_input_schema_rejection_calls_no_handler(self) -> None:
        handler = CountingHandler()
        bridge = self.bridge(
            fake_binding("test.schema", "read_repository", handler)
        )
        outcome = bridge.invoke(
            self.request(
                "invoke-invalid-input",
                "test.schema",
                arguments={"unexpected": "value"},
            )
        )
        self.assertEqual(outcome.status, ToolBridgeStatus.BLOCKED)
        self.assertEqual(handler.calls, [])
        latest = self.ledger.get(
            project_id="engineering-ai",
            invocation_id="invoke-invalid-input",
        )
        self.assertEqual(latest.failure_class, "INPUT_SCHEMA_REJECTED")

    def test_capability_request_budget_rejection_calls_no_handler(self) -> None:
        handler = CountingHandler()
        bridge = self.bridge(
            fake_binding(
                "test.budget",
                "read_repository",
                handler,
                max_request_chars=16,
            )
        )
        outcome = bridge.invoke(
            self.request(
                "invoke-budget",
                "test.budget",
                arguments={"value": "0123456789abcdef"},
            )
        )
        self.assertEqual(outcome.status, ToolBridgeStatus.BLOCKED)
        self.assertEqual(handler.calls, [])
        latest = self.ledger.get(
            project_id="engineering-ai",
            invocation_id="invoke-budget",
        )
        self.assertEqual(latest.failure_class, "REQUEST_BUDGET_EXCEEDED")

    def test_handler_exception_fails_closed_and_error_text_not_persisted(self) -> None:
        leaked = "HANDLER-ERROR-ECHO-DO-NOT-PERSIST"
        handler = CountingHandler(error=RuntimeError(leaked))
        bridge = self.bridge(
            fake_binding("test.exception", "read_repository", handler)
        )
        outcome = bridge.invoke(
            self.request("invoke-handler-error", "test.exception"),
            approval_obtained=True,
            approver="human-owner",
        )
        self.assertEqual(outcome.status, ToolBridgeStatus.FAIL)
        self.assertTrue(outcome.handler_called)
        self.assertNotIn(leaked, outcome.summary)
        self.assertNotIn(leaked.encode("utf-8"), self.db.read_bytes())

    def test_timed_out_result_fails_closed(self) -> None:
        handler = CountingHandler(
            result=CapabilityResult(
                ok=False,
                payload={"value": "timeout"},
                summary="synthetic timeout",
                timed_out=True,
            )
        )
        bridge = self.bridge(
            fake_binding("test.timeout", "read_repository", handler)
        )
        outcome = bridge.invoke(
            self.request("invoke-timeout", "test.timeout"),
            approval_obtained=True,
            approver="human-owner",
        )
        self.assertEqual(outcome.status, ToolBridgeStatus.FAIL)
        latest = self.ledger.get(
            project_id="engineering-ai",
            invocation_id="invoke-timeout",
        )
        self.assertEqual(
            latest.failure_class,
            "ControlledToolBridgeProtocolError",
        )

    def test_output_schema_or_budget_failure_is_not_accepted(self) -> None:
        bad_schema_handler = CountingHandler(
            result=CapabilityResult(
                ok=True,
                payload={"wrong": "field"},
                summary="bad output",
            )
        )
        bridge = self.bridge(
            fake_binding(
                "test.bad-output",
                "read_repository",
                bad_schema_handler,
            )
        )
        bad = bridge.invoke(
            self.request("invoke-bad-output", "test.bad-output"),
            approval_obtained=True,
            approver="human-owner",
        )
        self.assertEqual(bad.status, ToolBridgeStatus.FAIL)

        large_handler = CountingHandler(
            result=CapabilityResult(
                ok=True,
                payload={"value": "x" * 100},
                summary="large output",
            )
        )
        large_bridge = self.bridge(
            fake_binding(
                "test.large-output",
                "read_repository",
                large_handler,
                max_response_chars=20,
            )
        )
        large = large_bridge.invoke(
            self.request("invoke-large-output", "test.large-output"),
            approval_obtained=True,
            approver="human-owner",
        )
        self.assertEqual(large.status, ToolBridgeStatus.FAIL)

    def test_duplicate_invocation_id_is_rejected(self) -> None:
        handler = CountingHandler()
        bridge = self.bridge(
            fake_binding("test.duplicate-call", "read_repository", handler)
        )
        req = self.request(
            "invoke-duplicate",
            "test.duplicate-call",
        )
        self.assertEqual(
            bridge.invoke(
                req,
                approval_obtained=True,
                approver="human-owner",
            ).status,
            ToolBridgeStatus.PASS,
        )
        with self.assertRaises(ControlledToolBridgePolicyError):
            bridge.invoke(
                req,
                approval_obtained=True,
                approver="human-owner",
            )

    def test_ledger_reopen_integrity_and_tamper_detection(self) -> None:
        handler = CountingHandler()
        bridge = self.bridge(
            fake_binding("test.integrity", "read_repository", handler)
        )
        self.assertEqual(
            bridge.invoke(
                self.request("invoke-integrity", "test.integrity"),
                approval_obtained=True,
                approver="human-owner",
            ).status,
            ToolBridgeStatus.PASS,
        )
        report = self.ledger.verify_integrity(project_id="engineering-ai")
        self.assertTrue(report.ok)
        self.assertEqual(report.events_checked, 2)
        self.assertEqual(report.invocations_checked, 1)
        self.ledger.close()

        self.ledger = ToolInvocationLedger(
            self.db,
            event_id_factory=IdFactory(),
        )
        reopened = self.ledger.verify_integrity(project_id="engineering-ai")
        self.assertTrue(reopened.ok)

        self.ledger.close()
        conn = sqlite3.connect(self.db)
        try:
            conn.execute("DROP TRIGGER controlled_tool_invocation_no_update")
            conn.execute(
                """
                UPDATE controlled_tool_invocation_events
                SET request_chars = request_chars + 1
                WHERE invocation_id = 'invoke-integrity'
                  AND event_type = 'REQUEST_RECORDED'
                """
            )
            conn.commit()
        finally:
            conn.close()

        self.ledger = ToolInvocationLedger(
            self.db,
            event_id_factory=IdFactory(),
        )
        with self.assertRaises(ControlledToolBridgeIntegrityError):
            self.ledger.history(
                project_id="engineering-ai",
                invocation_id="invoke-integrity",
            )

    def test_no_generic_execution_or_write_surface(self) -> None:
        handler = CountingHandler()
        bridge = self.bridge(
            fake_binding("test.surface", "read_repository", handler)
        )
        for name in (
            "run",
            "execute",
            "shell",
            "write_file",
            "delete_file",
            "git_push",
            "git_merge",
            "register_dynamic",
            "eval",
            "grant_approval",
        ):
            self.assertFalse(hasattr(bridge, name))

    def test_gate022_smoke_script(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/gate022_controlled_tool_smoke.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate"], "022")
        self.assertEqual(
            payload["state"],
            "PASS_CONTROLLED_MCP_TOOL_EXPOSURE",
        )
        self.assertEqual(
            payload["external_disclosure_missing_status"],
            "NEEDS_HUMAN_APPROVAL",
        )
        self.assertFalse(
            payload["external_disclosure_missing_handler_called"]
        )
        self.assertEqual(payload["read_only_capability_status"], "PASS")
        self.assertTrue(payload["read_only_result_exact"])
        self.assertEqual(payload["unregistered_status"], "BLOCKED")
        self.assertFalse(payload["unregistered_handler_called"])
        self.assertEqual(
            payload["approval_missing_status"],
            "NEEDS_HUMAN_APPROVAL",
        )
        self.assertFalse(payload["approval_missing_handler_called"])
        self.assertEqual(payload["approval_named_status"], "PASS")
        self.assertEqual(payload["approval_named_handler_call_count"], 1)
        self.assertEqual(payload["forbidden_status"], "BLOCKED")
        self.assertFalse(payload["forbidden_handler_called"])
        self.assertFalse(payload["request_or_result_payload_persisted"])
        self.assertTrue(payload["ledger_database_reopened"])
        self.assertTrue(payload["ledger_integrity"])
        self.assertFalse(payload["handler_objects_exposed_in_listing"])
        self.assertFalse(payload["generic_shell_surface"])
        self.assertFalse(payload["filesystem_write_surface"])
        self.assertFalse(payload["git_mutation_surface"])
        self.assertFalse(payload["dynamic_import_eval_surface"])
        self.assertFalse(payload["public_network_listener"])
        self.assertFalse(payload["automatic_approval"])
        self.assertEqual(
            payload["physical_validation"],
            "PHYSICAL_NOT_EXECUTED",
        )

    @unittest.skipIf(shutil.which("git") is None, "git executable is required")
    def test_real_git_status_binding_uses_existing_read_only_adapter(self) -> None:
        project = self.root / "git-project"
        project.mkdir()
        subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.invalid"],
            cwd=project,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Engineering AI Test"],
            cwd=project,
            check=True,
        )
        (project / "a.txt").write_text("one\n", encoding="utf-8")
        subprocess.run(["git", "add", "a.txt"], cwd=project, check=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=project,
            check=True,
            capture_output=True,
        )
        binding = git_status_binding(
            project_id="engineering-ai",
            adapter=GitReadOnlyAdapter(project),
        )
        bridge = self.bridge(binding)
        req = ToolInvocationRequest(
            invocation_id="invoke-git-status",
            project_id="engineering-ai",
            capability_id="git.status",
            arguments={},
        )
        outcome = bridge.invoke(
            req,
            approval_obtained=True,
            approver="human-owner",
        )
        self.assertEqual(outcome.status, ToolBridgeStatus.PASS)
        assert outcome.result is not None
        self.assertEqual(outcome.result.payload["operation"], "git.status")


if __name__ == "__main__":
    unittest.main()
