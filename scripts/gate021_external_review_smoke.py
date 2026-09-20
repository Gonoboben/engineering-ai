from __future__ import annotations

import json
import tempfile
from pathlib import Path

from engineering_ai.supervisor import (
    ExternalConsultationLedger,
    ExternalConsultationRequest,
    ExternalConsultationStatus,
    ExternalContextItem,
    ExternalProviderResponse,
    ExternalReviewAuthority,
    ExternalReviewBridge,
    Supervisor,
)


def policy() -> dict:
    return {
        "schema_version": "1.0",
        "policy_version": "gate021-smoke",
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
        "current_gate": "021",
        "active_job_id": None,
        "repository_ref": {
            "branch": "gate-021-external-controlled-review-bridge",
            "head_sha": "0123456789abcdef0123456789abcdef01234567",
        },
        "architecture_baseline": "Gate 020 accepted scheduled unattended runs",
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


class FakeProvider:
    provider_name = "fake-external"

    def __init__(self) -> None:
        self.calls = []

    def review(self, request, *, timeout_seconds: int):
        self.calls.append((request, timeout_seconds))
        return ExternalProviderResponse(
            provider_name=self.provider_name,
            model=request.model,
            content="Advisory only: review the deterministic evidence before action.",
            raw_metadata={"transport": "fake-local-no-network"},
        )


def consultation(
    consultation_id: str,
    text: str,
) -> ExternalConsultationRequest:
    return ExternalConsultationRequest(
        consultation_id=consultation_id,
        project_id="engineering-ai",
        gate_id="021",
        job_id="gate021-smoke-review",
        purpose="Independent advisory review of one explicitly selected excerpt.",
        provider_name="fake-external",
        model="fake-reviewer",
        context_items=(
            ExternalContextItem(
                context_id=f"ctx-{consultation_id}",
                project_id="engineering-ai",
                source_ref="synthetic:gate021-smoke",
                kind="EXPLICIT_SMOKE_CONTEXT",
                content=text,
            ),
        ),
        max_context_chars=1000,
        max_output_chars=1000,
        timeout_seconds=30,
    )


def main() -> int:
    outbound_text = "GATE021-EXPLICIT-OUTBOUND-CONTEXT-DO-NOT-PERSIST"
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "external-consultations.sqlite3"
        ledger = ExternalConsultationLedger(db)
        provider = FakeProvider()
        supervisor = Supervisor(policy=policy(), state=state())
        bridge = ExternalReviewBridge(
            supervisor=supervisor,
            ledger=ledger,
            provider=provider,
        )

        blocked = bridge.consult(
            consultation("consultation-unapproved", outbound_text)
        )
        assert blocked.status is ExternalConsultationStatus.NEEDS_HUMAN_APPROVAL
        assert blocked.provider_called is False
        assert provider.calls == []

        approved = bridge.consult(
            consultation("consultation-approved", outbound_text),
            approval_obtained=True,
            approver="human-owner",
        )
        assert approved.status is ExternalConsultationStatus.PASS
        assert approved.provider_called is True
        assert approved.review is not None
        assert approved.review.authority is ExternalReviewAuthority.ADVISORY
        assert approved.review.evidence_eligible is False
        assert approved.review.physical_validation == "PHYSICAL_NOT_EXECUTED"
        assert len(provider.calls) == 1

        sent, timeout = provider.calls[0]
        assert timeout == 30
        assert sent.contexts == (
            (
                "ctx-consultation-approved",
                "synthetic:gate021-smoke",
                "EXPLICIT_SMOKE_CONTEXT",
                outbound_text,
            ),
        )
        assert not hasattr(sent, "tools")
        assert not hasattr(sent, "filesystem")
        assert not hasattr(sent, "shell")

        integrity_before = ledger.verify_integrity(project_id="engineering-ai")
        assert integrity_before.ok
        raw_before = db.read_bytes()
        assert outbound_text.encode("utf-8") not in raw_before
        ledger.close()

        ledger = ExternalConsultationLedger(db)
        integrity_after = ledger.verify_integrity(project_id="engineering-ai")
        approved_history = ledger.history(
            project_id="engineering-ai",
            consultation_id="consultation-approved",
        )
        blocked_history = ledger.history(
            project_id="engineering-ai",
            consultation_id="consultation-unapproved",
        )
        raw_after = db.read_bytes()

        assert integrity_after.ok
        assert len(approved_history) == 2
        assert len(blocked_history) == 2
        assert outbound_text.encode("utf-8") not in raw_after

        payload = {
            "gate": "021",
            "state": "PASS_EXTERNAL_CONTROLLED_ADVISORY_BRIDGE",
            "unapproved_status": blocked.status.value,
            "unapproved_provider_called": blocked.provider_called,
            "approved_status": approved.status.value,
            "approved_provider_called": approved.provider_called,
            "provider_call_count": len(provider.calls),
            "exact_explicit_context_sent": True,
            "outbound_content_persisted": False,
            "request_manifest_hash_recorded": bool(
                approved.review.request_manifest_sha256
            ),
            "response_hash_recorded": bool(approved.review.response_sha256),
            "review_authority": approved.review.authority.value,
            "review_evidence_eligible": approved.review.evidence_eligible,
            "tool_surface_exposed": False,
            "ledger_database_created": True,
            "ledger_database_reopened": True,
            "ledger_events_checked_before_reopen": integrity_before.events_checked,
            "ledger_events_checked_after_reopen": integrity_after.events_checked,
            "ledger_integrity": integrity_after.ok,
            "real_external_network_call": False,
            "automatic_external_approval": False,
            "physical_validation": "PHYSICAL_NOT_EXECUTED",
        }
        ledger.close()

    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
