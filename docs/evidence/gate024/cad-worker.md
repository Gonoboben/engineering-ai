# Gate 024 — Controlled parametric CAD worker evidence

## Gate identity
- Issue: #47 — Gate 024 — Controlled parametric CAD worker
- PR: #48
- Branch: `gate-024-controlled-parametric-cad-worker`
- Base: Gate 023 accepted squash merge `f3c826a434eca8e5d7163f5cf4166560717bdbc2`
- Physical validation: `PHYSICAL_NOT_EXECUTED`

## Objective
Provide a bounded parametric CAD proposal path with deterministic geometry checks
while preserving the accepted deterministic Supervisor authority model.

Gate 024 does not grant a new CAD-write permission. CAD generation is permitted
only as the already accepted `propose_patch` action and remains a proposed
working-branch artifact. Fabrication and release authority are unchanged.

## Implemented boundary

### Typed design
The accepted baseline supports:
- millimetres only;
- axis-aligned boxes;
- cylinders along +Z;
- translation-only placement;
- at most 128 entities;
- finite bounded dimensions and coordinates;
- unique ASCII-safe entity IDs.

The typed primitive kind cannot be overridden through caller input. Non-typed
entities and invalid placements fail closed.

### Deterministic geometry
Before any CAD runtime call the control plane derives:
- canonical design JSON and SHA-256;
- analytical volume for every primitive;
- per-entity axis-aligned bounding box;
- assembly axis-aligned bounding box;
- sum of primitive volumes.

The total volume is explicitly
`SUM_OF_PRIMITIVES_NOT_BOOLEAN_UNION`; overlapping solids are not silently
treated as a boolean-union volume.

### Supervisor authority
`CadWorker` routes generation only through
`Supervisor.evaluate_tool_proposal(..., action="propose_patch")`.

A current policy denial results in:
- `Decision.DENY`;
- zero CAD backend calls;
- no target artifact.

Gate 024 adds no `cad_write` permission and does not alter fabrication,
release, architecture, physics, destructive-action or validator policy.

### Trusted FreeCAD bridge
The concrete bridge invokes only the repository-owned
`scripts/freecad_parametric_worker.py` using `FreeCADCmd` with
`shell=False`.

The helper accepts data-only canonical JSON and fixed input/output arguments.
There is no interface for:
- model-provided Python source;
- macros;
- arbitrary executable names;
- shell commands;
- `eval` or `exec`;
- dynamic code loading;
- arbitrary filesystem writes.

### Publication boundary
The requested artifact path:
- must be relative to the configured project root;
- must resolve inside that root;
- must use the `.FCStd` suffix;
- must not be a symlink target.

The CAD runtime first writes into a temporary directory. Candidate artifact and
runtime-report symlinks are rejected.

Before target publication, runtime geometry must match the deterministic
expected:
- design SHA-256;
- entity identities;
- primitive kinds;
- entity volumes;
- entity AABBs;
- assembly AABB;
- total primitive volume.

A mismatch fails closed and the requested target artifact is not published.

## Evidence semantics
A successful Gate 024 result proves only the checked relationship:

`typed parametric specification -> generated geometry consistency`.

It does not prove:
- correctness of engineering intent;
- structural adequacy;
- manufacturability;
- safety;
- fabrication readiness;
- release readiness;
- physical validation.

Accordingly:
- geometry-consistency evidence: `ELIGIBLE_FOR_DEFINED_DETERMINISTIC_SCOPE`;
- engineering-design correctness: `NOT_ESTABLISHED_BY_CAD_WORKER`;
- fabrication authorization: `NOT_GRANTED`;
- release authorization: `NOT_GRANTED`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

## Deterministic smoke
Smoke:
`PASS_CONTROLLED_PARAMETRIC_CAD_BOUNDARY`

Verified:
- policy denial CAD backend calls: 0;
- approved `propose_patch` backend calls: 1;
- valid design/geometry hashes preserved;
- valid proposal artifact authority: `PROPOSED_PATCH_ONLY`;
- deterministic geometry mismatch blocked;
- mismatched target artifact not published;
- arbitrary model-script surface absent;
- shell surface absent;
- fabrication authority absent;
- release authority absent;
- real FreeCAD installation not required by deterministic CI;
- physical validation remains `PHYSICAL_NOT_EXECUTED`.

## Regression / CI history

### Core runtime hardening
Head:
`a02822fdecb8573fb20b33fb70b94e6ca5ac16cc`

Validation:
- generic workflow `35530942168`: `PASS`;
- strict exact-head workflow `35530942160`: `PASS`.

### Full deterministic suite with smoke
Corrected full-test head:
`bd9ebd15206be83f012e4ddd5625257247d37653`

Validation:
- deterministic regression: `289/289 PASS`;
- generic workflow `35530909113`: `PASS`;
- strict exact-head workflow `35530909124`: `PASS`;
- smoke: `PASS_CONTROLLED_PARAMETRIC_CAD_BOUNDARY`.

### Intermediate test-fixture failure
Intermediate test heads failed because a synthetic
`repository_ref.head_sha` string did not satisfy the already-existing schema
requirement for a 40-character hexadecimal Git SHA.

This was corrected by using an exact schema-valid repository SHA. No runtime
validator, schema, policy, CAD boundary or test requirement was weakened.

### Architecture/ADR head
Head:
`80f7372556c7799aaa80638f9717449da477d805`

Validation:
- generic workflow `35530998720`: `PASS`;
- strict exact-head workflow `35530998811`: `PASS`.

## Real FreeCAD execution state
A real FreeCAD workstation generation run has not been executed as Gate 024 CI
evidence in this session.

State:
- trusted FreeCAD bridge implementation: `IMPLEMENTED`;
- fake-runtime deterministic boundary validation: `PASS`;
- real FreeCAD runtime smoke: `NOT_RUN`;
- real CAD artifact semantic/manual inspection: `NOT_RUN`;
- production CAD-specialist model qualification: `NOT_RUN / NOT_REQUIRED_GATE_024`.

No claim of real FreeCAD execution, manufacturability, or physical validation is
made from the synthetic/fake-runtime PASS.

## Runtime scope review
Confirmed absent:
- new autonomous CAD/write permission;
- arbitrary model-generated code execution;
- generic shell/process command surface;
- unrestricted filesystem write surface;
- model-owned Supervisor/policy authority;
- fabrication or release authorization;
- automatic evidence promotion to engineering-design correctness;
- PHYSICAL_PASS synthesis;
- Gate 025 image-generation capability.

## Decision state
ADR-0023 remains `PROPOSED_GATE_024` until explicit exact-SHA human
squash-merge approval and accepted merge of PR #48.
