# Gate 031 — v1.0 measured and replaceable multi-model routing acceptance

## Gate identity
- Issue: #62
- PR: #63 (DRAFT)
- Branch: `gate-031-measured-replaceable-routing`
- Base: accepted Gate 030 squash merge
  `82ec76013e28c2d7db5644c1b99565170418f9a9`

## Objective
Close the Phase 8 / v1.0 criterion for measured and replaceable multi-model
routing by revalidating the already-accepted Gate 005/008 measurement evidence
and Gate 009 deterministic registry/router boundary as one cross-platform
acceptance package.

Gate 031 is acceptance-only. It does not qualify a new model, invoke models from
the Router, redefine Supervisor authority, or claim the separate later criterion
of practical workstation model/runtime replacement.

## Acceptance basis

Measured evidence:
- Gate 005 measured `gpt-oss:20b / medium` as the accepted baseline under a
  recorded local runtime envelope.
- Gate 008 measured `qwen3.5:9b` and qualified it for GENERAL_PLANNING.
- Gate 008 measured `qwen2.5-coder:7b-instruct` and qualified it with the hard
  limitation `NO_NATIVE_TOOL_PROPOSALS_UNDER_CURRENT_OLLAMA_CONTRACT`.

Deterministic routing:
- accepted registry entries carry provider/model identity, qualification,
  measured envelope and evidence references;
- GENERAL_PLANNING routes to `qwen3.5:9b`;
- CODE_REPOSITORY routes to `qwen2.5-coder:7b-instruct` only when native tool
  proposals are not required;
- BASELINE_REASONING routes to `gpt-oss:20b / medium`;
- context/output beyond measured limits fails closed as `NO_ROUTE`;
- unmeasured Vision and image-generation production routes remain `NO_ROUTE`.

Replaceability boundary:
- Router behavior is driven by an immutable `ModelCapabilityRegistry`;
- an alternate test-only registry entry can deterministically change the route
  without modifying Supervisor or Router implementation;
- route decisions preserve provider/model identity and evidence references;
- Router owns no provider/tool execution dependency.

The test-only replacement capability is synthetic and is not a production
qualification claim.

## Cross-platform validation
Gate-specific workflow:
`.github/workflows/gate031-measured-replaceable-routing.yml`

The workflow verifies the exact PR head independently on Ubuntu and Windows,
installs the package, and executes:

`python scripts/gate031_measured_replaceable_routing.py`

Final workflow IDs and exact-head regression counts are recorded only after CI.

## Explicit boundary to later Phase 8 work
This Gate closes only:
`measured and replaceable multi-model routing`.

It does **not** close:
`model/runtime replaceability demonstrated in practice`.

That later criterion requires an actual practical replacement/runtime
demonstration and must not be inferred from registry substitution alone.

## Authority boundaries
- architecture: unchanged;
- Supervisor authority: unchanged;
- automatic model qualification: prohibited;
- Router model execution: none;
- Router tool execution: none;
- remote Git mutation authority: not granted;
- release authorization: `NOT_GRANTED`;
- fabrication authorization: `NOT_GRANTED`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

## Gate state
Implementation is pending exact-head cross-platform validation and explicit human
exact-SHA squash-merge approval.
