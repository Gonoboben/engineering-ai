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
