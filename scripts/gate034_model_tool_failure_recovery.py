from __future__ import annotations

import itertools
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from engineering_ai.models import (
    ModelProviderUnavailable,
    ModelResponse,
    ModelToolCall,
    ModelToolSpec,
)
from engineering_ai.supervisor import (
    PersistedJobQueue,
    PlannerExecutorReviewerLoop,
    QueueEventType,
    RoleModelConfig,
    StubTool,
    Supervisor,
    ToolOutcome,
)
from engineering_ai.tools import (
    AllowListedProcessRunner,
    CommandSpec,
    NetworkRequirement,
    ToolAccessError,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_fixture(name: str) -> dict:
    with (FIXTURES / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def make_policy() -> dict:
    return load_fixture("valid_policy.json")


def make_state(head: str) -> dict:
    state = load_fixture("valid_state.json")
    state["current_gate"] = "034"
    state["active_job_id"] = None
    state["repository_ref"] = {
        "branch": "gate-034-model-tool-failure-recovery",
        "head_sha": head,
    }
    state["pending_checks"] = []
    state["blockers"] = []
    state["next_admissible_action"] = None
    return state


def make_job(
    job_id: str,
    *,
    action: str = "read_repository",
    retry_limit: int = 1,
) -> dict:
    job = load_fixture("valid_job.json")
    job["job_id"] = job_id
    job["project_id"] = "engineering-ai"
    job["gate_id"] = "034"
    job["objective"] = f"Gate 034 recovery scenario {job_id}"
    job["scope"] = ["documented model/tool failure recovery"]
    job["out_of_scope"] = ["architecture redesign", "authority expansion"]
    job["requested_actions"] = [action]
    job["required_validators"] = []
    job["retry_limit"] = retry_limit
    job["attempts"] = 0
    job["status"] = "QUEUED"
    job["blocker"] = None
    return job


class MutableClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 10, 3, 8, 0, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


class EventIds:
    def __init__(self) -> None:
        self.counter = itertools.count(1)

    def __call__(self) -> str:
        return f"qevt-gate034-{next(self.counter):04d}"


class ScriptedProvider:
    provider_name = "gate034-scripted"

    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.requests = []

    def runtime_version(self):
        return "gate034-scripted-1"

    def runtime_diagnostics(self):
        return {
            "provider": self.provider_name,
            "runtime_version": self.runtime_version(),
        }

    def chat(self, request, *, timeout_seconds=300.0):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("unexpected model call")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return ModelResponse(
            provider=self.provider_name,
            runtime_version=self.runtime_version(),
            model=request.model,
            content=(
                item["raw_content"]
                if "raw_content" in item
                else json.dumps(item.get("content", {}))
            ),
            tool_calls=tuple(item.get("tool_calls", ())),
            done_reason="stop",
        )


READ_SPEC = ModelToolSpec(
    name="read_repository",
    description="read one repository object",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string"}},
    },
)


def make_loop(
    *,
    provider: ScriptedProvider,
    state: dict,
    executor,
) -> PlannerExecutorReviewerLoop:
    return PlannerExecutorReviewerLoop(
        policy=make_policy(),
        state=state,
        provider=provider,
        model_config=RoleModelConfig(
            model="gate034-model",
            timeout_seconds=1.0,
        ),
        tool_specs={"read_repository": READ_SPEC},
        tool_executors={"read_repository": executor},
        max_protocol_retries=1,
    )


def successful_provider() -> ScriptedProvider:
    return ScriptedProvider(
        [
            {
                "content": {
                    "steps": ["inspect"],
                    "allowed_actions": ["read_repository"],
                }
            },
            {
                "content": {"summary": "inspection complete"},
                "tool_calls": [
                    ModelToolCall(
                        "read_repository",
                        {"path": "STATUS.md"},
                    )
                ],
            },
            {
                "content": {
                    "decision": "ACCEPT",
                    "summary": "deterministic evidence is sufficient",
                }
            },
        ]
    )


def main() -> int:
    head = git_head()
    initial_state = make_state(head)

    # Model-provider failure must become a bounded, persistable retry state.
    with tempfile.TemporaryDirectory() as tmp:
        queue_path = Path(tmp) / "model-recovery.sqlite3"
        ids = EventIds()
        queue = PersistedJobQueue(queue_path, event_id_factory=ids)
        model_job = make_job("gate034-model-retry")
        queue.enqueue(model_job, timeout_seconds=120)
        claimed = queue.claim_next(project_id="engineering-ai")
        require(claimed is not None, "model recovery job was not claimed")

        unavailable_provider = ScriptedProvider(
            [ModelProviderUnavailable("synthetic runtime unavailable")]
        )
        unavailable_result = make_loop(
            provider=unavailable_provider,
            state=initial_state,
            executor=lambda args: ToolOutcome(
                True,
                "unused",
                ("gate034:unused",),
            ),
        ).run(
            job=claimed.job_dict(),
            user_task="Exercise model runtime recovery",
        )
        require(
            unavailable_result.job["status"] == "QUEUED",
            "model unavailable did not requeue bounded work",
        )
        require(
            unavailable_result.job["attempts"] == 1,
            "model unavailable did not increment attempts exactly once",
        )
        require(
            unavailable_result.project_state["next_admissible_action"]
            == "retry role loop after planner model provider recovery",
            "model recovery next action is not explicit",
        )
        failed_model_events = [
            event
            for event in unavailable_result.audit_events
            if event["event_type"] == "MODEL_CALL"
            and event["result"]["status"] == "FAIL"
        ]
        require(
            len(failed_model_events) == 1,
            "model provider failure was not audited exactly once",
        )

        persisted_retry = queue.persist_execution_result(
            project_id="engineering-ai",
            job_id=model_job["job_id"],
            result_job=unavailable_result.job,
        )
        require(
            persisted_retry.status == "QUEUED"
            and persisted_retry.attempts == 1,
            "model retry state was not persisted",
        )
        queue.close()
        queue = PersistedJobQueue(queue_path, event_id_factory=ids)
        reopened_retry = queue.get(
            project_id="engineering-ai",
            job_id=model_job["job_id"],
        )
        require(
            reopened_retry.status == "QUEUED"
            and reopened_retry.attempts == 1,
            "model retry state did not survive reopen",
        )
        retry_claim = queue.claim_next(project_id="engineering-ai")
        require(retry_claim is not None, "persisted model retry was not reclaimable")

        recovered_result = make_loop(
            provider=successful_provider(),
            state=unavailable_result.project_state,
            executor=lambda args: ToolOutcome(
                True,
                "read recovered",
                ("gate034:model-recovered",),
            ),
        ).run(
            job=retry_claim.job_dict(),
            user_task="Recover after model runtime returns",
        )
        require(
            recovered_result.job["status"] == "PASS"
            and recovered_result.job["attempts"] == 1,
            "model recovery did not preserve attempt count and pass",
        )
        require(
            not any(
                blocker.startswith("model provider failure; retry available:")
                for blocker in recovered_result.project_state["blockers"]
            ),
            "successful retry retained stale model recovery blocker",
        )
        final_model = queue.persist_execution_result(
            project_id="engineering-ai",
            job_id=model_job["job_id"],
            result_job=recovered_result.job,
        )
        require(final_model.status == "PASS", "recovered model job was not persisted PASS")
        model_queue_integrity = queue.verify_integrity(project_id="engineering-ai")
        model_history = queue.history(
            project_id="engineering-ai",
            job_id=model_job["job_id"],
        )
        require(model_queue_integrity.ok, "model recovery queue integrity failed")
        queue.close()

    exhausted_model_job = make_job("gate034-model-exhausted")
    exhausted_model_job["attempts"] = 1
    exhausted_model = make_loop(
        provider=ScriptedProvider(
            [ModelProviderUnavailable("synthetic runtime still unavailable")]
        ),
        state=make_state(head),
        executor=lambda args: ToolOutcome(True, "unused"),
    ).run(
        job=exhausted_model_job,
        user_task="Exhaust model recovery",
    )
    require(
        exhausted_model.job["status"] == "FAIL",
        "model retry exhaustion did not terminate FAIL",
    )
    require(
        "retry limit exhausted after model provider failure"
        in (exhausted_model.blocker or ""),
        "model retry exhaustion blocker missing",
    )

    # Tool failures reuse the Supervisor-owned attempts/retry_limit classifier.
    first_tool_provider = ScriptedProvider(
        [
            {
                "content": {
                    "steps": ["inspect"],
                    "allowed_actions": ["read_repository"],
                }
            },
            {
                "content": {"summary": "attempt deterministic read"},
                "tool_calls": [
                    ModelToolCall(
                        "read_repository",
                        {"path": "STATUS.md"},
                    )
                ],
            },
        ]
    )
    first_tool = make_loop(
        provider=first_tool_provider,
        state=make_state(head),
        executor=lambda args: ToolOutcome(
            False,
            "synthetic deterministic tool failure",
            ("gate034:tool-failure",),
        ),
    ).run(
        job=make_job("gate034-tool-retry"),
        user_task="Exercise deterministic tool recovery",
    )
    require(
        first_tool.job["status"] == "QUEUED"
        and first_tool.job["attempts"] == 1,
        "tool failure did not enter bounded retry state",
    )
    require(
        first_tool.project_state["next_admissible_action"]
        == "retry read_repository",
        "tool retry next action is not explicit",
    )

    tool_recovered = make_loop(
        provider=successful_provider(),
        state=first_tool.project_state,
        executor=lambda args: ToolOutcome(
            True,
            "deterministic tool recovered",
            ("gate034:tool-recovered",),
        ),
    ).run(
        job=first_tool.job,
        user_task="Recover deterministic tool execution",
    )
    require(
        tool_recovered.job["status"] == "PASS"
        and tool_recovered.job["attempts"] == 1,
        "tool retry did not recover while preserving attempts",
    )
    require(
        not any(
            blocker.startswith("tool failure; retry available:")
            for blocker in tool_recovered.project_state["blockers"]
        ),
        "successful tool retry retained stale recovery blocker",
    )

    exhausted_tool_job = make_job("gate034-tool-exhausted")
    exhausted_tool_job["attempts"] = 1
    exhausted_tool = make_loop(
        provider=first_tool_provider.__class__(
            [
                {
                    "content": {
                        "steps": ["inspect"],
                        "allowed_actions": ["read_repository"],
                    }
                },
                {
                    "content": {"summary": "retry deterministic read"},
                    "tool_calls": [
                        ModelToolCall(
                            "read_repository",
                            {"path": "STATUS.md"},
                        )
                    ],
                },
            ]
        ),
        state=make_state(head),
        executor=lambda args: ToolOutcome(
            False,
            "synthetic deterministic tool failure",
            ("gate034:tool-failure-final",),
        ),
    ).run(
        job=exhausted_tool_job,
        user_task="Exhaust deterministic tool recovery",
    )
    require(
        exhausted_tool.job["status"] == "FAIL"
        and exhausted_tool.job["attempts"] == 1,
        "tool retry exhaustion did not terminate deterministically",
    )

    # Existing structured-output correction remains bounded.
    protocol_provider = ScriptedProvider(
        [
            {
                "content": {
                    "steps": ["inspect"],
                    "allowed_actions": ["read_repository"],
                }
            },
            {
                "content": {"summary": "inspection complete"},
                "tool_calls": [
                    ModelToolCall(
                        "read_repository",
                        {"path": "STATUS.md"},
                    )
                ],
            },
            {"raw_content": ""},
            {
                "content": {
                    "decision": "ACCEPT",
                    "summary": "corrected reviewer response",
                }
            },
        ]
    )
    protocol_recovered = make_loop(
        provider=protocol_provider,
        state=make_state(head),
        executor=lambda args: ToolOutcome(
            True,
            "read ok",
            ("gate034:protocol-evidence",),
        ),
    ).run(
        job=make_job("gate034-protocol-recover"),
        user_task="Recover malformed reviewer protocol",
    )
    require(
        protocol_recovered.job["status"] == "PASS"
        and len(protocol_provider.requests) == 4,
        "bounded protocol correction did not recover",
    )

    protocol_exhausted = make_loop(
        provider=ScriptedProvider(
            [
                {
                    "content": {
                        "steps": ["inspect"],
                        "allowed_actions": ["read_repository"],
                    }
                },
                {
                    "content": {"summary": "inspection complete"},
                    "tool_calls": [
                        ModelToolCall(
                            "read_repository",
                            {"path": "STATUS.md"},
                        )
                    ],
                },
                {"raw_content": ""},
                {"raw_content": ""},
            ]
        ),
        state=make_state(head),
        executor=lambda args: ToolOutcome(
            True,
            "read ok",
            ("gate034:protocol-exhausted",),
        ),
    ).run(
        job=make_job("gate034-protocol-exhausted"),
        user_task="Exhaust malformed reviewer protocol",
    )
    require(
        protocol_exhausted.job["status"] == "FAIL"
        and "structured-output retry exhausted"
        in (protocol_exhausted.blocker or ""),
        "protocol retry exhaustion was not explicit FAIL",
    )

    # Process timeout is a structured deterministic tool result.
    with tempfile.TemporaryDirectory() as tmp:
        timeout_runner = AllowListedProcessRunner(
            {
                "gate034.timeout": CommandSpec(
                    command_id="gate034.timeout",
                    executable=sys.executable,
                    network_requirement=NetworkRequirement.LOCAL_ONLY,
                    fixed_args=("-c", "import time; time.sleep(1.0)"),
                    timeout_seconds=0.1,
                    max_output_bytes=4096,
                )
            },
            root=tmp,
        )
        timeout_result = timeout_runner.run("gate034.timeout")
        require(
            timeout_result.timed_out
            and not timeout_result.ok
            and timeout_result.exit_code is None,
            "process timeout was not classified as a structured failure",
        )

        offline_runner = AllowListedProcessRunner(
            {
                "gate034.network": CommandSpec(
                    command_id="gate034.network",
                    executable=sys.executable,
                    network_requirement=NetworkRequirement.NETWORK_CAPABLE,
                    fixed_args=("-c", "print('must-not-run')"),
                    timeout_seconds=1.0,
                )
            },
            root=tmp,
            offline=True,
        )
        offline_blocked = False
        try:
            offline_runner.run("gate034.network")
        except ToolAccessError:
            offline_blocked = True
        require(
            offline_blocked,
            "offline network-capable operation was not blocked before process execution",
        )

    # Policy denial is blocked without consuming retry attempts or calling a tool.
    forbidden_calls: list[str] = []

    def forbidden_tool(action: str) -> ToolOutcome:
        forbidden_calls.append(action)
        return ToolOutcome(True, "must not execute")

    denied_job = make_job(
        "gate034-policy-denied",
        action="validator_weakening",
    )
    denied = Supervisor(
        policy=make_policy(),
        state=make_state(head),
    ).execute(
        job=denied_job,
        action="validator_weakening",
        tool=forbidden_tool,
    )
    require(
        denied.job["status"] == "BLOCKED"
        and denied.job["attempts"] == 0
        and not denied.tool_called
        and forbidden_calls == [],
        "policy denial was misclassified as a retriable tool failure",
    )

    # Persisted queue restart/deadline recovery remains fail-closed.
    with tempfile.TemporaryDirectory() as tmp:
        clock = MutableClock()
        ids = EventIds()
        queue_path = Path(tmp) / "queue-recovery.sqlite3"
        queue = PersistedJobQueue(
            queue_path,
            clock=clock,
            event_id_factory=ids,
        )

        interrupted_job = make_job("gate034-interrupted")
        queue.enqueue(interrupted_job, timeout_seconds=120)
        interrupted_claim = queue.claim_next(project_id="engineering-ai")
        require(
            interrupted_claim is not None
            and interrupted_claim.status == "RUNNING",
            "interrupted scenario did not enter RUNNING",
        )
        queue.close()
        queue = PersistedJobQueue(
            queue_path,
            clock=clock,
            event_id_factory=ids,
        )
        interrupted = queue.recover_interrupted_runs(
            project_id="engineering-ai"
        )
        require(
            len(interrupted) == 1
            and interrupted[0].status == "BLOCKED"
            and interrupted[0].event_type
            is QueueEventType.INTERRUPTED_RECOVERY,
            "interrupted RUNNING recovery was not fail-closed",
        )

        timeout_job = make_job("gate034-deadline")
        queue.enqueue(timeout_job, timeout_seconds=2)
        deadline_claim = queue.begin_run(
            project_id="engineering-ai",
            job_id=timeout_job["job_id"],
        )
        late_pass = deadline_claim.job_dict()
        late_pass["status"] = "PASS"
        clock.advance(3)
        late_result = queue.persist_execution_result(
            project_id="engineering-ai",
            job_id=timeout_job["job_id"],
            result_job=late_pass,
        )
        require(
            late_result.status == "BLOCKED"
            and late_result.event_type is QueueEventType.TIMEOUT_RECOVERY,
            "late PASS was accepted after persisted deadline expiry",
        )
        queue_integrity = queue.verify_integrity(project_id="engineering-ai")
        require(queue_integrity.ok, "queue recovery integrity failed")
        queue.close()

    # WAITING_FOR_APPROVAL survives reopen and cannot self-approve.
    with tempfile.TemporaryDirectory() as tmp:
        approval_path = Path(tmp) / "approval.sqlite3"
        ids = EventIds()
        queue = PersistedJobQueue(approval_path, event_id_factory=ids)
        approval_supervisor = Supervisor(
            policy=make_policy(),
            state=make_state(head),
            job_queue=queue,
        )
        approval_job = make_job(
            "gate034-approval",
            action="architecture_change",
        )
        approval_supervisor.enqueue_persisted_job(
            approval_job,
            timeout_seconds=120,
        )
        approval_claim = approval_supervisor.claim_next_persisted_job()
        require(approval_claim is not None, "approval job was not claimed")
        approval_tool = StubTool(
            ToolOutcome(True, "approval-gated action would execute")
        )
        waiting = approval_supervisor.execute(
            job=approval_claim.job_dict(),
            action="architecture_change",
            tool=approval_tool,
        )
        require(
            waiting.job["status"] == "WAITING_FOR_APPROVAL"
            and approval_tool.calls == [],
            "approval boundary executed tool without approval",
        )
        approval_supervisor.persist_persisted_job_result(
            job_id=approval_job["job_id"],
            result_job=waiting.job,
        )
        queue.close()
        queue = PersistedJobQueue(approval_path, event_id_factory=ids)
        reopened_approval = queue.get(
            project_id="engineering-ai",
            job_id=approval_job["job_id"],
        )
        require(
            reopened_approval.status == "WAITING_FOR_APPROVAL",
            "approval wait did not survive reopen",
        )
        require(
            queue.claim_next(project_id="engineering-ai") is None,
            "approval-waiting job was automatically reclaimed",
        )
        approval_integrity = queue.verify_integrity(project_id="engineering-ai")
        require(approval_integrity.ok, "approval queue integrity failed")
        queue.close()

    false_pass = any(
        status == "PASS"
        for status in (
            unavailable_result.job["status"],
            exhausted_model.job["status"],
            first_tool.job["status"],
            exhausted_tool.job["status"],
            denied.job["status"],
            interrupted[0].status,
            late_result.status,
            reopened_approval.status,
        )
    )
    require(not false_pass, "a failure/recovery boundary produced false PASS")

    result = {
        "gate": "034",
        "state": "PASS_V1_0_DOCUMENTED_MODEL_TOOL_FAILURE_RECOVERY",
        "source_revision": head,
        "model_recovery": {
            "unavailable_first_state": unavailable_result.job["status"],
            "unavailable_attempts": unavailable_result.job["attempts"],
            "failed_model_audit_recorded": len(failed_model_events) == 1,
            "persisted_reopen_state": reopened_retry.status,
            "persisted_reopen_attempts": reopened_retry.attempts,
            "recovered_state": recovered_result.job["status"],
            "recovered_attempts": recovered_result.job["attempts"],
            "retry_exhausted_state": exhausted_model.job["status"],
            "queue_history_events": [
                snapshot.event_type.value for snapshot in model_history
            ],
            "queue_integrity": model_queue_integrity.ok,
        },
        "tool_recovery": {
            "first_state": first_tool.job["status"],
            "first_attempts": first_tool.job["attempts"],
            "recovered_state": tool_recovered.job["status"],
            "recovered_attempts": tool_recovered.job["attempts"],
            "retry_exhausted_state": exhausted_tool.job["status"],
            "supervisor_owned_retry_classification": True,
        },
        "protocol_recovery": {
            "bounded_correction_recovered": (
                protocol_recovered.job["status"] == "PASS"
            ),
            "retry_exhausted_state": protocol_exhausted.job["status"],
        },
        "process_recovery": {
            "timeout_structured": timeout_result.timed_out,
            "timeout_ok": timeout_result.ok,
            "offline_network_blocked_before_execution": offline_blocked,
        },
        "queue_recovery": {
            "interrupted_state": interrupted[0].status,
            "interrupted_event": interrupted[0].event_type.value,
            "late_pass_state": late_result.status,
            "late_pass_event": late_result.event_type.value,
            "integrity": queue_integrity.ok,
        },
        "authority_boundaries": {
            "policy_denial_state": denied.job["status"],
            "policy_denial_attempts": denied.job["attempts"],
            "policy_denial_tool_called": denied.tool_called,
            "approval_survived_reopen": (
                reopened_approval.status == "WAITING_FOR_APPROVAL"
            ),
            "automatic_approval": False,
            "false_pass": false_pass,
            "new_architecture_authority": False,
            "new_model_authority": False,
            "new_tool_authority": False,
            "new_git_authority": False,
            "new_network_authority": False,
            "release_authority": False,
            "fabrication_authority": False,
        },
        "physical_validation": "PHYSICAL_NOT_EXECUTED",
    }

    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
