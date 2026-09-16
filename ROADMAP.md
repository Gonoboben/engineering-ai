# ROADMAP.md

## Roadmap policy
The project advances through small auditable Gates. A later Gate must not silently redefine an accepted earlier architecture decision; architecture changes require an explicit architecture Gate and human approval.

## Phase 0 — Governance and control-plane baseline

### Gate 001 — Architecture baseline and governance
Status: `ACCEPTED_MERGED`

Deliverables:
- governance and authority rules;
- control-plane architecture;
- roadmap;
- status/decision/chronology conventions.

Accepted merge commit:
`e10f949a6e860deed2104af770909bae1d043a53`

No runtime/model/tool implementation.

## Phase 1 — Minimal local engineering core

### Gate 002 — Repository skeleton and schemas
Status: `VALIDATION_PASS_PENDING_REVIEW`

Define the executable package layout and machine-readable schemas for:
- project profile;
- policy;
- task/job;
- project state;
- evidence;
- audit event.

Acceptance focus: schemas validate independently of any LLM.

Required Gate 002 evidence:
- JSON Schema Draft 2020-12 syntax validation — `PASS`;
- positive fixture PASS — `PASS`;
- negative permission/state/evidence/audit fixture rejection — `PASS`;
- package/import smoke PASS — `PASS`;
- local Windows/Python 3.12 validation — `PASS`;
- CI confirmation on implementation head `6e9c3d09ac7e690ba514ec9b878cd8dddfc3ac89` — `PASS`;
- final exact-head CI after validation-record documentation — `PENDING`.

### Gate 003 — Deterministic Supervisor core
Status: `NOT_STARTED`

Implement a local Supervisor state machine with:
- policy checks;
- stop/approval transitions;
- bounded retries;
- job lifecycle;
- audit emission.

Use fake/stub agents and tools first.

### Gate 004 — Tool adapter foundation
Implement narrow typed adapters for:
- filesystem/read-only project inspection;
- Git read/status/diff;
- controlled local process execution.

No project-specific writes yet.

### Gate 005 — Local model interface
Add one replaceable local model provider through a stable interface.

Model/runtime selection is made here using measured quality, compatibility and resource constraints on the existing workstation. Do not hard-code model semantics into the Supervisor.

### Gate 006 — Planner / Executor / Reviewer loop
Run one model in separated roles/contexts and require evidence-based completion states.

Acceptance focus: the Supervisor, not the model, controls transitions and permissions.

## Phase 2 — Existing project integration

### Gate 007 — PlataVM read-only adapter
Connect the existing PlataVM repository in read-only mode.

Capabilities:
- resolve governance/status/roadmap documents;
- inspect Git state;
- locate KiCad assets;
- invoke allowed read-only diagnostics/validators.

No project modification.

### Gate 008 — PlataVM controlled engineering loop
Add controlled branch/worktree writes and project-specific policy enforcement.

Mandatory property: existing PlataVM architecture/governance remains authoritative; Engineering AI cannot weaken it.

### Gate 009 — BuoyCalc read-only adapter
Connect BuoyCalc with its calculation-core/physics boundaries and validation semantics.

### Gate 010 — BuoyCalc controlled engineering loop
Enable controlled modifications, build/test/validation runs and structured evidence capture.

## Phase 3 — Persistent engineering memory

### Gate 011 — Decision/evidence memory
Add structured storage/search for:
- ADRs;
- calculations;
- test results;
- failure lessons;
- source references.

Start with simple local storage (repository files/SQLite/search).

### Gate 012 — Retrieval layer
Add semantic/vector retrieval only if benchmarked against repository/search approaches and shown to improve relevant engineering recall without hiding provenance.

### Gate 013 — Knowledge lifecycle
Define promotion rules for observations -> evidence -> accepted project knowledge, including invalidation when source revisions change.

## Phase 4 — Unattended local operation

### Gate 014 — Job queue
Add persisted queued jobs with retry/timeout/approval semantics.

### Gate 015 — Scheduled/overnight engineering runs
Allow unattended processing only for pre-authorized action classes. Produce morning-style summaries with PASS/FAIL/BLOCKED/WAITING_FOR_APPROVAL counts and evidence links.

## Phase 5 — Optional external consultation

### Gate 016 — External reasoning/review bridge
Add a policy-controlled optional OpenAI/external-model consultation path.

Requirements:
- local core remains functional offline;
- outbound project context is explicit;
- calls/results are audited;
- external models never bypass local policy.

### Gate 017 — Controlled MCP/tool exposure
Expose selected local capabilities through a controlled bridge when useful. Keep write authority narrow and reviewable.

## Phase 6 — Multimodal engineering

### Gate 018 — Vision worker
Support schematics/photos/screenshots/plots as structured observations while retaining source provenance.

### Gate 019 — CAD worker
Integrate controlled parametric CAD generation/manipulation with deterministic geometry checks.

### Gate 020 — Image-generation worker
Add concept/visual generation as a non-authoritative design aid. Generated imagery is never treated as an engineering drawing without deterministic reconstruction/validation.

## Phase 7 — Multi-model / specialist routing

### Gate 021 — Model capability registry and router
Benchmark and route bounded tasks by capability/cost/resource availability.

### Gate 022 — Specialist workers
Potential workers: code, electronics, vision, CAD, image, reviewer.

Constraint: all workers share Supervisor-controlled state/evidence interfaces; no unrestricted peer-to-peer swarm.

### Gate 023 — Independent review and consensus policy
Add explicit disagreement handling and evidence-based escalation rather than majority voting between models.

## Phase 8 — Stable engineering platform

### v1.0 criteria
A stable v1.0 requires, at minimum:
- reproducible local installation;
- offline continuation of connected projects;
- tested policy/approval enforcement;
- deterministic tool/validator integration;
- auditable state transitions;
- persistent project memory with provenance;
- successful controlled use on both PlataVM and BuoyCalc;
- documented recovery from model/tool failure;
- model/runtime replaceability demonstrated in practice.
