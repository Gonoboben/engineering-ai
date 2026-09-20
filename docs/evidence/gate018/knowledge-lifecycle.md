# Gate 018 — Knowledge lifecycle evidence

## Scope
Gate 018 defines deterministic promotion/invalidation semantics over accepted
Gate 016 memory and Gate 017 retrieval. It does not change Gate 016 storage
semantics, implement semantic/vector retrieval, inject context automatically,
or implement Gate 019/Gate 023.

## Architecture
Lifecycle state is stored in a separate append-only local SQLite ledger. The
ledger binds exact Gate 016 memory revisions by project ID, memory ID, record
ID, revision and canonical SHA-256.

Lifecycle stages:
1. OBSERVATION
2. EVIDENCE
3. ACCEPTED
4. INVALIDATED

INVALIDATED knowledge may later be re-qualified using only current evidence,
then accepted again. Every transition appends a new lifecycle revision.

## Trust boundaries
- observation memory must remain ADVISORY;
- MODEL cannot own a lifecycle transition;
- evidence must be current, non-model and evidence-qualified;
- CONTROL/ADR memory is not lifecycle evidence and cannot bypass human decision
  authority;
- physical validation is never inferred;
- no automatic Blackboard/model context injection exists;
- semantic/vector retrieval remains DEFERRED_NOT_JUSTIFIED.

## Revision drift
Every evidence/source dependency is bound to the exact memory revision/hash.
If Gate 016 memory has a newer revision for the same memory_id:
- source dependency -> STALE_SOURCE_REVISION;
- other evidence dependency -> STALE_EVIDENCE_REVISION.

Stale knowledge can be explicitly invalidated through an append-only lifecycle
revision. Prior accepted history remains reconstructable.

## CI evidence

Initial implementation head:
`e679067ca060d3182d4c51b18229c5c0d780a02e`

- deterministic tests: `191/191 PASS`
- generic CI run: `35513495763 PASS`
- strict exact-head CI run: `35513495762 PASS`

Corrected lifecycle head:
`72569edf34af12b78c0d3f04f6905c61e1d310d6`

- deterministic tests: `193/193 PASS`
- generic CI run: `35513601561 PASS`
- strict exact-head CI run: `35513601565 PASS`
- requalification after invalidation: tested
- CONTROL/ADR bypass through evidence: rejected
- project isolation: tested
- lifecycle hash tamper: fail-closed
- JSON Schemas: validated
- physical validation: `PHYSICAL_NOT_EXECUTED`

GitHub Actions currently emits an infrastructure warning that actions targeting
Node.js 20 are being forced to Node.js 24. The Gate 018 deterministic test suite
still completes successfully; this warning is not treated as engineering
validation evidence.

## Primary-workstation local smoke

Exact head:
`7d23cfd62e616659a793d21c7cb22ee7af0ca388`

Result:
`PASS_APPEND_ONLY_KNOWLEDGE_LIFECYCLE`

Observed:
- accepted_state_before_source_change = `ACCEPTED_CURRENT`
- observation_validation_class = `ADVISORY`
- source_revision_before = `1`
- source_revision_after = `2`
- stale_state = `STALE_SOURCE_REVISION`
- invalidated_revision = `4`
- final_state = `INVALIDATED`
- history_revisions = `[1, 2, 3, 4]`
- history_stages = `[OBSERVATION, EVIDENCE, ACCEPTED, INVALIDATED]`
- memory_integrity = `true`
- lifecycle_integrity = `true`
- automatic_context_injection = `false`
- semantic_vector_backend = `DEFERRED_NOT_JUSTIFIED`
- physical_validation_inferred = `false`
- physical_validation = `PHYSICAL_NOT_EXECUTED`
- EXIT = `0`
- working tree remained clean and branch head unchanged.

## Remaining acceptance evidence

Run final generic and strict exact-head CI on the post-smoke evidence/status
head and complete final scope review.

ADR-0017 remains `PROPOSED_GATE_018` until final exact-SHA human approval and
squash merge.
