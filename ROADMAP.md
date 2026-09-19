# ROADMAP.md

## Roadmap policy
The project advances through small auditable Gates. A later Gate must not silently redefine an accepted earlier architecture decision; architecture changes require an explicit architecture Gate and human approval.

## Phase 0 — Governance and control-plane baseline

### Gate 001 — Architecture baseline and governance
Status: `ACCEPTED_MERGED`

Accepted merge commit:
`e10f949a6e860deed2104af770909bae1d043a53`

Delivered:
- governance and authority rules;
- control-plane architecture;
- roadmap;
- status/decision/chronology conventions.

### Gate 002 — Repository skeleton and schemas
Status: `ACCEPTED_MERGED`

Accepted merge commit:
`90df86ceebfb3ee6166a959fcf84172e989c646a`

Delivered:
- executable Python package skeleton;
- machine-readable project profile, policy, job, state, evidence and audit schemas;
- deterministic semantic validation;
- positive/negative fixtures;
- local and CI validation independent of any LLM.

## Phase 1 — Minimal local engineering core

### Gate 003 — Deterministic Supervisor core
Status: `ACCEPTED_MERGED`

Accepted merge commit:
`bb073ea212676ecc17d50131beee41842bd2eed2`

Delivered:
- deterministic policy checks;
- `ALLOW`, `DENY`, `NEEDS_HUMAN_APPROVAL` outcomes;
- stop/approval transitions;
- bounded retries;
- job lifecycle;
- schema-validated audit emission;
- defensive authoritative-state snapshots;
- fake/stub tools only.

Validation note:
Gate 003 local Windows/Python 3.12 validation ran on the stated branch head and passed `18/18`. The historical PR workflow used GitHub's default pull-request merge-ref checkout; strict CI branch-head verification was added during Gate 004.

### Gate 004 — Tool adapter foundation
Status: `ACCEPTED_MERGED`

Accepted merge commit:
`bc950ded14487b0de90e9209589486fe6bfd83f2`

Delivered:
- root-bounded read-only filesystem inspection;
- fixed read-only Git status/branch/head/log/diff operations;
- allow-listed fixed-profile local process execution;
- `shell=False` process execution;
- timeouts;
- bounded stdout/stderr capture;
- root-bounded working directories;
- strict exact-PR-head CI workflow with explicit SHA verification.

Validation:
- Linux/CI suite — `28/28 PASS`;
- local Windows/Python 3.12 — `28/28 PASS`;
- strict exact-head final PR validation — `PASS`.

No project-specific writes or project access.

### Gate 005 — Local model interface
Status: `ACCEPTED_MERGED`

Implemented:
- provider-neutral request/response/message/tool-call types;
- replaceable `ModelProvider` protocol;
- loopback-only Ollama provider;
- structured-output transport;
- tool-call proposal transport without tool execution;
- runtime metrics/resource diagnostics;
- reproducible benchmark harness and candidate-selection evidence format;
- ASCII-safe JSON evidence output for Windows legacy code pages;
- explicit generation-budget and `done_reason` evidence;
- truncation represented as `INCONCLUSIVE` rather than deterministic failure;
- provider timeout preserved as evidence instead of aborting the entire benchmark package.

Validated baseline:
- strict exact-head CI on implementation head — `34/34 PASS`;
- local Windows/Python 3.12 suite — `34/34 PASS`;
- Ollama `0.34.1` installed and reachable at `127.0.0.1:11434`;
- local model directory fixed to `C:\workspace\models\ollama`;
- cloud disabled;
- one loaded model / one parallel request policy fixed for baseline measurements;
- benchmark context baseline fixed at `8192` tokens;
- RTX 3060 Ti 8 GB visible to the runtime environment.

Measured benchmark candidates:
- Candidate A: `gpt-oss:20b`, MXFP4, ~14 GB package — `4/4 PASS` at `reasoning=medium`; processor split `57% CPU / 43% GPU`; active free RAM ~`16.3 GB`;
- Candidate A diagnostic: `reasoning=high` reproduced `2 PASS + 2 INCONCLUSIVE_TRUNCATED` in two independent runs, so `high` is not the default baseline;
- Candidate B: `qwen3.6:27b-q4_K_M`, 27.8B Q4_K_M, ~17 GB — `3 PASS + 1 INCONCLUSIVE_TRUNCATED`, no deterministic FAIL; processor split `69% CPU / 31% GPU`; ~`2.45–2.55 eval tokens/s`; ~`37.7 min` aggregate benchmark time;
- Stretch: `qwen3.6:35b` — deferred/not justified on the current workstation after the measured 27B CPU-heavy performance.

