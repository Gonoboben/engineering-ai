# STATUS.md

## Project
`Gonoboben/engineering-ai`

## Mission
Build a local-first, auditable engineering AI control plane that can safely continue real engineering projects using replaceable AI models plus deterministic tools and validators.

## Current Gate
- Gate: `001 — Architecture baseline and governance`
- Issue: `#1`
- Branch: `gate-001-architecture-baseline`
- State: `IN_REVIEW`

## Architecture state
- Control-plane architecture: `PROPOSED_BASELINE`
- Supervisor: `DESIGNED_NOT_IMPLEMENTED`
- Project state schema: `NOT_IMPLEMENTED`
- Policy engine: `NOT_IMPLEMENTED`
- Audit log: `DESIGNED_NOT_IMPLEMENTED`
- Evidence layer: `DESIGNED_NOT_IMPLEMENTED`
- Model interface: `DESIGNED_NOT_IMPLEMENTED`
- Local model runtime: `NOT_SELECTED`
- Tool adapters: `NOT_IMPLEMENTED`
- Engineering memory: `DESIGNED_NOT_IMPLEMENTED`
- Multi-agent routing: `DEFERRED`
- Vision/image/CAD workers: `DEFERRED`
- External/OpenAI bridge: `OPTIONAL_NOT_IMPLEMENTED`

## Connected engineering projects
- PlataVM: `NOT_CONNECTED`
- BuoyCalc: `NOT_CONNECTED`

No existing project is modified by Gate 001.

## Validation state
- Architecture document consistency review: `PENDING`
- Runtime tests: `NOT_APPLICABLE`
- Model benchmark: `NOT_RUN`
- Supervisor tests: `NOT_RUN`
- Project adapter tests: `NOT_RUN`
- Physical validation: `PHYSICAL_NOT_EXECUTED`

## Global invariants currently proposed
- repository/project state is authoritative, not chat/model memory;
- offline-first operation;
- replaceable models;
- deterministic validators outrank model claims;
- non-LLM Supervisor controls policy and state transitions;
- project repositories remain independent;
- validator weakening is prohibited;
- simulation does not imply physical validation;
- material actions are auditable;
- human approval remains mandatory at defined irreversible/architecture/physics boundaries;
- single-agent core precedes multi-agent expansion.

## Next admissible action after Gate 001
`Gate 002 — Repository skeleton and schemas`, but only after Gate 001 is reviewed and merged.

Gate 002 will define executable package layout and machine-readable schemas; it will not yet select a production local model or modify connected engineering projects.
