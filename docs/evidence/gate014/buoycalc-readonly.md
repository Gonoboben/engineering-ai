# Gate 014 — BuoyCalc Strict Read-Only Adapter Evidence

## Scope

Gate 014 connects `Gonoboben/buoycalc-windows` to Engineering AI in strict
read-only mode.

No BuoyCalc source, governance, calculation result, solver/physics semantics,
UI/PDF/2D/report path, CI run, RC trigger, tag, GitHub Release, or physical
validation state is modified by this Gate.

Physical validation remains:
`PHYSICAL_NOT_EXECUTED`.

## Mandatory project authority

Resolved from current BuoyCalc `main`:

1. `AGENTS.md`
2. `docs/OPTIMIZATION_PLAN.md`
3. `RELEASE.md`

Observed source hashes:
- `AGENTS.md`: `2a747f0c17407b59d57f504194f18d29af55a878`
- `docs/OPTIMIZATION_PLAN.md`: `1fcf43d8f7698d7baea8a5c9cb4d705d8641bdae`
- `RELEASE.md`: `75cdf0e38f74598f5d4178a4be9080aa17fb43cf`

Missing mandatory governance is a hard adapter error.

## Current BuoyCalc repository baseline

Current `main` observed through the GitHub connector:
`0db1e7cc17e309fc1402fe58b265d2e95c2d4d39`.

Relevant accepted sequence:
- PR #606 head `0cc45f18132fdfec68a85c4c971fa45aba2993e0`
  merged as `a2da9d9df7034b88279d284b9a18d23a6958eb91`;
- PR #604 head `149c2eae96cd20f0ccff97ce18d51c2c36cc55c7`
  merged as current main `0db1e7cc17e309fc1402fe58b265d2e95c2d4d39`.

The Gate 014 adapter does not reinterpret or modify this engineering state.

## Preserved engineering invariants

The adapter deterministically checks governance/release markers for:

- engineering physics in calculation/solver domain only;
- UI/PDF/2D/report as consumers/renderers only;
- selected calculated X/Z as the only user-facing engineering geometry;
- production segmentation target `0.20 m`;
- signed feedback budget `64`;
- signed `WeightWaterKgM` semantics unchanged;
- Accepted signed candidate = exact deterministic fixed point;
- renderers = presentation only;
- 3D = post-v1;
- v1.0.0 tag/GitHub Release forbidden before explicit user approval after
  manual Windows RC smoke.

A missing/changed marker is surfaced as an invariant violation. The adapter does
not silently replace the project rule with a model assumption.

## Source-boundary inventory

Implementation:
`src/engineering_ai/projects/buoycalc.py`.

Tracked files are enumerated only through the fixed read-only Git
`ls-files` operation and are count-bounded.

Boundary classes:
- `GOVERNANCE`;
- `CALCULATION_CORE_CANDIDATE`;
- `READ_MODEL_CONSUMER`;
- `PRESENTATION_CONSUMER`;
- `VALIDATION_OR_TOOLING`;
- `OTHER`.

The classification is intentionally conservative. It does not declare that
every Services/Calculation file contains correct physics; it only prevents
presentation/report paths from being promoted to physics authority.

PDF/report/MainWindow/Views are presentation consumers, never
`CALCULATION_CORE_CANDIDATE`.

## Required check semantics

Governance minimum:
- `.NET Build`;
- `Selected Shape Consumer Scan`;
- `Report Store Consumer Scan`.

Release gate additionally requires:
- `BuoyCalc Validation 601 Main Gate`;
- `BuoyCalc Windows Build: success`.

CI classifications:
- `PASS`;
- `FAIL`;
- `CANCELLED`;
- `PENDING`;
- `MISSING`;
- `UNKNOWN`.

Only exact `success/completed` is PASS. Missing, queued/pending, cancelled,
failed or unknown evidence is non-PASS.

## Remote exact-head evidence

PR #604 exact head:
`149c2eae96cd20f0ccff97ce18d51c2c36cc55c7`.

Observed successful workflow runs on that exact PR head:
- `.NET Build`: run `34847992380`;
- `Selected Shape Consumer Scan`: run `34847992378`;
- `Report Store Consumer Scan`: run `34847992402`;
- `BuoyCalc Validation 601 Main Gate`: run `34847992459`;
- additional `BuoyCalc Validation 601 Physical Rejection`: run `34847992520`.

No `BuoyCalc Windows Build: success` workflow/status evidence was returned for
that head by the available connector query.

For current merge commit
`0db1e7cc17e309fc1402fe58b265d2e95c2d4d39`,
the workflow-run query returned no runs.

Gate 014 therefore does not infer an exact-main release PASS from PR-head
evidence.

## Release boundary

