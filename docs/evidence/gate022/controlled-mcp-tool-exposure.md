# Gate 022 — Controlled MCP/tool exposure evidence

## Scope
Gate 022 adds a transport-neutral registered-capability broker that can be
wrapped by a later MCP transport without granting that transport ambient local
authority. Gate acceptance uses an in-process fake transport only; no network
listener or real MCP server is required.

## Capability contract
Each immutable capability declares:
- capability/project identity;
- mapped existing project policy action;
- input/output JSON Schemas;
- READ_ONLY side-effect class;
- timeout contract;
- request/result size budgets.

Public listing returns metadata only. Local handler/adapter objects are not
included.

Initial real bindings:
- `filesystem.read_text` using the accepted root-bounded read-only filesystem
  adapter plus an explicit configured relative-path allow-list;
- `git.status` using the accepted fixed read-only Git adapter.

## Dual policy boundary
Every registered invocation re-evaluates:
1. `external_disclosure`;
2. the capability's mapped project action.

Both must be ALLOW before the handler runs. A required approval must include a
named approver.

Zero local handler calls occur for:
- project mismatch;
- unregistered capability;
- request budget violation;
- input-schema rejection;
- missing external-disclosure approval;
- action-policy denial or missing approval.

## Execution/result boundary
The bridge accepts only canonical JSON arguments/results under configured bounds.
Handler exception, reported timeout, invalid result type, output-schema failure,
oversized output or capability-reported failure is terminal FAIL.

The bridge does not expose:
- arbitrary shell/process command;
- filesystem write/delete;
- Git mutation/push/merge;
- dynamic import/eval;
- automatic approval;
- credentials relay;
- concrete MCP/public network listener.

## Persistent audit
A separate append-only SQLite ledger records:
- invocation/project/capability identity;
- mapped action/side-effect metadata;
- combined `external_disclosure|action` policy decision;
- approval metadata;
- request SHA-256/size;
- response SHA-256/size for accepted results;
- evidence refs;
- failure class;
- predecessor linkage and event SHA-256.

Request arguments, result payloads and handler exception text are not persisted.

Transitions:
- REQUEST_RECORDED -> POLICY_BLOCKED
- REQUEST_RECORDED -> TOOL_FAILED
- REQUEST_RECORDED -> RESULT_ACCEPTED

## CI evidence

Initial implementation head:
`cc7a315fa58aa1be34daada3530305b6a918840c`
- tests: `266/266 PASS`
- generic CI: `35525960611 PASS`
- strict exact-head CI: `35525960343 PASS`

Disclosure/path hardening head:
`6a51beef91b1396a0afe816d4852287e95b4079b`
- tests: `268/268 PASS`
- generic CI: `35526184987 PASS`
- strict exact-head CI: `35526184994 PASS`

Runtime scope review:
`PASS`

## Primary-workstation Windows fake-transport smoke

Exact head:
`2d48e3cde3c2536565b90f65e39af2490fa8d53f`

Result:
`PASS_CONTROLLED_MCP_TOOL_EXPOSURE`

Observed:
- registered_capability_count = `3`
- handler_objects_exposed_in_listing = `false`
- external_disclosure_missing_status = `NEEDS_HUMAN_APPROVAL`
- external_disclosure_missing_handler_called = `false`
- read_only_capability_status = `PASS`
- read_only_result_exact = `true`
- unregistered_status = `BLOCKED`
- unregistered_handler_called = `false`
- approval_missing_status = `NEEDS_HUMAN_APPROVAL`
- approval_missing_handler_called = `false`
- approval_named_status = `PASS`
- approval_named_handler_call_count = `1`
- forbidden_status = `BLOCKED`
- forbidden_handler_called = `false`
- request_or_result_payload_persisted = `false`
- ledger_database_created = `true`
- ledger_database_reopened = `true`
- ledger_events_checked_before_reopen = `12`
- ledger_events_checked_after_reopen = `12`
- ledger_invocations_checked = `6`
- ledger_integrity = `true`
- generic_shell_surface = `false`
- filesystem_write_surface = `false`
- git_mutation_surface = `false`
- dynamic_import_eval_surface = `false`
- public_network_listener = `false`
- automatic_approval = `false`
- physical_validation = `PHYSICAL_NOT_EXECUTED`
- EXIT = `0`
- working tree remained clean and exact head unchanged.

## Remaining acceptance evidence

Run final generic and strict exact-head CI on the post-smoke evidence/status
head and complete final runtime scope review. Then prepare and validate one
final documentation-only acceptance head.

ADR-0021 remains `PROPOSED_GATE_022` until explicit exact-SHA human approval
and squash merge.
