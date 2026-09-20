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
Status: `ACCEPTED_MERGED`

Implement:
- typed model/runtime identity;
- qualification state;
- accepted role classes;
- resource envelope;
- measured evidence references;
- deterministic Supervisor-owned task classification and routing.

The model cannot grant itself a role, choose a broader tool surface, or bypass policy.

### Gate 010 — Task Blackboard and supervised model hand-offs
Status: `ACCEPTED_MERGED`

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
Status: `ACCEPTED_MERGED`

Add controlled second-model review and explicit disagreement handling.

Resolution order:
- deterministic verification where available;
- bounded independent review;
- bounded revision;
- human escalation when evidence cannot resolve the conflict.

Majority voting between models never substitutes for evidence.

## Phase 3 — Existing project integration

### Gate 012 — PlataVM read-only adapter
Status: `ACCEPTED_MERGED`

Connect the existing PlataVM repository in read-only mode.

Capabilities:
- resolve governance/status/roadmap documents;
- inspect Git state;
- locate KiCad assets;
- invoke allowed read-only diagnostics/validators.

No project modification.

### Gate 013 — PlataVM controlled engineering loop
Status: `ACCEPTED_MERGED`

Add controlled branch/worktree writes and project-specific policy enforcement.

Mandatory property: existing PlataVM architecture/governance remains authoritative; Engineering AI cannot weaken it.

### Gate 014 — BuoyCalc read-only adapter
Status: `ACCEPTED_MERGED`

Connect BuoyCalc with its calculation-core/physics boundaries and validation semantics.

### Gate 015 — BuoyCalc controlled engineering loop
Status: `ACCEPTED_MERGED`

Enable controlled modifications, build/test/validation runs and structured evidence capture.

## Phase 4 — Persistent engineering memory

### Gate 016 — Decision/evidence memory
Status: `ACCEPTED_MERGED`

Add structured storage/search for:
- ADRs;
- calculations;
- test results;
- failure lessons;
- source references.

Start with simple local storage (repository files/SQLite/search).

### Gate 017 — Retrieval layer
Status: `ACCEPTED_MERGED`

Accepted merge commit:
`f416799ca95f3bbe124b7bbfa62a86c1be0d1cbc`

Delivered deterministic provenance-preserving lexical retrieval over Gate 016 memory. The measured primary-workstation benchmark improved mean recall@3 from `0.25` to `1.0` while preserving safety/provenance. Semantic/vector retrieval remains `DEFERRED_NOT_JUSTIFIED`.

### Gate 018 — Knowledge lifecycle
Status: `ACCEPTED_MERGED`

Accepted merge commit:
`75ee907446e952fbfc8a53006c1fd65f1257faea`

Delivered a deterministic append-only lifecycle over Gate 016 memory:
`OBSERVATION -> EVIDENCE -> ACCEPTED -> INVALIDATED`, with exact source/evidence revision binding, stale detection and requalification while preserving history.

## Phase 5 — Unattended local operation

### Gate 019 — Job queue
Status: `ACCEPTED_MERGED`

Accepted merge commit:
`f8e4a6c7893c67bbc81c98bb89698ab6b91553c7`

Delivered a persisted append-only Supervisor-owned job queue with deterministic FIFO claim, bounded retry persistence, explicit timeout/deadline handling, WAITING_FOR_APPROVAL persistence, fail-closed interrupted-run recovery and full predecessor-chain integrity.

### Gate 020 — Scheduled/overnight engineering runs
Status: `ACCEPTED_MERGED`

Accepted merge commit:
`5e4fb761ed4f7c8730b1ddf9acc3d0a842751e35`

Delivered persisted one-shot due schedules and bounded unattended sessions with current-policy re-authorization, no automatic approvals, fail-closed restart behavior and deterministic summaries.

## Phase 6 — Optional external consultation and control

### Gate 021 — External controlled reasoning/review bridge
Status: `ACCEPTED_MERGED`

Accepted merge commit:
`992b2ac07ea1a192919be286eef026a2fa255e73`

Delivered a provider-neutral, policy-controlled external advisory-review bridge with explicit bounded disclosure manifests, named approval enforcement, metadata-only append-only audit, zero local tool authority and ADVISORY-only response semantics.

### Gate 022 — Controlled MCP/tool exposure
Status: `ACCEPTED_MERGED`

Accepted merge commit:
`3111a1d793c05ead0292839500e698a9c5fe2c56`

Delivered a transport-neutral immutable registered-capability broker with dual `external_disclosure` + mapped-action policy checks, explicit file allow-lists, named approvals, bounded schemas/budgets, metadata-only append-only audit, and no generic shell/filesystem-write/Git-mutation authority.

