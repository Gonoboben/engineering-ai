from __future__ import annotations

import itertools
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from engineering_ai.supervisor import (
    Decision,
    ExternalConsultationEventType,
    ExternalConsultationLedger,
    ExternalConsultationRequest,
    ExternalConsultationStatus,
    ExternalContextItem,
    ExternalProviderResponse,
    ExternalReviewAuthority,
    ExternalReviewBridge,
    ExternalReviewIntegrityError,
    ExternalReviewPolicyError,
    ExternalReviewProtocolError,
    Supervisor,
)
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
    state["current_gate"] = "021"
    state["active_job_id"] = None
    state["repository_ref"] = {
        "branch": "gate-021-external-controlled-review-bridge",
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
        return f"xevt-test-{next(self._counter):04d}"


class FakeExternalProvider:
    provider_name = "fake-external"

    def __init__(
        self,
        *,
        content: str = "Advisory review only.",
        response_provider: str | None = None,
        response_model: str | None = None,
        raw_metadata: dict | None = None,
        error: Exception | None = None,
    ) -> None:
        self.content = content
        self.response_provider = response_provider
        self.response_model = response_model
        self.raw_metadata = raw_metadata or {}
        self.error = error
        self.calls = []

    def review(self, request, *, timeout_seconds: int):
        self.calls.append((request, timeout_seconds))
        if self.error is not None:
            raise self.error
        return ExternalProviderResponse(
            provider_name=self.response_provider or self.provider_name,
            model=self.response_model or request.model,
            content=self.content,
            raw_metadata=self.raw_metadata,
        )


def context(
    text: str = "explicit project excerpt",
    *,
    context_id: str = "ctx-one",
    project_id: str = "engineering-ai",
    contains_secrets: bool = False,
) -> ExternalContextItem:
    return ExternalContextItem(
        context_id=context_id,
        project_id=project_id,
        source_ref="STATUS.md:L1-L8",
        kind="FILE_EXCERPT",
        content=text,
        contains_secrets=contains_secrets,
    )


def request(
    *items: ExternalContextItem,
    consultation_id: str = "consultation-one",
    project_id: str = "engineering-ai",
    provider_name: str = "fake-external",
    model: str = "external-reviewer",
    max_context_chars: int = 1000,
    max_output_chars: int = 1000,
) -> ExternalConsultationRequest:
    if not items:
        items = (context(),)
    return ExternalConsultationRequest(
        consultation_id=consultation_id,
        project_id=project_id,
        gate_id="021",
        job_id="gate021-review",
        purpose="Review this explicit engineering context and identify concerns.",
        provider_name=provider_name,
        model=model,
        context_items=tuple(items),
        max_context_chars=max_context_chars,
        max_output_chars=max_output_chars,
        timeout_seconds=30,
    )


class ExternalReviewBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "external-consultations.sqlite3"
        self.ledger = ExternalConsultationLedger(
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

    def bridge(self, provider: FakeExternalProvider) -> ExternalReviewBridge:
        return ExternalReviewBridge(
            supervisor=self.supervisor,
            ledger=self.ledger,
            provider=provider,
        )

    def test_local_supervisor_remains_functional_without_external_bridge(self) -> None:
        decision = self.supervisor.inspect_project_action(action="read_repository")
        self.assertEqual(decision.decision, Decision.ALLOW)

    def test_unapproved_external_disclosure_calls_no_provider(self) -> None:
        provider = FakeExternalProvider()
        req = request()

        outcome = self.bridge(provider).consult(req)

        self.assertEqual(
            outcome.status,
            ExternalConsultationStatus.NEEDS_HUMAN_APPROVAL,
        )
        self.assertFalse(outcome.provider_called)
        self.assertIsNone(outcome.review)
        self.assertEqual(provider.calls, [])
        history = self.ledger.history(
            project_id="engineering-ai",
            consultation_id=req.consultation_id,
        )
        self.assertEqual(
            tuple(item.event_type for item in history),
            (
                ExternalConsultationEventType.REQUEST_RECORDED,
                ExternalConsultationEventType.POLICY_BLOCKED,
            ),
        )
        validate_instance(
            "external-consultation-snapshot.schema.json",
            history[-1].as_dict(),
        )

    def test_asserted_approval_without_named_approver_calls_no_provider(self) -> None:
        provider = FakeExternalProvider()
        outcome = self.bridge(provider).consult(
            request(consultation_id="consultation-no-name"),
            approval_obtained=True,
        )
        self.assertEqual(
            outcome.status,
            ExternalConsultationStatus.NEEDS_HUMAN_APPROVAL,
        )
        self.assertEqual(provider.calls, [])

    def test_approved_request_sends_exact_explicit_context_only(self) -> None:
        provider = FakeExternalProvider(content="External advisory response.")
        one = context("first exact excerpt", context_id="ctx-first")
        two = ExternalContextItem(
            context_id="ctx-second",
            project_id="engineering-ai",
            source_ref="evidence:abc123",
            kind="EVIDENCE_SUMMARY",
            content="second explicit excerpt",
        )
        req = request(
            one,
            two,
            consultation_id="consultation-approved",
        )

        outcome = self.bridge(provider).consult(
            req,
            approval_obtained=True,
            approver="human-owner",
        )

        self.assertEqual(outcome.status, ExternalConsultationStatus.PASS)
        self.assertTrue(outcome.provider_called)
        self.assertEqual(len(provider.calls), 1)
        sent, timeout = provider.calls[0]
        self.assertEqual(timeout, 30)
        self.assertEqual(sent.consultation_id, req.consultation_id)
        self.assertEqual(sent.model, req.model)
        self.assertEqual(sent.purpose, req.purpose)
        self.assertEqual(
            sent.contexts,
            (
                ("ctx-first", "STATUS.md:L1-L8", "FILE_EXCERPT", "first exact excerpt"),
                (
                    "ctx-second",
                    "evidence:abc123",
                    "EVIDENCE_SUMMARY",
                    "second explicit excerpt",
                ),
            ),
        )
        self.assertFalse(hasattr(sent, "tools"))
        self.assertFalse(hasattr(sent, "filesystem"))
        self.assertFalse(hasattr(sent, "shell"))

        review = outcome.review
        assert review is not None
        self.assertEqual(review.authority, ExternalReviewAuthority.ADVISORY)
        self.assertFalse(review.evidence_eligible)
        self.assertEqual(review.physical_validation, "PHYSICAL_NOT_EXECUTED")
        self.assertEqual(review.content, "External advisory response.")

    def test_ledger_does_not_store_outbound_content_or_purpose_text(self) -> None:
        secretish_but_explicit = "PROJECT-CONTENT-DO-NOT-PERSIST-123"
        purpose = "PURPOSE-TEXT-DO-NOT-PERSIST-456"
        item = context(secretish_but_explicit, context_id="ctx-ledger")
        req = replace(
            request(item, consultation_id="consultation-ledger"),
            purpose=purpose,
        )
        provider = FakeExternalProvider(content="advisory")

        outcome = self.bridge(provider).consult(
            req,
            approval_obtained=True,
            approver="human-owner",
        )
        self.assertEqual(outcome.status, ExternalConsultationStatus.PASS)

        raw = self.db.read_bytes()
        self.assertNotIn(secretish_but_explicit.encode("utf-8"), raw)
        self.assertNotIn(purpose.encode("utf-8"), raw)

        latest = self.ledger.get(
            project_id="engineering-ai",
            consultation_id=req.consultation_id,
        )
        manifest_text = json.dumps(latest.as_dict()["request_manifest"])
        self.assertNotIn(secretish_but_explicit, manifest_text)
        self.assertNotIn(purpose, manifest_text)
        self.assertIn(item.content_sha256, manifest_text)

    def test_context_marked_secrets_is_rejected_before_bridge(self) -> None:
        with self.assertRaises(ExternalReviewPolicyError):
            context(
                "api-key-like material",
                context_id="ctx-secret",
                contains_secrets=True,
            )

    def test_cross_project_context_is_rejected(self) -> None:
        foreign = context(
            "foreign project data",
            context_id="ctx-foreign",
            project_id="buoycalc",
        )
        with self.assertRaises(ExternalReviewPolicyError):
            request(
                foreign,
                consultation_id="consultation-cross-project",
            )

    def test_purpose_and_context_labels_have_hard_bounds(self) -> None:
        with self.assertRaises(ValueError):
            replace(
                request(consultation_id="consultation-purpose-bound"),
                purpose="p" * 4001,
            )
        with self.assertRaises(ValueError):
            ExternalContextItem(
                context_id="ctx-source-bound",
                project_id="engineering-ai",
                source_ref="s" * 2049,
                kind="FILE_EXCERPT",
                content="x",
            )
        with self.assertRaises(ValueError):
            ExternalContextItem(
                context_id="ctx-kind-bound",
                project_id="engineering-ai",
                source_ref="source",
                kind="k" * 129,
                content="x",
            )

    def test_persisted_manifest_is_deeply_immutable(self) -> None:
        req = request(consultation_id="consultation-immutable")
        outcome = self.bridge(FakeExternalProvider()).consult(req)
        self.assertEqual(
            outcome.status,
            ExternalConsultationStatus.NEEDS_HUMAN_APPROVAL,
        )
        item = self.ledger.get(
            project_id="engineering-ai",
            consultation_id=req.consultation_id,
        )
        with self.assertRaises(TypeError):
            item.request_manifest["model"] = "mutated"
        self.assertIsInstance(item.request_manifest["context_items"], tuple)

    def test_context_budget_is_enforced_before_provider_call(self) -> None:
        with self.assertRaises(ExternalReviewPolicyError):
            request(
                context("0123456789", context_id="ctx-budget"),
                consultation_id="consultation-budget",
                max_context_chars=5,
            )

    def test_provider_identity_mismatch_rejected_before_provider_call(self) -> None:
        provider = FakeExternalProvider()
        req = request(
            consultation_id="consultation-provider-mismatch",
            provider_name="another-provider",
        )
        with self.assertRaises(ExternalReviewProtocolError):
            self.bridge(provider).consult(
                req,
                approval_obtained=True,
                approver="human-owner",
            )
        self.assertEqual(provider.calls, [])

    def test_provider_response_identity_mismatch_fails_closed(self) -> None:
        provider = FakeExternalProvider(response_provider="spoofed-provider")
        req = request(consultation_id="consultation-spoofed")
        outcome = self.bridge(provider).consult(
            req,
            approval_obtained=True,
            approver="human-owner",
        )
        self.assertEqual(outcome.status, ExternalConsultationStatus.FAIL)
        self.assertTrue(outcome.provider_called)
        self.assertIsNone(outcome.review)
        latest = self.ledger.get(
            project_id="engineering-ai",
            consultation_id=req.consultation_id,
        )
        self.assertEqual(
            latest.event_type,
            ExternalConsultationEventType.PROVIDER_FAILED,
        )

    def test_oversized_external_response_fails_closed(self) -> None:
        provider = FakeExternalProvider(content="x" * 11)
        req = request(
            consultation_id="consultation-oversize",
            max_output_chars=10,
        )
        outcome = self.bridge(provider).consult(
            req,
            approval_obtained=True,
            approver="human-owner",
        )
        self.assertEqual(outcome.status, ExternalConsultationStatus.FAIL)
        self.assertIsNone(outcome.review)

    def test_external_tool_metadata_is_rejected(self) -> None:
        provider = FakeExternalProvider(
            content="attempted proposal",
            raw_metadata={"tool_calls": [{"name": "read_repository"}]},
        )
        req = request(consultation_id="consultation-tool-metadata")
        outcome = self.bridge(provider).consult(
            req,
            approval_obtained=True,
            approver="human-owner",
        )
        self.assertEqual(outcome.status, ExternalConsultationStatus.FAIL)
        self.assertIsNone(outcome.review)

    def test_provider_exception_text_is_not_persisted(self) -> None:
        leaked = "REMOTE-ECHO-OF-PROJECT-CONTENT"
        provider = FakeExternalProvider(error=RuntimeError(leaked))
        req = request(consultation_id="consultation-provider-error")
        outcome = self.bridge(provider).consult(
            req,
            approval_obtained=True,
            approver="human-owner",
        )
        self.assertEqual(outcome.status, ExternalConsultationStatus.FAIL)
        self.assertNotIn(leaked, outcome.summary)
        self.assertNotIn(leaked.encode("utf-8"), self.db.read_bytes())

    def test_policy_denied_disclosure_calls_no_provider(self) -> None:
        state = make_state()
        state["effective_permissions"]["approval_required"].remove(
            "external_disclosure"
        )
        state["effective_permissions"]["forbidden"].append("external_disclosure")
        supervisor = Supervisor(policy=make_policy(), state=state)
        provider = FakeExternalProvider()
        bridge = ExternalReviewBridge(
            supervisor=supervisor,
            ledger=self.ledger,
            provider=provider,
        )
        req = request(consultation_id="consultation-denied")
        outcome = bridge.consult(
            req,
            approval_obtained=True,
            approver="human-owner",
        )
        self.assertEqual(outcome.status, ExternalConsultationStatus.BLOCKED)
        self.assertEqual(provider.calls, [])

    def test_duplicate_consultation_id_is_rejected(self) -> None:
        provider = FakeExternalProvider()
        req = request(consultation_id="consultation-duplicate")
        first = self.bridge(provider).consult(req)
        self.assertEqual(
            first.status,
            ExternalConsultationStatus.NEEDS_HUMAN_APPROVAL,
        )
        with self.assertRaises(ExternalReviewPolicyError):
            self.bridge(provider).consult(req)

    def test_tampered_ledger_fails_closed(self) -> None:
        req = request(consultation_id="consultation-tamper")
        self.bridge(FakeExternalProvider()).consult(req)
        self.ledger.close()

        conn = sqlite3.connect(self.db)
        try:
            conn.execute("DROP TRIGGER external_consultation_no_update")
            conn.execute(
                """
                UPDATE external_consultation_events
                SET provider_name = 'tampered-provider'
                WHERE consultation_id = 'consultation-tamper'
                  AND event_type = 'REQUEST_RECORDED'
                """
            )
            conn.commit()
        finally:
            conn.close()

        self.ledger = ExternalConsultationLedger(
            self.db,
            event_id_factory=IdFactory(),
        )
        with self.assertRaises(ExternalReviewIntegrityError):
            self.ledger.history(
                project_id="engineering-ai",
                consultation_id=req.consultation_id,
            )

    def test_gate021_smoke_script(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/gate021_external_review_smoke.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate"], "021")
        self.assertEqual(
            payload["state"],
            "PASS_EXTERNAL_CONTROLLED_ADVISORY_BRIDGE",
        )
        self.assertEqual(
            payload["unapproved_status"],
            "NEEDS_HUMAN_APPROVAL",
        )
        self.assertFalse(payload["unapproved_provider_called"])
        self.assertEqual(payload["approved_status"], "PASS")
        self.assertTrue(payload["approved_provider_called"])
        self.assertEqual(payload["provider_call_count"], 1)
        self.assertTrue(payload["exact_explicit_context_sent"])
        self.assertFalse(payload["outbound_content_persisted"])
        self.assertEqual(payload["review_authority"], "ADVISORY")
        self.assertFalse(payload["review_evidence_eligible"])
        self.assertFalse(payload["tool_surface_exposed"])
        self.assertTrue(payload["ledger_database_reopened"])
        self.assertTrue(payload["ledger_integrity"])
        self.assertFalse(payload["real_external_network_call"])
        self.assertFalse(payload["automatic_external_approval"])
        self.assertEqual(
            payload["physical_validation"],
            "PHYSICAL_NOT_EXECUTED",
        )

    def test_integrity_report_and_no_external_tool_surface(self) -> None:
        req = request(consultation_id="consultation-integrity")
        outcome = self.bridge(FakeExternalProvider()).consult(req)
        self.assertEqual(
            outcome.status,
            ExternalConsultationStatus.NEEDS_HUMAN_APPROVAL,
        )
        report = self.ledger.verify_integrity(project_id="engineering-ai")
        self.assertTrue(report.ok)
        self.assertEqual(report.events_checked, 2)
        self.assertEqual(report.consultations_checked, 1)

        bridge = self.bridge(FakeExternalProvider())
        for name in (
            "run_tool",
            "execute_shell",
            "write_file",
            "git_push",
            "grant_approval",
        ):
            self.assertFalse(hasattr(bridge, name))


if __name__ == "__main__":
    unittest.main()
