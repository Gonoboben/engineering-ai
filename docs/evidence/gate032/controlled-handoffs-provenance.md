# Gate 032 — Controlled Model-to-Model Handoffs with Provenance Acceptance

## Scope

Gate 032 revalidates the accepted Gate 010 Task Blackboard / Supervisor-mediated
handoff runtime together with the accepted Gate 011 evidence-first independent
review boundary.

This Gate is predominantly acceptance-oriented. The only runtime hardening is
additive handoff provenance: existing Supervisor-created HANDOFF records now
carry explicit origin, target, visible evidence, and source/version identity
without changing routing, qualification, tool execution, policy, or project
authority.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

Release authorization:
`NOT_GRANTED`.

Fabrication authorization:
`NOT_GRANTED`.

## Accepted architecture reused

Gate 010 remains authoritative for:
- Task Blackboard as the bounded shared inter-worker surface;
- read-only worker views;
- Supervisor-created control and HANDOFF records;
- model records remaining ADVISORY;
- deterministic-tool authority for deterministic evidence;
- explicit visible-record context;
- hidden and cross-task evidence exclusion;
- fail-closed missing-context behavior;
- no direct worker-to-worker writes;
- no native-tool coder route without qualification.

Gate 011 remains authoritative for:
- deterministic evidence before model review;
- independent reviewer routing;
- same-model self-review prohibition;
- bounded revision and human escalation;
- model agreement never becoming deterministic evidence.

No new architecture is introduced by Gate 032.

## Gate 032 provenance contract

A Supervisor-created HANDOFF records:
- task identity;
- originating role;
- originating model/provider when the handoff originates from a model;
- target role;
- routed target model/provider;
- visible Blackboard record IDs;
- deterministic evidence references from visible records;
- relevant source/version references;
- model-route qualification evidence references.

Explicit source/version refs supplied by the Supervisor are preserved. Visible
deterministic evidence refs are also folded into the handoff provenance. If a
bounded handoff has no explicit source refs but does have visible records, the
append-only Blackboard record identities remain available as a deterministic
fallback provenance reference.

## Fail-closed acceptance cases

The Gate-specific deterministic smoke proves:
- hidden evidence cannot satisfy required context;
- evidence from another task cannot satisfy required context;
- missing required context produces no handoff;
- the coder cannot receive a native-tool-proposal handoff because that
  capability remains unqualified;
- a model cannot author a HANDOFF control record;
- the independent reviewer remains different from the originating model;
- the review handoff preserves originating and target provenance;
- a review finding remains ADVISORY and carries no deterministic evidence refs;
- no model agreement is promoted to evidence.

## Authority boundaries

Gate 032 adds no:
- model qualification;
- peer-to-peer/swarm authority;
- tool authority;
- generic filesystem or Git mutation authority;
- network authority;
- connected-project physics change;
- release/fabrication authority;
- physical-validation claim.

Practical model/runtime replacement remains outside Gate 032.

Persistent project memory with provenance remains Gate 033.

## Validation

Implementation validation is pending CI on the Gate 032 implementation head.

Required final acceptance evidence:
- full deterministic regression;
- generic CI;
- strict exact-head CI;
- Gate 032 Ubuntu/Windows acceptance workflow;
- inherited Phase 8 workflows;
- final exact-head validation after source-of-truth synchronization.

No PASS from this Gate is physical evidence.
