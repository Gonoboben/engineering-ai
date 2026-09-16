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
- local checkout `C:\workspace\repos\engineering-ai` synchronized to Gate 001 baseline.

Known platform risk:
Windows build 22000 is an unsupported host OS baseline and cannot currently be updated in the user's environment. This is tracked as a security/platform risk rather than a Gate 002 blocker. Future local network services must default to local-only exposure until explicitly reviewed.

---

## 2026-09-16 — Gate 002 opened and implemented for validation

Issue:
`#3 — Gate 002 — Repository skeleton and machine-readable schemas`

Branch:
`gate-002-repository-skeleton-schemas`

Implemented scope:
- Python package skeleton for Supervisor, model interfaces, tools, project adapters, memory, evidence and audit;
- non-secret configuration boundary;
- `.gitignore` for local virtual environments and runtime artifacts;
- JSON Schema Draft 2020-12 definitions for project profile, project policy, job, project state, evidence and audit event;
- deterministic semantic validation for permission separation, mandatory approval boundaries and retry limits;
- positive and negative fixtures;
- `unittest` validation suite;
- GitHub Actions validation workflow;
- schema documentation.

Model/runtime integration:
`NOT_STARTED`

Connected project access:
`NOT_STARTED`

Current Gate state:
`IMPLEMENTED_PENDING_VALIDATION`
