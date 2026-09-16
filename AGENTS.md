# AGENTS.md

## Purpose
This repository defines and implements a local-first engineering AI control plane. It orchestrates replaceable AI models, deterministic engineering tools, project-specific policies, persistent project state, evidence, validation, and audit.

## Source of truth
1. Repository state and committed project artifacts are authoritative.
2. Model/chat memory is advisory only and must never be the sole source of project state.
3. Project-specific repositories remain authoritative for their own code, schematics, tests, and history.
4. When sources conflict, stop and surface the conflict instead of silently reconciling it.

## Authority order
For engineering claims, use this order unless a project policy defines a stricter rule:
1. Explicit human-approved architecture and project policy.
2. Measured physical evidence and signed/recorded test results.
3. Deterministic validator/tool output (compiler, tests, ERC/DRC, SPICE/FEM, calculation scripts).
4. Controlled calculations with recorded inputs and assumptions.
5. Source documentation and datasheets.
6. AI/model analysis.

A model claim cannot override a failed deterministic check or physical evidence.

## Global invariants
- Offline-first operation is a primary requirement.
- The AI model is replaceable; no core project state may live only inside model context or model weights.
- A non-LLM Supervisor enforces permissions, state transitions, stop conditions, retries, and audit.
- Validators must never be weakened, bypassed, hidden, or reinterpreted merely to obtain PASS.
- Simulation/synthetic/calculation PASS must never be represented as physical validation.
- All material actions must be attributable and auditable.
- Existing project repositories are connected through adapters/profiles; their contents are not duplicated into this control-plane repository unless explicitly required.
- Multi-agent specialization is deferred until the single-agent core is stable and measurable.

## Human approval required
Stop before any of the following unless the active project policy explicitly grants narrower pre-approval:
- architecture changes;
- physics/model-semantic changes;
- safety-critical design decisions without sufficient evidence;
- destructive or irreversible actions;
- production/fabrication/release authorization;
- publication or external disclosure;
- validator/CI/ERC/DRC/test weakening or suppression;
- actions outside the declared task scope;
- unresolved conflicts between authoritative sources.

## Autonomous actions allowed by default
Subject to project policy, the Supervisor may permit:
- read-only inspection of repositories and local documentation;
- local search/indexing;
- calculations and simulations;
- compiler, unit/integration test, ERC/DRC, SPICE/FEM and other validation runs;
- generation of proposed patches in a working branch;
- local commits when the project policy permits them;
- status, chronology, evidence and audit updates;
- repeated diagnose/fix/retest loops that do not cross a stop condition.

## Development workflow for this repository
Use one Gate -> one Issue -> one branch -> one PR for material changes.

A Gate must define:
- objective and scope;
- explicit out-of-scope items;
- acceptance criteria;
- required validation/evidence;
- stop conditions where applicable.

Do not mix unrelated architecture, implementation, model-selection, and project-adapter changes into the same Gate.

## Validation semantics
Use explicit states rather than ambiguous success language:
- `PASS`: the named deterministic check passed for the recorded inputs/revision.
- `FAIL`: the named deterministic check failed.
- `NOT_RUN`: the check was not executed.
- `NOT_APPLICABLE`: the check does not apply.
- `PHYSICAL_NOT_EXECUTED`: no physical validation was performed.
- `NEEDS_HUMAN_APPROVAL`: a policy boundary was reached.

Never infer one validation class from another.

## Model behavior
Models may propose, analyze, plan, review, and call permitted tools through the Supervisor. Models must not:
- directly own permissions;
- directly redefine policy;
- silently mutate project state;
- treat confidence as evidence;
- fabricate tool results, test results, citations, files, commits, or measurements;
- continue through a human-approval boundary.

## Project adapters
Each connected engineering project will define its own profile/policy/tool configuration. Project policy may be stricter than this file but must not silently weaken global invariants.

## Audit requirement
For each material operation, retain enough information to reconstruct:
- timestamp;
- actor/model/runtime identity;
- task or Gate;
- relevant repository/ref before the action;
- tool/action requested;
- result and validation state;
- files/state changed;
- repository/ref after the action;
- evidence references;
- whether human approval was required and obtained.
