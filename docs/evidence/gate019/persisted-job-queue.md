# Gate 019 — Persisted job queue evidence

## Scope
Gate 019 adds persisted bounded job control state only. It does not add a
scheduler, daemon, overnight runner, distributed workers, external queue,
automatic approvals or broader action authority.

## Storage model
The queue is a local SQLite append-only event ledger.

Events:
- ENQUEUED
- RUN_STARTED
- EXECUTION_RESULT
- INTERRUPTED_RECOVERY
- TIMEOUT_RECOVERY

Every event stores a complete schema-valid job snapshot, exact predecessor event,
timeout/deadline metadata, timestamp and canonical SHA-256.

The queue verifies:
- project/job identity;
- event hash;
- exact linear supersession chain;
- immutable job definition fields;
- valid job schema/attempt semantics.

## Control semantics
- enqueue does not execute a job;
- claim does not grant action authority;
- existing Supervisor.execute remains the execution/policy authority;
- retries are bounded by existing job/Supervisor semantics;
- retry QUEUED events re-enter deterministic FIFO at the tail;
- WAITING_FOR_APPROVAL persists across reopen and is not low-level claimable;
- explicit approval resume requires Supervisor + current PolicyEngine + named
  human approver;
- interrupted or expired RUNNING state recovers BLOCKED, not PASS/QUEUED;
- a result persisted after its deadline is blocked rather than accepted as PASS;
- terminal jobs are not automatically requeued;
- queue exposes no schedule/daemon/tool-execution/approval-grant API.

## CI evidence

Implementation head:
`63b612fd64e7317cf4dad218bce63f130f966ae8`
- tests: `208/208 PASS`
- generic CI: `35516817721 PASS`
- strict exact-head CI: `35516817717 PASS`

Approval-boundary head:
`f65ca9c7cce403511a2e685dd6baf8b0fbc70a0e`
- tests: `208/208 PASS`
- generic CI: `35516884394 PASS`
- strict exact-head CI: `35516884392 PASS`

Smoke/acceptance-test head:
`983dafc9da4df41094961d4ce438cec7f4c8623e`
- tests: `209/209 PASS`
- generic CI: `35516965090 PASS`
- strict exact-head CI: `35516965135 PASS`
- Gate 019 smoke harness executes in CI
- direct queue WAITING_FOR_APPROVAL resume rejected

## Primary-workstation local smoke

Exact head:
`f423f16d4895049121026386f37a9c9c68b8bf89`

Result:
`PASS_PERSISTED_JOB_QUEUE_REOPEN_RECOVERY`

Observed:
- database_created = `true`
- database_reopened = `true`
- fifo_retry_tail_preserved = `true`
- retry_attempts_preserved = `1`
- retry_final_state = `PASS`
- approval_wait_survived_reopen = `true`
- approval_final_state = `PASS`
- interrupted_run_recovery = `INTERRUPTED_RECOVERY`
- interrupted_final_state = `BLOCKED`
- queue_events_checked = `13`
- queue_jobs_checked = `3`
- queue_integrity = `true`
- automatic_approval = `false`
- scheduled_execution = `false`
- distributed_workers = `false`
- physical_validation = `PHYSICAL_NOT_EXECUTED`
- EXIT = `0`
- working tree remained clean and branch head unchanged.

## Remaining acceptance evidence

Run final generic and strict exact-head CI on the post-smoke evidence/status
head and complete final scope review.

ADR-0018 remains `PROPOSED_GATE_019` until explicit exact-SHA human approval
and squash merge.
