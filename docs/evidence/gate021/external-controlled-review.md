# Gate 021 — External controlled reasoning/review bridge evidence

## Scope
Gate 021 adds an optional provider-neutral external advisory review bridge. The
local Engineering AI core remains functional without it. Gate acceptance uses a
fake provider only; no real external network call or credentials are required.

## Disclosure and authority boundary
Every outbound context item is explicitly constructed by the caller and includes:
- context_id;
- project_id;
- source_ref;
- kind;
- exact text (provider call only);
- deterministic SHA-256 and character count.

Cross-project context mixing is rejected. Items explicitly marked as containing
secrets are rejected. Purpose/source_ref/kind/context/output/timeout dimensions
are bounded.

Before a provider call, current Supervisor/PolicyEngine evaluates
`external_disclosure`.
- missing required approval -> NEEDS_HUMAN_APPROVAL and zero provider calls;
- policy denial -> BLOCKED and zero provider calls;
- current ALLOW -> provider may receive the exact explicit payload.

The provider request contains no local tools, filesystem, shell, Git, queue,
scheduler, approval handle or MCP capability.

## Response semantics
An accepted external response is:
- authority: ADVISORY;
- evidence_eligible: false;
- physical_validation: PHYSICAL_NOT_EXECUTED.

Malformed identity, empty/oversized content, tool-call metadata or provider
failure results in FAIL, not accepted advisory output.

## Persistent audit
A separate append-only SQLite ledger records:
- request manifest metadata;
- source refs;
- purpose/context character counts;
- request context hashes;
- provider/model identity;
- approval-required/obtained/approver fields;
- response hash/size;
- terminal status/failure class.

It does not persist outbound context text or purpose text. Provider exception
text is intentionally omitted because it may echo disclosed project data.

Transitions:
- REQUEST_RECORDED -> POLICY_BLOCKED
- REQUEST_RECORDED -> PROVIDER_FAILED
- REQUEST_RECORDED -> RESPONSE_ACCEPTED

Full history and SHA-256 integrity fail closed.

## CI evidence
Initial implementation head:
`8ed0f345ef7f2904041f1b14a08403b846f7141b`
- tests: `245/245 PASS`
- generic CI: `35524343520 PASS`
- strict exact-head CI: `35524343416 PASS`

Hardening head:
`bca9381cf10462cc66e0b92c324fb0225acaada7`
- added hard outbound metadata bounds and deep manifest immutability
- generic CI: `35524431902 FAIL`
- strict exact-head CI: `35524431903 FAIL`
- reason: one new regression incorrectly attempted direct JSON serialization
  of mappingproxy; runtime bridge defect was not indicated

Corrected hardened head:
`f6ed7a9a36c75f08248efe6fbe8148b5fa75a2c8`
- tests: `247/247 PASS`
- generic CI: `35524489887 PASS`
- strict exact-head CI: `35524489903 PASS`

Runtime scope review:
`PASS`

Confirmed absent:
- concrete external network client
- credentials/API-key storage
- provider local tool/filesystem/shell/Git authority
- automatic approval
- MCP runtime
- semantic/vector backend
- physical PASS inference

## Primary-workstation Windows fake-provider smoke

Exact head:
`306466507f5ead228b4efd7194df9a85512d80cf`

Result:
`PASS_EXTERNAL_CONTROLLED_ADVISORY_BRIDGE`

Observed:
- unapproved_status = `NEEDS_HUMAN_APPROVAL`
- unapproved_provider_called = `false`
- approved_status = `PASS`
- approved_provider_called = `true`
- provider_call_count = `1`
- exact_explicit_context_sent = `true`
- outbound_content_persisted = `false`
- request_manifest_hash_recorded = `true`
- response_hash_recorded = `true`
- review_authority = `ADVISORY`
- review_evidence_eligible = `false`
- tool_surface_exposed = `false`
- ledger_database_created = `true`
- ledger_database_reopened = `true`
- ledger_events_checked_before_reopen = `4`
- ledger_events_checked_after_reopen = `4`
- ledger_integrity = `true`
- real_external_network_call = `false`
- automatic_external_approval = `false`
- physical_validation = `PHYSICAL_NOT_EXECUTED`
- EXIT = `0`
- working tree remained clean and branch head unchanged.

## Remaining acceptance evidence

Run final generic and strict exact-head CI on the post-smoke evidence/status
head and complete final runtime scope review. Then prepare and validate one
final documentation-only acceptance head.

ADR-0020 remains `PROPOSED_GATE_021` until explicit exact-SHA human approval
and squash merge.


## Final acceptance checkpoint

Post-smoke evidence head:
`cf57c13890637d3e1d072e0d83e66f97cb13e365`

Validation:
- deterministic tests: `247/247 PASS`
- generic CI run: `35525232870 PASS`
- strict exact-head CI run: `35525232786 PASS`
- primary-workstation fake-provider smoke:
  `PASS_EXTERNAL_CONTROLLED_ADVISORY_BRIDGE`

Final runtime scope review:
`PASS`

Confirmed absent:
- concrete external network client
- credentials/API-key handling
- provider local tool/filesystem/shell/Git authority
- automatic approval granting
- MCP runtime
- semantic/vector backend
- physical PASS inference
- architecture/physics/fabrication/release authority expansion

ADR-0020 remains `PROPOSED_GATE_021` until explicit exact-SHA human approval
and squash merge.
