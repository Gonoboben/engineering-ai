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
- State: `IMPLEMENTED_PENDING_LOCAL_VALIDATION`

## Architecture / implementation state
- Python package skeleton: `IMPLEMENTED_VALIDATED`
- Gate 002 schemas/semantic validation: `IMPLEMENTED_VALIDATED`
- Deterministic policy engine: `IMPLEMENTED_PENDING_FINAL_VALIDATION`
- Supervisor state machine: `IMPLEMENTED_PENDING_FINAL_VALIDATION`
- Explicit policy outcomes (`ALLOW`, `DENY`, `NEEDS_HUMAN_APPROVAL`): `IMPLEMENTED_PENDING_FINAL_VALIDATION`
- Approval boundary enforcement: `IMPLEMENTED_PENDING_FINAL_VALIDATION`
- Forbidden-action enforcement: `IMPLEMENTED_PENDING_FINAL_VALIDATION`
- Bounded retry handling: `IMPLEMENTED_PENDING_FINAL_VALIDATION`
- Structured audit emission: `IMPLEMENTED_PENDING_FINAL_VALIDATION`
- Fake/stub tool interface: `IMPLEMENTED_PENDING_FINAL_VALIDATION`
- Defensive authoritative-state snapshots: `IMPLEMENTED_PENDING_FINAL_VALIDATION`
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
- local Windows/Python 3.12 validation on current Gate 003 head: `PENDING`
- final exact-head CI after this documentation update: `PENDING`
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
Run the complete deterministic suite locally on the primary Windows/Python 3.12 workstation at the current Gate 003 head, then confirm final exact-head GitHub Actions PASS and complete review of PR #6.

Gate 004 — Tool adapter foundation — is not admissible until Gate 003 is reviewed and merged.
