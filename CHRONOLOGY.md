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

---

## 2026-09-17 — Gate 005 measured model selection

Candidate A measurement:
- model: `gpt-oss:20b`, MXFP4;
- baseline: context `8192`, max output `2048`, reasoning `medium`;
- result: `4/4 PASS`;
- processor split: `57% CPU / 43% GPU`;
- active VRAM observed: ~`7.38 GB`;
- free system RAM during run: ~`16.3 GB`;
- aggregate benchmark wall time: ~`49.9 s`.

Candidate A `high` diagnostic:
- repeated twice independently;
- each run produced `2 PASS + 2 INCONCLUSIVE_TRUNCATED`;
- both affected structured-output cases exhausted exactly `2048` generation tokens;
- `high` is therefore not accepted as the default baseline for this model.

Candidate B measurement:
- model: `qwen3.6:27b-q4_K_M`, 27.8B Q4_K_M;
- baseline: context `8192`, max output `2048`, reasoning `medium`;
- result: `3 PASS + 1 INCONCLUSIVE_TRUNCATED`, deterministic FAIL `0`;
- processor split: `69% CPU / 31% GPU`;
- active VRAM observed: ~`7.62 GB`;
- free system RAM during run: ~`12.8–13.4 GB`;
- throughput: ~`2.45–2.55 eval tokens/s`;
- aggregate benchmark wall time: ~`37.7 min`;
- model remained memory-stable but was operationally too slow for the primary interactive role on the current workstation.

Selection:
- initial local engineering model: `gpt-oss:20b`;
- baseline reasoning level: `medium`;
- runtime: Ollama `0.34.1`;
- context baseline: `8192`;
- benchmark-equivalent max output: `2048`.

Selection rationale and raw evidence are recorded under `docs/evidence/gate005/`.

Gate 005 state became:
`MODEL_SELECTED_PENDING_FINAL_VALIDATION`.

Next step:
Run the final local Windows regression suite on the final Gate 005 head and confirm strict exact-head CI on the same head before requesting explicit exact-SHA squash-merge approval for PR #10.


---

## 2026-09-19 — Gate 005 acceptance synchronized

Gate 005 final accepted branch head:
`9d6677290ee5bbaf0253234c7b8d479c6a3f948e`

Final validation:
- local Windows/Python 3.12 regression: `39/39 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`ddf6fd9420bc60d3d812a17b948f7319e2cb63cd`

Gate 005 state:
`ACCEPTED_MERGED`.

---

## 2026-09-19 — Gate 006 deterministic role loop implemented

Issue #11 / draft PR #12.

Branch:
`gate-006-planner-executor-reviewer`

Baseline:
- Gate 005 merge `ddf6fd9420bc60d3d812a17b948f7319e2cb63cd`;
- model `gpt-oss:20b`;
- reasoning `medium`;
- context `8192`;
- benchmark-equivalent max output `2048`.

Implemented:
- explicit `PLANNER / EXECUTOR / REVIEWER` roles and typed results;
- deterministic role-loop state machine with illegal-transition rejection;
- separate role prompts and contexts while using one replaceable provider;
- Planner cannot execute tools;
- Executor receives only the approved plan and declared tool surface;
- model tool calls remain inert proposals;
- existing deterministic Supervisor evaluates proposal policy and invokes a narrow registered tool only after `ALLOW`;
- deterministic evidence is required before review/completion;
- Reviewer outcomes: `ACCEPT / REVISE / REJECT / NEEDS_HUMAN_APPROVAL`;
- bounded revision behavior and terminal failure;
- reviewer rejection and approval boundaries;
- `MODEL_CALL` audit records with role/model/provider/runtime identity;
- narrow read-only local smoke harness in `scripts/gate006_role_smoke.py`.

A first deterministic test attempt correctly exposed an invalid test-only policy fixture; the production validator was not weakened. The fixture was corrected to retain all global approval boundaries.

A later refactor routed model tool proposals through the existing Supervisor rather than a parallel policy authority. A simple initialization-order defect was then found by CI and corrected without changing policy or validator semantics.

Deterministic implementation validation head:
`61f8bc469e3ab827749d7a94a6a393e5715a237a`

Result:
- deterministic suite: `46/46 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

