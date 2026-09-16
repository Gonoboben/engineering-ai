# CHRONOLOGY.md

## 2026-09-16 — Repository bootstrap

Repository `Gonoboben/engineering-ai` created as a private repository.

Bootstrap commit:
`73376bfe41395fd26d574201b8cc06d2b34130c3`

---

## 2026-09-16 — Gate 001 accepted and merged

PR #2 approved at exact head:
`90d2f4dcc8ef78e9b9de75aeb3421480cb428af2`

Squash merge on `main`:
`e10f949a6e860deed2104af770909bae1d043a53`

Architecture state:
`ACCEPTED_BASELINE`

---

## 2026-09-16 — Primary workstation bootstrap

Confirmed environment:
- Windows 11 Pro `10.0.22000`;
- Intel Core i7-11700K;
- 31.9 GB RAM;
- NVIDIA GeForce RTX 3060 Ti, 8192 MiB VRAM;
- NVIDIA driver `591.86`;
- Git `2.55.0.windows.3`;
- GitHub CLI `2.101.0`;
- Python `3.12.10`;
- checkout `C:\workspace\repos\engineering-ai`.

Known platform risk:
Windows build 22000 is unsupported and cannot currently be updated in the user's environment. This remains a tracked platform/security risk, not a current development blocker.

---

## 2026-09-16 — Gate 002 accepted and merged

Issue #3 / PR #4.

Delivered:
- Python package skeleton;
- project/profile/job/state/evidence/audit schemas;
- deterministic semantic validation;
- positive and negative fixtures;
- GitHub Actions test workflow.

Local Windows validation:
- `8` tests;
- result `OK`;
- working tree clean.

Approved PR head:
`33155965b374d9150b55ad528bb801f49043480d`

Squash merge on `main`:
`90df86ceebfb3ee6166a959fcf84172e989c646a`

---

## 2026-09-16 — Gate 003 implemented and validated

Issue #5 / PR #6.

Delivered:
- deterministic policy engine;
- `ALLOW`, `DENY`, `NEEDS_HUMAN_APPROVAL`;
- Supervisor job/state lifecycle;
- named human approval requirement;
- forbidden/undeclared action blocking before tool invocation;
- bounded retries and terminal failure;
- schema-validated audit events;
- defensive authoritative-state snapshots;
- deterministic stub tool interface.

Local Windows/Python 3.12 validation on branch head:
`ad95a1ed0e1ac0346247955da2a5063669a6df29`

Result:
- `18` tests;
- failures `0`;
- errors `0`;
- `OK`;
- working tree `CLEAN`.

Final approved PR head:
`5b078f86f322f16628646cd692465a24a009116e`

Squash merge on `main`:
`bb073ea212676ecc17d50131beee41842bd2eed2`

---

## 2026-09-16 — CI exact-head semantics correction

During Gate 004 review of validation behavior, it was identified that the historical GitHub Actions workflow triggered by `pull_request` used the default GitHub merge-ref checkout. Therefore earlier Gate 002/003 GitHub Actions results validated the PR merge ref rather than strictly checking out the branch-head SHA.

This does not invalidate the independently recorded local Windows branch-head test runs, but the previous use of the term `exact-head CI` was too strong.

Correction:
- a dedicated `.github/workflows/validate-exact-head.yml` workflow was added;
- it explicitly checks out `github.event.pull_request.head.sha`;
- it separately compares `git rev-parse HEAD` with the expected PR head SHA before running tests.

This correction strengthens validation and does not weaken any prior invariant.

---

## 2026-09-16 — Gate 004 opened and implemented for validation

Issue:
`#7 — Gate 004 — Tool adapter foundation`

PR:
`#8 — Gate 004: tool adapter foundation`

Branch:
`gate-004-tool-adapter-foundation`

Implemented scope:
- typed adapter result/error primitives;
- root-bounded read-only filesystem adapter;
- read-size limits;
- parent traversal and symlink escape rejection;
- read-only Git adapter with fixed status/branch/head/log/diff methods;
- no public generic Git command API;
- allow-listed fixed-profile local process runner;
- `shell=False` process launch;
- root-bounded process working directory;
- timeout handling;
- stdout/stderr capture through temporary files with bounded returned output;
- cross-platform deterministic tests.

Explicitly not implemented:
- filesystem writes/deletes;
- Git commit/push/merge/checkout mutation operations;
- arbitrary shell commands;
- project-specific access;
- LLM/runtime integration.

Implementation CI on Linux:
- `28` tests run;
- result `OK`.

Strict exact-head validation workflow on head:
`73c025b5d8676c464beeb059cb5cbc3b0980488e`

Result:
- checkout exact PR head: `PASS`;
- explicit revision equality check: `PASS`;
- package install: `PASS`;
- deterministic tests: `PASS`.

Current Gate state:
`IMPLEMENTED_PENDING_LOCAL_VALIDATION`