## Phase 7 — Multimodal engineering

### Gate 023 — Vision worker
Status: `ACCEPTED_MERGED`

Accepted merge commit:
`f3c826a434eca8e5d7163f5cf4166560717bdbc2`

Delivered a bounded provenance-preserving Vision-worker boundary for explicit
PNG/JPEG/WebP inputs, inline-only loopback transport, deterministic
qualification-gated Vision routing, exact source-ref constrained structured
observations and ADVISORY-only result semantics.

The accepted registry intentionally contains no production Vision model until
separate measured local qualification evidence exists; therefore the default
Vision route is `NO_ROUTE`.

Final approved PR head:
`880a8d4fce352e5c614254119192d7bf7d283e27`.

Final validation:
- deterministic regression: `280/280 PASS`;
- generic CI `35529619290`: `PASS`;
- strict exact-head CI `35529619244`: `PASS`;
- smoke: `PASS_PROVENANCE_PRESERVING_VISION_BOUNDARY`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

ADR-0022: `ACCEPTED_GATE_023`.

### Gate 024 — CAD worker
Status: `ACCEPTED_MERGED`

Accepted merge commit:
`99a8e216dc2c8ec7b98c445f0e1909479bff6b52`

Delivered a bounded proposal-only parametric CAD worker with typed millimetre
box/cylinder primitives, deterministic design SHA-256, analytical volume/AABB
checks, Supervisor-owned `propose_patch` authority, fixed data-only
FreeCADCmd helper and root-bounded FCStd publication only after deterministic
runtime geometry agreement.

Final approved PR head:
`8330aa62964ec2f9b38873b69a7591a44e1fa5a4`.

Final validation:
- deterministic regression: `289/289 PASS`;
- generic CI `35531166350`: `PASS`;
- strict exact-head CI `35531166349`: `PASS`;
- smoke: `PASS_CONTROLLED_PARAMETRIC_CAD_BOUNDARY`;
- real FreeCAD workstation smoke: `NOT_RUN`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

ADR-0023: `ACCEPTED_GATE_024`.

### Gate 025 — Image-generation worker
Status: `ACCEPTED_MERGED`

Accepted merge commit:
`171ff20125389d2d953576a0d3340c13dc1dc53f`

Final approved PR head:
`eca63b5c28ea908c6cb43900aa97909d0fb289bc`

Delivered bounded local text-to-image concept generation with explicit
evidence-qualified routing, existing Supervisor `propose_patch` authority,
deterministic PNG validation and root-bounded publication. Generated imagery
remains `ADVISORY_CONCEPT_ONLY`, `evidence_eligible=false`,
`engineering_drawing=false`.

Final validation:
- deterministic regression: `301/301 PASS`;
- generic workflow `35532035872`: `PASS`;
- strict exact-head workflow `35532035537`: `PASS`;
- smoke: `PASS_NON_AUTHORITATIVE_IMAGE_GENERATION_BOUNDARY`;
- production image-generation model/provider: `NOT_QUALIFIED`;
- default accepted route: `NO_ROUTE`;
- real provider call: `NOT_RUN`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

ADR-0024: `ACCEPTED_GATE_025`.

## Phase 8 — Stable engineering platform

### Gate 026 — Reproducible local installation
Status: `IMPLEMENTED_VALIDATED_PENDING_HUMAN_APPROVAL`

Issue: `#51`

PR: `#52 (DRAFT; implementation validated)`

Branch: `gate-026-reproducible-local-installation`

Base: Gate 025 squash merge
`171ff20125389d2d953576a0d3340c13dc1dc53f`.

Validated implementation head:
`6c7bfbd9f8d07b96adeb3014b2071a4bc8a0793e`.

Delivered:
- documented Python 3.12.x install contract;
- exact frozen runtime and install-tool dependency sets;
- clean fresh-venv bootstrap;
- non-editable wheel install;
- repeated wheel SHA-256 equality check per platform;
- installed package/version/schema verification;
- `pip check`;
- full installed-package deterministic regression;
- Ubuntu and Windows acceptance workflow.

Implementation validation:
- deterministic installed-package regression:
  `306/306 PASS` on Ubuntu;
- deterministic installed-package regression:
  `306/306 PASS` on Windows;
- generic workflow `35535616430`: `PASS`;
- strict exact-head workflow `35535616425`: `PASS`;
- Gate 026 install workflow `35535616417`:
  Ubuntu `PASS`, Windows `PASS`.

Gate 026 establishes the reproducible-local-installation criterion only.
Offline dependency acquisition and offline continuation remain separate Phase 8
criteria and are not inferred from this PASS.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

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