Initial model selection:
- selected model: `gpt-oss:20b`;
- selected baseline reasoning: `medium`;
- baseline context: `8192`;
- selection evidence: `docs/evidence/gate005/model-selection.md`.

Final acceptance:
- final Gate 005 head: `9d6677290ee5bbaf0253234c7b8d479c6a3f948e`;
- local Windows regression: `39/39 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- explicit exact-SHA human approval: `PASS`;
- squash merge commit: `ddf6fd9420bc60d3d812a17b948f7319e2cb63cd`.

Do not hard-code model-family semantics into Supervisor behavior.

### Gate 006 — Planner / Executor / Reviewer loop
Status: `ACCEPTED_MERGED`

Implemented:
- typed Planner / Executor / Reviewer roles and results;
- explicit deterministic role-loop state machine;
- separate role prompts/contexts using one replaceable model provider;
- approved-plan-only Executor context;
- inert model tool proposals routed through the existing deterministic Supervisor;
- deterministic evidence requirement before review/completion;
- Reviewer outcomes `ACCEPT / REVISE / REJECT / NEEDS_HUMAN_APPROVAL`;
- bounded revision behavior;
- explicit terminal failure and human-approval boundaries;
- model role/runtime audit identity;
- narrow read-only local smoke harness for `gpt-oss:20b / medium / 8192 / 2048`.

Deterministic validation:
- Gate 002–005 regression remains `PASS`;
- implementation head `61f8bc469e3ab827749d7a94a6a393e5715a237a`: `46/46 PASS`;
- generic CI on that head: `PASS`;
- strict exact-head CI on that head: `PASS`.

Acceptance evidence:
- local runtime smoke on primary workstation at head `f3c434e630a10bbf016e28d6c873df4f79783c28`: `PASS`;
- result: `COMPLETE / PASS`, bounded `read_repository`, SHA-256 evidence for `STATUS.md`, Reviewer `ACCEPT`;
- physical validation remains `PHYSICAL_NOT_EXECUTED`.

Final acceptance:
- final PR head: `04d3f7653471b8bb8db7f90d939e55b122bfc1c1`;
- deterministic tests: `50/50 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`;
- squash merge commit: `24b1fbc009920c1dee8317c784ef42711044be87`.

Acceptance focus remains: the Supervisor, not the model, controls transitions and permissions.

## Phase 2 — Supervised multi-model foundation

### Gate 007 — Supervised multi-model architecture baseline
Status: `ACCEPTED_MERGED`

Issue:
`#13`

Purpose:
freeze the architecture for multiple specialized local models without changing the deterministic authority model.

Defines:
- Supervisor-mediated multi-model workers;
- Model Capability Registry semantics;
- deterministic Model Router authority;
- Task Blackboard semantics;
- evidence-based disagreement handling;
- optional external-control boundary;
- candidate roles for Qwen3.5-9B, Qwen2.5-Coder-7B, gpt-oss:20b and later reviewer candidates.

No model download, model qualification, router code, Blackboard runtime, project adapter, or external bridge implementation belongs in this Gate.

### Gate 008 — Local specialist model qualification
Status: `ACCEPTED_MERGED`

Qualify practical local candidates on the primary workstation before assigning production roles.

Initial candidates:
- `Qwen3.5-9B` — general/Planner and future multimodal candidate;
- `Qwen2.5-Coder-7B` — code/repository specialist candidate;
- `gpt-oss:20b / medium` — retained accepted baseline/reference.

Optional comparison:
- `Huihui Qwen3 14B` for independent critique/review.

27B-class downloads are not required unless later evidence justifies them.

Required measurements:
- deterministic engineering/math cases;
- structured JSON reliability;
- inert tool proposal behavior;
- code analysis/repair cases;
- role-specific Planner/Reviewer cases;
- latency and eval throughput;
- CPU/GPU placement;
- VRAM/RAM use;
- truncation/timeout behavior;
- failure/retry behavior.

Public benchmark/model-card claims are advisory; local measured evidence determines qualification.

### Gate 009 — Model capability registry and deterministic router
Status: `IMPLEMENTED_VALIDATED_PENDING_HUMAN_APPROVAL`

Implement:
- typed model/runtime identity;
- qualification state;
- accepted role classes;
- resource envelope;
- measured evidence references;
- deterministic Supervisor-owned task classification and routing.

The model cannot grant itself a role, choose a broader tool surface, or bypass policy.

