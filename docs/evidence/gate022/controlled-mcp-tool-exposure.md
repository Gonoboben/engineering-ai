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

## Remaining acceptance evidence
Run one primary-workstation Windows/Python 3.12 fake-transport smoke on a stable
post-documentation Gate 022 head using:
`scripts/gate022_controlled_tool_smoke.py`

Required observations:
- state = PASS_CONTROLLED_MCP_TOOL_EXPOSURE;
- external_disclosure_missing_status = NEEDS_HUMAN_APPROVAL;
- external_disclosure_missing_handler_called = false;
- registered read-only capability = PASS after named approval;
- unregistered = BLOCKED / zero handler calls;
- approval-missing = NEEDS_HUMAN_APPROVAL / zero handler calls;
- named approval executes only the registered fake capability once;
- forbidden = BLOCKED / zero handler calls;
- request/result payload persisted = false;
- ledger reopen/integrity PASS;
- generic shell/write/Git-mutation/dynamic-eval/public-listener surfaces = false;
- automatic_approval = false;
- physical_validation = PHYSICAL_NOT_EXECUTED.

ADR-0021 remains `PROPOSED_GATE_022` until explicit exact-SHA human approval
and squash merge.
