# Gate 029 — v1.0 deterministic tool/validator integration acceptance

## Gate identity
- Issue: #57
- Branch: `gate-029-deterministic-tool-validator-integration`
- Base: accepted Gate 028 squash merge
  `e6e6dcf2dff3d081f2fb3c394b919f60b43e2c78`

## Objective
Close the Phase 8 / v1.0 criterion for deterministic tool/validator integration
by revalidating the already-accepted tool adapter and connected-project
validator boundaries as one cross-platform acceptance package.

Gate 029 is an acceptance Gate. It does not add new generic execution,
filesystem-write, remote Git mutation, release, fabrication, architecture or
project-physics authority.

## Acceptance basis
The Gate 029 smoke executes the existing deterministic test modules for:
- root-bounded filesystem and read-only Git adapters;
- allow-listed fixed-profile process execution;
- PlataVM read-only and controlled integration;
- BuoyCalc read-only and controlled integration.

It also executes the accepted Gate 027 offline continuation smoke and checks its
structured network-boundary result.

The acceptance package proves the following existing properties together:
- filesystem reads/listing stay root-bounded;
- the Git adapter remains read-only and exposes no public generic command API;
- process execution stays fixed-profile, `shell=False`, timeout-bounded and
  output-bounded;
- network-capable commands are blocked before executable resolution/subprocess
  creation in offline mode;
- PlataVM validator failure cannot be promoted to ready state;
- BuoyCalc validator failure or tracked-state mutation cannot be promoted to
  ready state;
- connected-project primary repositories remain protected by existing
  controlled-worktree semantics;
- remote Git mutation/release authority is not introduced.

## Cross-platform validation
Gate-specific workflow:
`.github/workflows/gate029-tool-validator.yml`

The workflow checks out and verifies the exact pull-request head independently
on Ubuntu and Windows, installs the package, and executes:

`python scripts/gate029_tool_validator_acceptance.py`

Final run IDs and exact-head results will be recorded after validation.

## Authority boundaries
- arbitrary shell authority: not granted;
- generic filesystem write/delete authority: not granted;
- remote Git mutation authority: not granted;
- project physics/architecture authority: unchanged;
- validator weakening: prohibited;
- release authorization: `NOT_GRANTED`;
- fabrication authorization: `NOT_GRANTED`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

## Gate state
Implementation is pending exact-head deterministic validation and review.
