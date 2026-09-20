# Gate 023 — Provenance-preserving Vision worker evidence

## Scope

Gate 023 adds a bounded local Vision-worker boundary for explicit images while
preserving the accepted deterministic Supervisor/model-routing authority.

It does not qualify a production Vision model merely because a runtime or model
family advertises multimodal capability.

Base:
`3111a1d793c05ead0292839500e698a9c5fe2c56` (Gate 022 squash merge).

Issue:
`#45`.

PR:
`#46`.

## Implemented boundary

- explicit transient `ModelImageAttachment` inputs;
- allow-listed PNG/JPEG/WebP media types;
- bounded per-image and aggregate image sizes;
- basic declared-media signature validation;
- SHA-256 and exact source-reference identity;
- raw image bytes hidden from normal object `repr`;
- loopback Ollama transport sends inline base64 bytes only;
- no image path or URL is sent to the model transport;
- distinct deterministic `VISION_ANALYSIS` routing class;
- routing requires `supports_vision_inputs=true` in a qualified capability;
- default accepted model registry intentionally has no Vision candidate;
- default Vision route therefore returns `NO_ROUTE`;
- typed Vision worker request/result contract;
- schema-bounded structured observations;
- every observation may cite only exact supplied source references;
- provider tool calls are rejected on the Vision path;
- model result authority fixed to `ADVISORY`;
- `evidence_eligible=false`;
- `physical_validation=PHYSICAL_NOT_EXECUTED`;
- no automatic Blackboard/evidence/knowledge promotion.

## Validation history

Initial implementation checkpoint:

`bb48c4ff1af907e324455e0979208192ac972a6c`

- deterministic regression: `278/278 PASS`;
- generic workflow run `35527536750`: `PASS`;
- strict exact-head workflow run `35527536771`: `PASS`.

Input-hardening checkpoint:

`f33f2ba785e37d43d96a4e5293a013af4047c222`

This head intentionally introduced declared-media signature checks before the
existing synthetic fixtures were updated. CI correctly failed on the stale
fixtures. This was a test/fixture transition, not evidence of a bypass or a
weakened runtime boundary.

Corrected hardening and smoke checkpoint:

`539d8dfb328aefa496b957110f1e903036844357`

- signature-valid fixtures installed;
- Gate 023 smoke harness added to deterministic regression;
- deterministic regression: `279/279 PASS`;
- generic workflow run `35527660162`: `PASS`;
- strict exact-head workflow run `35527660202`: `PASS`;
- smoke state: `PASS_PROVENANCE_PRESERVING_VISION_BOUNDARY`;
- unmeasured default Vision route: `NO_ROUTE`;
- provider calls before qualified synthetic route: `0`;
- qualified synthetic boundary route: `PASS`;
- tool surface exposed: `false`;
- result authority: `ADVISORY`;
- evidence eligible: `false`;
- source reference/hash preserved: `true`;
- raw image persisted in result: `false`;
- external network: `false`;
- automatic evidence promotion: `false`;
- production Vision model qualified: `false`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

## Final hardening checkpoint

Exact head:
`82ca772902738de0670fab84bbd28914d0684e44`.

Additional hardening:
- raw `VisionInput.data` hidden from normal object `repr`;
- returned provider identity must match the deterministic routed provider;
- explicit regression coverage for provider-identity mismatch and transient
  request representation.

Validation:
- deterministic regression: `280/280 PASS`;
- generic workflow run `35527817840`: `PASS`;
- strict exact-head workflow run `35527817828`: `PASS`;
- smoke state: `PASS_PROVENANCE_PRESERVING_VISION_BOUNDARY`.

## Scope review

Review of the PR diff confirms no Gate 023 runtime addition of:

- arbitrary filesystem reads;
- URL/network image fetching;
- camera/live-video capture;
- shell/process authority;
- Git mutation;
- generic tool execution;
- automatic approval;
- automatic Blackboard/evidence/knowledge promotion;
- external/cloud Vision provider;
- CAD manipulation;
- image generation;
- architecture/physics/fabrication/release authority.

The only added `urlopen` references are in tests that patch the pre-existing
loopback Ollama provider. The only new `Path` use is the test loader for the
Gate 023 smoke script.

## Model qualification boundary

Production Vision model:
`NOT_QUALIFIED`.

Real Vision semantic-quality qualification:
`NOT_RUN / SEPARATE_MEASURED_QUALIFICATION_REQUIRED`.

A synthetic qualified capability is used only to validate the deterministic
routing and worker boundary. It does not qualify any production model.

## Validation semantics

Gate 023 software tests establish only the stated software control boundary.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.
