# CHRONOLOGY.md

## 2026-09-16 — Repository bootstrap

Repository `Gonoboben/engineering-ai` created as a private repository.

A minimal `README.md` bootstrap commit was created on `main` because GitHub cannot create a branch from a repository with no commits.

Bootstrap commit:
`73376bfe41395fd26d574201b8cc06d2b34130c3`

No architecture or implementation baseline was established by that commit.

---

## 2026-09-16 — Gate 001 opened

Issue:
`#1 — Gate 001 — Architecture baseline and governance`

Branch:
`gate-001-architecture-baseline`

Purpose:
Establish governance, system architecture, roadmap, status semantics and foundational decisions before implementing code or selecting a local model runtime.

Key proposed decisions:
- repository/project state is the source of truth instead of model/chat memory;
- use a deterministic non-LLM Supervisor;
- keep AI models replaceable;
- operate offline-first;
- keep PlataVM/BuoyCalc as independent repositories;
- deterministic validation outranks model claims;
- do not weaken validators for PASS;
- keep physical validation distinct from simulation;
- make evidence/provenance and audit first-class;
- establish a stable single-agent core before multi-agent/vision/image/CAD expansion.

Implementation/runtime status:
`NOT_STARTED`

Connected project modification status:
`NONE`

---

## 2026-09-16 — Gate 001 accepted and merged

Human approval was given for squash-merge of PR #2 at exact head:
`90d2f4dcc8ef78e9b9de75aeb3421480cb428af2`

Squash merge result on `main`:
`e10f949a6e860deed2104af770909bae1d043a53`

Architecture state became:
`ACCEPTED_BASELINE`

---

## 2026-09-16 — Primary workstation bootstrap

A previously unused stationary workstation was selected as the future deep-engineering/local-AI host.

Confirmed environment:
- Windows 11 Pro `10.0.22000`;
- Intel Core i7-11700K;
- 31.9 GB RAM;
- NVIDIA GeForce RTX 3060 Ti with 8192 MiB VRAM;
- NVIDIA driver `591.86`;
- Git `2.55.0.windows.3`;
- GitHub CLI `2.101.0`, authenticated as `Gonoboben`;
- Python `3.12.10`;
- local checkout `C:\workspace\repos\engineering-ai`.

Known platform risk:
Windows build 22000 is an unsupported host OS baseline and cannot currently be updated in the user's environment. This is tracked as a security/platform risk rather than a current development blocker. Future local network services must default to local-only exposure until explicitly reviewed.

---

## 2026-09-16 — Gate 002 opened and implemented

Issue:
`#3 — Gate 002 — Repository skeleton and machine-readable schemas`

PR:
`#4 — Gate 002: repository skeleton and machine-readable schemas`

Branch:
`gate-002-repository-skeleton-schemas`

Implemented scope:
- Python package skeleton for Supervisor, model interfaces, tools, project adapters, memory, evidence and audit;
- non-secret configuration boundary;
- `.gitignore` for local virtual environments, `*.egg-info/` and runtime artifacts;
- JSON Schema Draft 2020-12 definitions for project profile, project policy, job, project state, evidence and audit event;
- deterministic semantic validation for permission separation, mandatory approval boundaries and retry limits;
- positive and negative fixtures;
- `unittest` validation suite;
- GitHub Actions validation workflow;
- schema documentation.

Independent local validation on Windows/Python 3.12:
- `8` tests run;
- result `OK`;
- working tree clean.

Final exact-head CI on:
`33155965b374d9150b55ad528bb801f49043480d`

Result:
`PASS`

---

## 2026-09-16 — Gate 002 accepted and merged

Human approval was given for squash-merge of PR #4 at exact head:
`33155965b374d9150b55ad528bb801f49043480d`

Squash merge result on `main`:
`90df86ceebfb3ee6166a959fcf84172e989c646a`

Gate 002 state became:
`ACCEPTED_MERGED`

No model runtime and no connected engineering project access were introduced.

---

## 2026-09-16 — Gate 003 opened

Issue:
`#5 — Gate 003 — Deterministic Supervisor core`

PR:
`#6 — Gate 003: deterministic Supervisor core`

Branch:
`gate-003-deterministic-supervisor`

Purpose:
Implement the first executable non-LLM Supervisor that owns policy decisions, state transitions, bounded retries and audit emission before any local AI model is connected.

Implemented scope:
- deterministic policy engine with `ALLOW`, `DENY`, `NEEDS_HUMAN_APPROVAL` outcomes;
- rule that effective runtime state may tighten but not relax project policy;
- Supervisor job/state lifecycle;
- explicit approval blocking and named-approver requirement;
- forbidden and undeclared action rejection before tool invocation;
- bounded retry handling with terminal failure after exhaustion;
- schema-validated policy, tool and state-transition audit events;
- defensive copies preventing advisory callers from directly mutating authoritative Supervisor state;
- deterministic stub tool interface;
- regression and Supervisor unit tests.

Model/runtime integration:
`NOT_STARTED`

Real tool adapters:
`NOT_STARTED`

Connected project access:
`NOT_STARTED`

---

## 2026-09-16 — Gate 003 implementation-head CI

Implementation head:
`52c32a385bb3772ba3f431eba6d5105624f867ce`

GitHub Actions result:
`PASS`

Validated behavior includes:
- all Gate 002 schema tests remain green;
- autonomous actions execute through the Supervisor;
- forbidden actions never invoke the stub tool;
- approval-required actions wait for named human approval;
- actions not declared by the job are denied;
- retry exhaustion terminates instead of looping indefinitely;
- effective state cannot relax policy-forbidden actions;
- job retry limits cannot exceed project policy;
- external state snapshots cannot mutate authoritative Supervisor state;
- audit events validate against the Gate 002 audit schema;
- identical inputs with fixed clock/ID sources produce identical results.

Current Gate state:
`IMPLEMENTED_PENDING_LOCAL_VALIDATION`

A local Windows/Python 3.12 run and a final exact-head CI after this evidence/status update are still required before Gate 003 can be review-ready.