Local runtime smoke:
- harness: `IMPLEMENTED`;
- target: `gpt-oss:20b / medium / 8192 / 2048`;
- execution on primary Windows/Ollama workstation: `NOT_RUN`.

Next step:
Execute the narrow local role-loop smoke on the primary workstation, record its evidence, then run final regression and strict exact-head CI on the final PR head before requesting explicit exact-SHA squash-merge approval.


---

## 2026-09-19 — Gate 006 local smoke exposed tool-only Executor response

Local workstation smoke was executed on head:
`30ade24c9128a0c44cd81a7e90f0740237d1711c`.

Observed:
- Planner advanced into Executor;
- local `gpt-oss:20b / medium / 8192 / 2048` returned a tool proposal with empty response `content`;
- Gate 006 attempted to parse the empty Executor content as JSON and terminated with
  `SemanticValidationError: EXECUTOR returned invalid JSON`.

Classification:
`FAIL_RUNTIME_CONTRACT`.

This was not classified as an engineering-domain failure, evidence PASS, or physical validation.

Review against accepted Gate 005 semantics showed that the tool-proposal benchmark intentionally scores `response.tool_calls` and does not require JSON content alongside a tool proposal.

Correction:
- Executor now accepts empty content only when a tool proposal is present;
- a neutral summary is created deterministically by orchestration;
- tool proposals remain inert and still pass through the existing deterministic Supervisor;
- empty content without tool proposals remains invalid;
- a dedicated regression test covers the observed local runtime shape.

Corrected implementation head:
`00b17d498f90e3970352f6264584f8b1fdb60d53`.

Corrected validation:
- deterministic tests: `47/47 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.

Evidence:
`docs/evidence/gate006/runtime-smoke.md`.

Next step:
rerun the local workstation smoke on the corrected documented branch head.


---

## 2026-09-19 — Gate 006 second local smoke exposed Reviewer structured-output failure

Local workstation smoke was executed on head:
`7e20a4beaf617dfd118e4f7d1cb1c6ecc3e96942`.

Observed:
- Planner completed;
- Executor proposed the permitted read action;
- deterministic Supervisor evaluated the proposal;
- `STATUS.md` was read through the bounded read-only adapter;
- deterministic evidence was collected;
- Reviewer then returned content that did not satisfy the required JSON contract;
- the role loop propagated `SemanticValidationError: REVIEWER returned invalid JSON` as an uncaught traceback.

Classification:
`FAIL_RUNTIME_CONTRACT`.

Correction:
- Planner/Reviewer structured output now has one bounded same-model/same-reasoning protocol retry;
- retry preserves the existing schema and asks for exactly one valid JSON object;
- retry exhaustion produces terminal `FAIL`, not an exception;
- malformed Executor structured output also becomes terminal `FAIL`;
- audit model events now include done reason, content length, and tool-call count.

Corrected implementation head:
`0cb1756ebb8eb50ee4f45d883b42a0c14b1d2cca`.

Validation:
- deterministic tests: `50/50 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.

Next step:
rerun the local workstation smoke on the final documented branch head.


---

## 2026-09-19 — Gate 006 local runtime smoke passed end-to-end

Local workstation smoke was executed on head:
`f3c434e630a10bbf016e28d6c873df4f79783c28`.

Runtime:
- Windows 11 Pro;
- Ollama `0.34.1`, loopback-only;
- model `gpt-oss:20b`;
- reasoning `medium`;
- context `8192`;
- max output `2048`.

Observed result:
- state: `COMPLETE`;
- job status: `PASS`;
- blocker: none;
- executed action: `read_repository`;
- deterministic evidence:
  `sha256:STATUS.md:ac9f1cb5c40f9793a0342df00f7926b9b95af12e9f7e70b2f27b5710097b4b45`;
- Reviewer decision: `ACCEPT`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

Interpretation:
the complete Planner -> Executor -> deterministic Supervisor -> bounded tool ->
deterministic evidence -> Reviewer -> Supervisor terminal path executed
successfully on the primary workstation without granting additional authority.

Gate 006 local runtime acceptance criterion is satisfied.

Next step:
final regression and strict exact-head CI on the final documentation/evidence
head, followed by explicit human exact-SHA squash-merge approval for PR #12.
