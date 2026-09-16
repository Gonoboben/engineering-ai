# STATUS.md

## Project
`Gonoboben/engineering-ai`

## Mission
Build a local-first, auditable engineering AI control plane that can safely continue real engineering projects using replaceable AI models plus deterministic tools and validators.

## Accepted baseline
- Gate 001: `ACCEPTED_MERGED`
- Gate 001 merge commit: `e10f949a6e860deed2104af770909bae1d043a53`
- Gate 002: `ACCEPTED_MERGED`
- Gate 002 merge commit: `90df86ceebfb3ee6166a959fcf84172e989c646a`
- Control-plane architecture: `ACCEPTED_BASELINE`
- Human architecture approval: `APPROVED`

## Current Gate
- Gate: `003 — Deterministic Supervisor core`
- Issue: `#5`
- PR: `#6`
- Branch: `gate-003-deterministic-supervisor`
- State: `VALIDATION_PASS_PENDING_FINAL_EXACT_HEAD_CI_AND_REVIEW`

## Architecture / implementation state
- Python package skeleton: `IMPLEMENTED_VALIDATED`
- Gate 002 schemas/semantic validation: `IMPLEMENTED_VALIDATED`
- Deterministic policy engine: `IMPLEMENTED_VALIDATED`
- Supervisor state machine: `IMPLEMENTED_VALIDATED`
- Explicit policy outcomes (`ALLOW`, `DENY`, `NEEDS_HUMAN_APPROVAL`): `IMPLEMENTED_VALIDATED`
- Approval boundary enforcement: `IMPLEMENTED_VALIDATED`
- Forbidden-action enforcement: `IMPLEMENTED_VALIDATED`
- Bounded retry handling: `IMPLEMENTED_VALIDATED`
- Structured audit emission: `IMPLEMENTED_VALIDATED`
- Fake/stub tool interface: `IMPLEMENTED_VALIDATED`
- Defensive authoritative-state snapshots: `IMPLEMENTED_VALIDATED`
- Real filesystem/Git/process tool adapters: `NOT_IMPLEMENTED` (Gate 004)
- Model interface runtime: `DESIGNED_NOT_IMPLEMENTED`
- Local model runtime: `NOT_SELECTED`
- Engineering memory runtime: `DESIGNED_NOT_IMPLEMENTED`
- Multi-agent routing: `DEFERRED`
- Vision/image/CAD workers: `DEFERRED`
- External/OpenAI bridge: `OPTIONAL_NOT_IMPLEMENTED`

## Connected engineering projects
- PlataVM: `NOT_CONNECTED`
- BuoyCalc: `NOT_CONNECTED`

Gate 003 does not access or modify either engineering project.

## Gate 002 validation state
- schema syntax: `PASS`
- positive fixtures: `PASS`
- negative fixture rejection: `PASS`
- package/import smoke: `PASS`
- local Windows/Python 3.12 validation: `PASS`
- final exact-head GitHub Actions on `33155965b374d9150b55ad528bb801f49043480d`: `PASS`
- human merge approval: `PASS`
- squash merge: `PASS`

## Gate 003 validation state
- existing Gate 002 schema suite regression: `PASS`
- Supervisor policy/state tests on implementation head `52c32a385bb3772ba3f431eba6d5105624f867ce`: `PASS`
- approval-boundary tests: `PASS`
- forbidden-action tests: `PASS`
- retry-exhaustion tests: `PASS`
- audit schema validation: `PASS`
- deterministic repeatability test: `PASS`
- authoritative-state mutation protection test: `PASS`
- GitHub Actions on implementation head `52c32a385bb3772ba3f431eba6d5105624f867ce`: `PASS`
- GitHub Actions on documentation head `ad95a1ed0e1ac0346247955da2a5063669a6df29`: `PASS`
- local Windows/Python 3.12 validation on `ad95a1ed0e1ac0346247955da2a5063669a6df29`: `PASS`
- local tests run: `18`; result: `OK`; working tree: `CLEAN`
- final exact-head CI after this validation-record commit: `PENDING`
- physical validation: `PHYSICAL_NOT_EXECUTED`

## Primary workstation status
- host: Windows 11 Pro build `10.0.22000` (`KNOWN_PLATFORM_RISK`, not a current blocker)
- Git: `2.55.0.windows.3`
- GitHub CLI: `2.101.0`, authenticated as `Gonoboben`
- Python: `3.12.10`
- NVIDIA GPU: `GeForce RTX 3060 Ti, 8192 MiB`
- repository checkout: `C:\workspace\repos\engineering-ai`
- local `.venv`: present and ignored by Git
- editable-install metadata `*.egg-info/`: ignored by Git

Security constraint for future local services:
default to loopback/local-only exposure until an explicit network-security decision permits broader access.

## Global invariants
- repository/project state is authoritative, not chat/model memory;
- offline-first operation;
- replaceable models;
- deterministic validators outrank model claims;
- non-LLM Supervisor controls policy and state transitions;
- runtime state may tighten project policy but may not relax it;
- project repositories remain independent;
- validator weakening for PASS is prohibited;
- simulation does not imply physical validation;
- material actions are auditable;
- human approval remains mandatory at defined irreversible/architecture/physics boundaries;
- single-agent core precedes multi-agent expansion.

## Next admissible action
Confirm final exact-head GitHub Actions PASS for the head containing this local-validation record, complete PR #6 consistency review, and mark PR #6 ready for human merge approval.

Gate 004 — Tool adapter foundation — is not admissible until Gate 003 is reviewed and merged.