Adapter release state is fixed to:
`NOT_AUTHORIZED_REQUIRES_EXPLICIT_MANUAL_WINDOWS_RC_SMOKE`.

Gate 014 exposes no package/publish/tag/release-authorization API.

The repository may display identity `v1.0.0`, but that identity is not treated
as a published release.

## Gate 014 project policy

Autonomous:
- `read_repository`.

Forbidden:
- calculation/simulation execution;
- validators in this Gate;
- patch/worktree writes;
- commit/push/PR/merge;
- physics/architecture changes;
- validator weakening;
- fabrication/release authorization;
- destructive/scope-expansion/external-disclosure actions.

This Gate records validation semantics; it does not execute the BuoyCalc
calculation core or release pipeline.

## Deterministic validation

Implementation head:
`facc9d8b4a514120ce5be3a886fc77c8eda87dcc`

Result:
- deterministic tests: `128/128 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- exact revision verification: `PASS`.

Validated boundaries:
- mandatory governance resolution;
- invariant-marker detection and drift reporting;
- tracked-file inventory count bound;
- presentation/report paths cannot be classified as calculation-core candidates;
- PASS/FAIL/CANCELLED/PENDING/MISSING/UNKNOWN CI-state separation;
- fixed release state remains unauthorized;
- committed profile/policy schema validation;
- project write/release/execution API absence;
- missing local checkout returns structured `LOCAL_REPOSITORY_NOT_FOUND` with exit code 2.

Final acceptance-state CI remains required after status/evidence synchronization.

## Remaining acceptance

A local strict read-only smoke must run against
`C:\workspace\repos\buoycalc-windows`.

It must prove:
- local `main` equals `origin/main`;
- working tree is clean and unchanged before/after;
- all mandatory governance resolves;
- all invariant markers pass;
- source inventory is bounded;
- presentation/report paths are not physics-authoritative;
- release remains unauthorized;
- physical validation remains `PHYSICAL_NOT_EXECUTED`.


## Primary-workstation final BuoyCalc read-only smoke

The strict Gate 014 smoke completed successfully on the real Windows checkout.

Engineering AI pre-smoke head:
`b17fa249f4d717ed24b74898285addefac79be6c`.

Observed BuoyCalc repository:
- path: `C:\workspace\repos\buoycalc-windows`;
- branch: `main`;
- HEAD: `0db1e7cc17e309fc1402fe58b265d2e95c2d4d39`;
- `origin/main`: `0db1e7cc17e309fc1402fe58b265d2e95c2d4d39`;
- dirty: `false`;
- baseline_aligned: `true`;
- repository_unchanged: `true`.

Governance SHA-256:
- `AGENTS.md`:
  `1c9a78c3baed5ca452f26f783f9ca02ec7c632ff36652b6a7036c396770bdb0c`;
- `docs/OPTIMIZATION_PLAN.md`:
  `981d531b89da43ab136cd79bf98b71bcb099f39c17b39cd74af4a663c5906260`;
- `RELEASE.md`:
  `b901cc8dd9edbb7d9fdfffb50c0bfcabe9ab7c6a4d8cac0968995774ea43b3c0`.

Invariant checks:
- physics-domain-authority: PASS;
- presentation-is-renderer-only: PASS;
- selected-xz-primary-geometry: PASS;
- segmentation-020m: PASS;
- signed-feedback-budget-64: PASS;
- signed-weightwater-semantics: PASS;
- exact-deterministic-fixed-point: PASS;
- renderers-presentation-only: PASS;
- 3d-post-v1: PASS;
- release-needs-manual-smoke: PASS.

Invariant violations:
`[]`.

Tracked source inventory:
- total: `471`;
- VALIDATION_OR_TOOLING: `97`;
- PRESENTATION_CONSUMER: `113`;
- GOVERNANCE: `3`;
- OTHER: `196`;
- READ_MODEL_CONSUMER: `10`;
- CALCULATION_CORE_CANDIDATE: `52`.

Presentation/report physics-authority violation:
`false`.

Required check semantics were exposed exactly as:
- governance: .NET Build / Selected Shape Consumer Scan /
  Report Store Consumer Scan;
- release additionally: BuoyCalc Validation 601 Main Gate /
  BuoyCalc Windows Build: success.

Release state:
`NOT_AUTHORIZED_REQUIRES_EXPLICIT_MANUAL_WINDOWS_RC_SMOKE`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

Smoke state:
`READ_ONLY_BASELINE_OK`.

Smoke process exit:
`0`.

Classification:
`PASS_STRICT_READ_ONLY_BASELINE`.

No calculation, validator, solver, PDF/report generation, RC packaging, release
trigger, tag, GitHub Release, project write, commit, push or PR mutation was
performed.
