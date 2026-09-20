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

## Remaining acceptance evidence
Run one primary-workstation Windows/Python 3.12 smoke on a stable post-documentation
Gate 019 head using `scripts/gate019_job_queue_smoke.py`.

Required observations:
- database created and reopened;
- retry attempts survive reopen;
- retry later completes PASS through Supervisor;
- WAITING_FOR_APPROVAL survives reopen;
- explicit Supervisor approval resume completes only with named approval;
- interrupted RUNNING job recovers BLOCKED;
- queue integrity PASS;
- automatic_approval=false;
- scheduled_execution=false;
- physical validation remains PHYSICAL_NOT_EXECUTED.

ADR-0018 remains `PROPOSED_GATE_019` until exact-SHA human approval and squash merge.
