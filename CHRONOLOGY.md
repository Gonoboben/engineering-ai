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

## 2026-09-16 — Gate 004 implemented and validated

Issue #7 / PR #8.

Delivered:
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
- bounded stdout/stderr capture;
- strict exact-PR-head CI workflow.

Local Windows/Python 3.12 validation on branch head:
`aea2921caad82b6792e3d6adb3eb7518f2b89afd`

Result:
- `28` tests;
- failures `0`;
- errors `0`;
- `OK`;
- working tree `CLEAN`.

Final strict exact-head CI on approved PR head:
`0fa74070764587e3959a15afa0148491fb6a944e`

Result:
`PASS`.

Human approval was given for squash-merge of PR #8 at the same exact head.

Squash merge on `main`:
`bc950ded14487b0de90e9209589486fe6bfd83f2`

Gate 004 state became:
`ACCEPTED_MERGED`.

---

## 2026-09-16 — Gate 005 opened and interface implemented

Issue #9 / draft PR #10.

Branch:
`gate-005-local-model-interface`

Purpose:
Add one replaceable local model provider behind a stable interface and select the first local engineering model using measured workstation evidence rather than public benchmark claims alone.

Implemented:
- provider-neutral model message/request/response/metrics/tool-call types;
- replaceable `ModelProvider` protocol;
- loopback-only Ollama provider using `localhost`, `127.0.0.1`, or `::1` only;
- structured-output transport;
- tool-call proposal transport without tool execution;
- Ollama runtime version/resource diagnostics;
- provider-neutral benchmark harness;
- reproducible synthetic benchmark command;
- machine-scored electrical, validation-semantics, and tool-proposal cases;
- deterministic provider/harness tests.

Implementation exact head:
`19d136a0b2a1b82385f31125d6d530d6d53fb3bc`

Strict exact-head GitHub Actions result:
- expected SHA equals actual checkout SHA: `PASS`;
- total deterministic tests: `34`;
- failures: `0`;
- errors: `0`;
- result: `OK`.

---

## 2026-09-16 — Gate 005 primary workstation interface/runtime baseline

Local branch head:
`19d136a0b2a1b82385f31125d6d530d6d53fb3bc`

Local Windows/Python 3.12 result:
- editable package installation: `PASS`;
- deterministic tests: `34/34 PASS`;
- Git working tree: `CLEAN`.

Ollama runtime baseline:
- Ollama version: `0.34.1`;
- local API `/api/version`: `0.34.1`, `PASS`;
- host: `127.0.0.1:11434`;
- model storage: `C:\workspace\models\ollama`;
- parallel requests: `1`;
- max loaded models: `1`;
- context baseline: `8192` tokens;
- cloud functions disabled: `OLLAMA_NO_CLOUD=1`;
- model process list before download/load: empty, expected;
- NVIDIA GeForce RTX 3060 Ti visible with `8192 MiB` VRAM.

Current candidate plan, rechecked against current Ollama registry:
- Candidate A: `gpt-oss:20b`, ~14 GB;
- Candidate B: `qwen3.6:27b-q4_K_M`, ~17 GB;
- stretch candidate: `qwen3.6:35b`, ~23 GB, deferred pending measured memory margin.

Next step:
Download and benchmark Candidate A first. Record local CPU/GPU split, memory/resource state, latency/throughput, structured-output behavior, tool-call proposal behavior and machine-scored engineering results before Candidate B is tested under identical settings.
