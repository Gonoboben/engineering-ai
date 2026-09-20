# Gate 020 — Scheduled/overnight engineering runs evidence

## Scope
Gate 020 adds persisted one-shot due schedules and bounded unattended sessions on
top of the accepted Gate 019 queue. It does not install an operating-system
scheduler, run a daemon/service, grant approvals, or broaden tool authority.

## Authority model
A schedule allowed_actions list is a narrowing constraint, not permission.

For every queued job:
1. the current Supervisor/PolicyEngine is evaluated;
2. only a current ALLOW action also present in allowed_actions may invoke a
   supplied narrow tool;
3. NEEDS_HUMAN_APPROVAL persists WAITING_FOR_APPROVAL without calling a tool;
4. DENY persists BLOCKED without calling a tool;
5. an autonomous action omitted by the schedule stays QUEUED.

## Persistence model
Schedule/session state uses a separate local SQLite append-only ledger.

Transitions:
- SCHEDULED -> SESSION_STARTED -> SESSION_COMPLETED
- SCHEDULED -> SESSION_STARTED -> SESSION_BLOCKED
- SCHEDULED -> CANCELLED

Each event includes exact predecessor identity and canonical SHA-256. Full
history, event semantics and schedule definition immutability are verified.

An interrupted SESSION_STARTED is blocked on next one-shot invocation and is not
automatically replayed.

## Bounded execution
- max_jobs: 1..100 claims per session
- max_session_seconds: 1..86400
- Gate 019 job retry/deadline semantics remain in force
- interrupted prior RUNNING queue jobs recover BLOCKED before new unattended work
- ambiguous multi-action jobs block without tool execution
- missing tool bindings block fail-closed

## Summary
Completed sessions record:
- PASS / FAIL / BLOCKED / WAITING_FOR_APPROVAL / CANCELLED / QUEUED counts for
  touched jobs;
- touched/recovered job IDs;
- claims;
- stop reason;
- deterministic evidence refs from Supervisor audit/tool outcomes;
- PHYSICAL_NOT_EXECUTED.

## CI evidence

Initial implementation head:
`d455738ee9522aa7c1c2671cc3cd9bf6f1e567e5`
- tests: `226/226 PASS`
- generic CI: `35522348903 PASS`
- strict exact-head CI: `35522348911 PASS`

Chronology-hardening head:
`a61a3e1fa16341265396b66a9db73700bfaabc7c`
- tests: `227/227 PASS`
- generic CI: `35522438419 PASS`
- strict exact-head CI: `35522438328 PASS`

Runtime scope review:
`PASS`

Confirmed absent:
- OS scheduler/service installation
- daemon/service runtime
- automatic approval granting
- unrestricted shell
- remote/cloud scheduler
- distributed workers
- semantic/vector backend
- vision runtime
- PHYSICAL_PASS synthesis
- generic SQL write API

## Primary-workstation Windows smoke

Exact head:
`82ead2e02f381a9ce988263058662c2614b23428`

Result:
`PASS_SCHEDULED_UNATTENDED_RUN_SESSION`

Observed:
- due_schedule_executed = `true`
- future_schedule_remained_scheduled = `true`
- autonomous_allowed_final_state = `PASS`
- approval_final_state = `WAITING_FOR_APPROVAL`
- forbidden_final_state = `BLOCKED`
- unlisted_autonomous_final_state = `QUEUED`
- interrupted_final_state = `BLOCKED`
- summary_counts = `PASS 1 / BLOCKED 2 / WAITING_FOR_APPROVAL 1 / FAIL 0 / CANCELLED 0 / QUEUED 0`
- summary_evidence_refs = `ev-gate020-read`
- approval_tool_calls = `[]`
- forbidden_tool_calls = `[]`
- unlisted_tool_calls = `[]`
- schedule_database_created = `true`
- schedule_database_reopened = `true`
- schedule_events_checked_before_reopen = `4`
- schedule_events_checked_after_reopen = `4`
- schedule_integrity = `true`
- queue_events_checked = `13`
- queue_integrity = `true`
- automatic_approval = `false`
- os_scheduler_installation = `false`
- daemon_service = `false`
- distributed_workers = `false`
- physical_validation = `PHYSICAL_NOT_EXECUTED`
- EXIT = `0`
- working tree remained clean and branch head unchanged.

## Remaining acceptance evidence

Run final generic and strict exact-head CI on the post-smoke evidence/status
head and complete final runtime scope review. Then prepare and validate one
final documentation-only acceptance head.

ADR-0019 remains `PROPOSED_GATE_020` until explicit exact-SHA human approval
and squash merge.
