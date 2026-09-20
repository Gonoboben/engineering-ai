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

## Remaining acceptance evidence
Run one primary-workstation Windows/Python 3.12 smoke on a stable
post-documentation Gate 020 head using
`scripts/gate020_scheduled_run_smoke.py`.

Required observations:
- due schedule executes;
- future schedule remains SCHEDULED;
- autonomous allowed job reaches PASS;
- approval-required job reaches WAITING_FOR_APPROVAL and its tool is not called;
- forbidden job reaches BLOCKED and its tool is not called;
- schedule-unlisted autonomous job remains QUEUED and its tool is not called;
- interrupted RUNNING job recovers BLOCKED;
- schedule/session ledger reopens with integrity PASS;
- queue integrity PASS;
- automatic_approval=false;
- os_scheduler_installation=false;
- daemon_service=false;
- physical validation remains PHYSICAL_NOT_EXECUTED.

ADR-0019 remains `PROPOSED_GATE_020` until exact-SHA human approval and squash merge.