### Gate 010 — Task Blackboard and supervised model hand-offs
Status: `NOT_STARTED`

Implement typed, bounded inter-worker exchange for:
- task assignment;
- plans;
- model claims;
- open questions;
- proposed actions;
- deterministic evidence references;
- review findings;
- approvals;
- terminal state.

No unrestricted peer-to-peer model messaging.
Writing a model claim to the Blackboard does not promote it to evidence.

### Gate 011 — Independent review and disagreement escalation
Status: `NOT_STARTED`

Add controlled second-model review and explicit disagreement handling.

Resolution order:
- deterministic verification where available;
- bounded independent review;
- bounded revision;
- human escalation when evidence cannot resolve the conflict.

Majority voting between models never substitutes for evidence.

## Phase 3 — Existing project integration

### Gate 012 — PlataVM read-only adapter
Status: `NOT_STARTED`

Connect the existing PlataVM repository in read-only mode.

Capabilities:
- resolve governance/status/roadmap documents;
- inspect Git state;
- locate KiCad assets;
- invoke allowed read-only diagnostics/validators.

No project modification.

### Gate 013 — PlataVM controlled engineering loop
Status: `NOT_STARTED`

Add controlled branch/worktree writes and project-specific policy enforcement.

Mandatory property: existing PlataVM architecture/governance remains authoritative; Engineering AI cannot weaken it.

### Gate 014 — BuoyCalc read-only adapter
Status: `NOT_STARTED`

Connect BuoyCalc with its calculation-core/physics boundaries and validation semantics.

### Gate 015 — BuoyCalc controlled engineering loop
Status: `NOT_STARTED`

Enable controlled modifications, build/test/validation runs and structured evidence capture.

## Phase 4 — Persistent engineering memory

### Gate 016 — Decision/evidence memory
Status: `NOT_STARTED`

Add structured storage/search for:
- ADRs;
- calculations;
- test results;
- failure lessons;
- source references.

Start with simple local storage (repository files/SQLite/search).

### Gate 017 — Retrieval layer
Status: `NOT_STARTED`

Add semantic/vector retrieval only if benchmarked against repository/search approaches and shown to improve relevant engineering recall without hiding provenance.

### Gate 018 — Knowledge lifecycle
Status: `NOT_STARTED`

Define promotion rules for observations -> evidence -> accepted project knowledge, including invalidation when source revisions change.

## Phase 5 — Unattended local operation

### Gate 019 — Job queue
Status: `NOT_STARTED`

Add persisted queued jobs with retry/timeout/approval semantics.

### Gate 020 — Scheduled/overnight engineering runs
Status: `NOT_STARTED`

Allow unattended processing only for pre-authorized action classes. Produce summaries with PASS/FAIL/BLOCKED/WAITING_FOR_APPROVAL counts and evidence links.

## Phase 6 — Optional external consultation and control

### Gate 021 — External controlled reasoning/review bridge
Status: `NOT_STARTED`

Add a policy-controlled optional bridge for ChatGPT/OpenAI or another external reviewer/architect.

Requirements:
- local core remains functional offline;
- outbound project context is explicit and policy-controlled;
- calls/results are audited;
- external models never bypass local Supervisor policy, approvals, or evidence semantics;
- no unrestricted shell/filesystem authority is exposed.

### Gate 022 — Controlled MCP/tool exposure
Status: `NOT_STARTED`

Expose selected local capabilities through a controlled bridge when useful. Keep write authority narrow, typed, policy-gated, and reviewable.

## Phase 7 — Multimodal engineering

### Gate 023 — Vision worker
Status: `NOT_STARTED`

Support schematics/photos/screenshots/plots as structured observations while retaining source provenance.

### Gate 024 — CAD worker
Status: `NOT_STARTED`

Integrate controlled parametric CAD generation/manipulation with deterministic geometry checks.

### Gate 025 — Image-generation worker
Status: `NOT_STARTED`

Add concept/visual generation as a non-authoritative design aid. Generated imagery is never treated as an engineering drawing without deterministic reconstruction/validation.

## Phase 8 — Stable engineering platform

### v1.0 criteria
A stable v1.0 requires, at minimum:
- reproducible local installation;
- offline continuation of connected projects;
- tested policy/approval enforcement;
- deterministic tool/validator integration;
- auditable state transitions;
- measured and replaceable multi-model routing;
- controlled model-to-model hand-offs with provenance;
- persistent project memory with provenance;
- successful controlled use on both PlataVM and BuoyCalc;
- documented recovery from model/tool failure;
- model/runtime replaceability demonstrated in practice.
