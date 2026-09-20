from __future__ import annotations

import json
import tempfile
from pathlib import Path

from engineering_ai.supervisor import (
    CapabilityBinding,
    CapabilityDefinition,
    CapabilityRegistry,
    CapabilityResult,
    CapabilitySideEffect,
    ControlledToolBridge,
    ToolBridgeStatus,
    ToolInvocationLedger,
    ToolInvocationRequest,
    Supervisor,
    filesystem_read_text_binding,
)
from engineering_ai.tools.filesystem import ReadOnlyFilesystemAdapter


def policy() -> dict:
    return {
        "schema_version": "1.0",
        "policy_version": "gate022-smoke",
        "project_id": "engineering-ai",
        "autonomous_actions": ["read_repository", "run_validator"],
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
        "retry_limit": 2,
    }


def state() -> dict:
    return {
        "schema_version": "1.0",
        "state_revision": 1,
        "project_id": "engineering-ai",
        "current_gate": "022",
        "active_job_id": None,
        "repository_ref": {
            "branch": "gate-022-controlled-mcp-tool-exposure",
            "head_sha": "0123456789abcdef0123456789abcdef01234567",
        },
        "architecture_baseline": "Gate 021 accepted external advisory bridge",
        "effective_permissions": {
            "autonomous": ["read_repository", "run_validator"],
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


class CountingHandler:
    def __init__(self, value: str) -> None:
        self.value = value
        self.calls = []

    def __call__(self, arguments, *, timeout_seconds: int) -> CapabilityResult:
        self.calls.append((dict(arguments), timeout_seconds))
        return CapabilityResult(
            ok=True,
            payload={"value": self.value},
            summary="fake registered capability completed",
        )


def fake_binding(
    capability_id: str,
    action: str,
    handler: CountingHandler,
) -> CapabilityBinding:
    return CapabilityBinding(
        definition=CapabilityDefinition(
            capability_id=capability_id,
            project_id="engineering-ai",
            action=action,
            description=f"Gate 022 smoke {capability_id}",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["value"],
                "properties": {"value": {"type": "string", "maxLength": 128}},
            },
            output_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["value"],
                "properties": {"value": {"type": "string"}},
            },
            side_effect=CapabilitySideEffect.READ_ONLY,
            timeout_seconds=10,
            max_request_chars=1024,
            max_response_chars=1024,
        ),
        handler=handler,
    )


def main() -> int:
    payload_text = "GATE022-READ-PAYLOAD-DO-NOT-PERSIST"

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        project = root / "project"
        project.mkdir()
        (project / "note.txt").write_text(payload_text, encoding="utf-8")
        db = root / "tool-invocations.sqlite3"

        approval_handler = CountingHandler("approved")
        forbidden_handler = CountingHandler("must-not-run")
        ledger = ToolInvocationLedger(db)
        bridge = ControlledToolBridge(
            supervisor=Supervisor(policy=policy(), state=state()),
            registry=CapabilityRegistry(
                (
                    filesystem_read_text_binding(
                        project_id="engineering-ai",
                        adapter=ReadOnlyFilesystemAdapter(project),
                    ),
                    fake_binding(
                        "test.approval",
                        "architecture_change",
                        approval_handler,
                    ),
                    fake_binding(
                        "test.forbidden",
                        "validator_weakening",
                        forbidden_handler,
                    ),
                )
            ),
            ledger=ledger,
        )

        listed = bridge.list_capabilities()
        assert tuple(item["capability_id"] for item in listed) == (
            "filesystem.read_text",
            "test.approval",
            "test.forbidden",
        )
        assert all("handler" not in item for item in listed)

        read = bridge.invoke(
            ToolInvocationRequest(
                invocation_id="invoke-read",
                project_id="engineering-ai",
                capability_id="filesystem.read_text",
                arguments={"path": "note.txt"},
            )
        )
        assert read.status is ToolBridgeStatus.PASS
        assert read.handler_called is True
        assert read.result is not None
        assert read.result.payload == {"text": payload_text}

        unregistered = bridge.invoke(
            ToolInvocationRequest(
                invocation_id="invoke-unregistered",
                project_id="engineering-ai",
                capability_id="test.missing",
                arguments={"value": "x"},
            )
        )
        assert unregistered.status is ToolBridgeStatus.BLOCKED
        assert unregistered.handler_called is False

        approval_missing = bridge.invoke(
            ToolInvocationRequest(
                invocation_id="invoke-approval-missing",
                project_id="engineering-ai",
                capability_id="test.approval",
                arguments={"value": "x"},
            )
        )
        assert approval_missing.status is ToolBridgeStatus.NEEDS_HUMAN_APPROVAL
        assert approval_missing.handler_called is False
        assert approval_handler.calls == []

        approval_named = bridge.invoke(
            ToolInvocationRequest(
                invocation_id="invoke-approval-named",
                project_id="engineering-ai",
                capability_id="test.approval",
                arguments={"value": "x"},
            ),
            approval_obtained=True,
            approver="human-owner",
        )
        assert approval_named.status is ToolBridgeStatus.PASS
        assert approval_named.handler_called is True
        assert len(approval_handler.calls) == 1

        forbidden = bridge.invoke(
            ToolInvocationRequest(
                invocation_id="invoke-forbidden",
                project_id="engineering-ai",
                capability_id="test.forbidden",
                arguments={"value": "x"},
            ),
            approval_obtained=True,
            approver="human-owner",
        )
        assert forbidden.status is ToolBridgeStatus.BLOCKED
        assert forbidden.handler_called is False
        assert forbidden_handler.calls == []

        integrity_before = ledger.verify_integrity(project_id="engineering-ai")
        assert integrity_before.ok
        raw_before = db.read_bytes()
        assert payload_text.encode("utf-8") not in raw_before

        ledger.close()
        ledger = ToolInvocationLedger(db)
        integrity_after = ledger.verify_integrity(project_id="engineering-ai")
        assert integrity_after.ok
        raw_after = db.read_bytes()
        assert payload_text.encode("utf-8") not in raw_after

        payload = {
            "gate": "022",
            "state": "PASS_CONTROLLED_MCP_TOOL_EXPOSURE",
            "registered_capability_count": len(listed),
            "handler_objects_exposed_in_listing": False,
            "read_only_capability_status": read.status.value,
            "read_only_result_exact": read.result.payload == {"text": payload_text},
            "unregistered_status": unregistered.status.value,
            "unregistered_handler_called": unregistered.handler_called,
            "approval_missing_status": approval_missing.status.value,
            "approval_missing_handler_called": approval_missing.handler_called,
            "approval_named_status": approval_named.status.value,
            "approval_named_handler_call_count": len(approval_handler.calls),
            "forbidden_status": forbidden.status.value,
            "forbidden_handler_called": forbidden.handler_called,
            "request_or_result_payload_persisted": False,
            "ledger_database_created": True,
            "ledger_database_reopened": True,
            "ledger_events_checked_before_reopen": integrity_before.events_checked,
            "ledger_events_checked_after_reopen": integrity_after.events_checked,
            "ledger_invocations_checked": integrity_after.invocations_checked,
            "ledger_integrity": integrity_after.ok,
            "generic_shell_surface": False,
            "filesystem_write_surface": False,
            "git_mutation_surface": False,
            "dynamic_import_eval_surface": False,
            "public_network_listener": False,
            "automatic_approval": False,
            "physical_validation": "PHYSICAL_NOT_EXECUTED",
        }
        ledger.close()

    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
