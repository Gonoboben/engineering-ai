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


---

## 2026-09-19 — Gate 006 accepted and merged

Final approved PR head:
`04d3f7653471b8bb8db7f90d939e55b122bfc1c1`.

Final acceptance evidence:
- deterministic tests: `50/50 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- local Windows/Ollama end-to-end role-loop smoke: `COMPLETE / PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`;
- physical validation remained `PHYSICAL_NOT_EXECUTED`.

Squash merge on `main`:
`24b1fbc009920c1dee8317c784ef42711044be87`.

Issue #11 was closed by the merged PR.

Gate 006 state:
`ACCEPTED_MERGED`.

---

## 2026-09-19 — Gate 007 supervised multi-model architecture opened

Human direction:
- retain the deterministic Supervisor as the sole control authority;
- move to a supervised multi-model architecture after Gate 006;
- use specialized local models through controlled hand-offs rather than unrestricted peer-to-peer communication;
- qualify `Qwen3.5-9B` and `Qwen2.5-Coder-7B` before assigning production roles;
- retain `gpt-oss:20b / medium` as the accepted baseline/deep-reasoning reference;
- defer 27B-class downloads on the current workstation unless later evidence justifies them;
- design a future controlled bridge so an external ChatGPT/OpenAI reviewer can supervise/advice without bypassing local policy.

Issue:
`#13 — Gate 007 — Supervised multi-model architecture baseline`.

Branch:
`gate-007-supervised-multi-model-architecture`.

Base:
Gate 006 squash merge `24b1fbc009920c1dee8317c784ef42711044be87`.

Draft PR:
`#14`.

Gate 007 scope is architecture/governance only:
- Model Capability Registry semantics;
- deterministic Supervisor-owned Model Router;
- Supervisor-controlled Task Blackboard;
- evidence-based disagreement escalation;
- external-control boundary;
- roadmap realignment.

Explicitly out of scope:
- downloading or qualifying models;
- implementing the router or Blackboard runtime;
- project adapters;
- external bridge implementation;
- any increase in model authority.

Next step:
complete architecture-document consistency review and exact-head CI before requesting explicit exact-SHA human architecture approval.


---

## 2026-09-19 — Gate 007 architecture documentation review completed

Architecture preparation head:
`a8128d8f28815e2c100f8f9b71940b61b830491c`.

Consistency review:
- changed files limited to architecture/governance/status documentation;
- no model/runtime download or qualification;
- no router/Blackboard implementation;
- no project adapter change;
- no model authority increase;
- no stale Gate 007 PlataVM numbering or Gate 006 pending-state conflicts detected.

Validation on the architecture preparation head:
- deterministic tests: `50/50 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.

Gate 007 state:
`ARCHITECTURE_DOCUMENTED_PENDING_HUMAN_APPROVAL`.

A final exact-head CI run is required after status/chronology synchronization before requesting exact-SHA squash-merge approval.


---

## 2026-09-19 — Gate 007 accepted and merged

Final approved PR head:
`c09dae76d0526a899233a9b4656affd0d4c7e631`.

Final validation:
- deterministic tests: `50/50 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- explicit exact-SHA architecture approval: `PASS`.

Squash merge on `main`:
`3903672d44f6ac5119183eb58363847d42e25d9b`.

Issue #13 closed.

Accepted architecture:
- Supervisor-mediated specialist models;
- deterministic Model Capability Registry / Router authority;
- Supervisor-controlled Task Blackboard;
- evidence-based disagreement handling;
- optional controlled external review bridge;
- no unrestricted peer-to-peer swarm;
- model agreement is not evidence.

Gate 007 state:
`ACCEPTED_MERGED`.

---

## 2026-09-19 — Gate 008 local specialist model qualification opened

Issue:
`#15 — Gate 008 — Local specialist model qualification`.

Branch:
`gate-008-local-specialist-model-qualification`.

Base:
Gate 007 squash merge `3903672d44f6ac5119183eb58363847d42e25d9b`.

Candidates:
- `qwen3.5:9b`;
- `qwen2.5-coder:7b-instruct`.

Reference:
- accepted `gpt-oss:20b / medium / context 8192 / max output 2048`.

Human direction:
- do not test Electronics/PCB capability in Gate 008;
- do not run KiCad/ERC/DRC/SPICE specialist tests;
- prepare and qualify the basic model stack first;
- determine engineering specialist assignments later;
- do not download 27B-class models in this Gate.

Next step:
prepare deterministic Gate 008 benchmark/evidence harness, then install and benchmark the two fixed candidate tags on the primary workstation.


---

## 2026-09-19 — Gate 008 candidate models installed and metadata verified

Primary workstation repository head before installation:
`685f1ec046f0b42b8bd8d7c533dab7e5043cb6ce`.

Installed:
- `qwen3.5:9b` — local ID `6488c96fa5fa`, 6.6 GB package, architecture `qwen35`, 9.7B parameters, context 262144, Q4_K_M, capabilities completion/vision/tools/thinking;
- `qwen2.5-coder:7b-instruct` — local ID `dae161e27b0e`, 4.7 GB package, architecture `qwen2`, 7.6B parameters, context 32768, Q4_K_M, capabilities completion/tools/insert.

Captured environment remained:
- `OLLAMA_CONTEXT_LENGTH=8192`;
- `OLLAMA_HOST=127.0.0.1:11434`;
- `OLLAMA_MAX_LOADED_MODELS=1`;
- `OLLAMA_MODELS=C:\workspace\models\ollama`;
- `OLLAMA_NO_CLOUD=1`;
- `OLLAMA_NUM_PARALLEL=1`;
- `ollama ps` empty before benchmark.

No Electronics/PCB/KiCad/ERC/DRC/SPICE capability was tested.

Next step:
run only the Qwen3.5-9B general/Planner benchmark before starting any Qwen2.5-Coder benchmark.


---

## 2026-09-19 — Gate 008 Qwen3.5-9B general/Planner qualification passed

Tested model:
`qwen3.5:9b`, local ID `6488c96fa5fa`, Q4_K_M, 9.7B.

Runtime:
- Ollama `0.34.2`;
- context `8192`;
- max output `2048`;
- reasoning `none`.

Result:
- general suite: `4/4 PASS`;
- failed: `0`;
- unscored: `0`;
- structured JSON: `PASS`;
- bounded Planner contract: `PASS`;
- validation semantics: `PASS`;
- inert tool proposal: `PASS`;
- truncation/timeouts/provider errors: `0`.

Performance/resource observations:
- aggregate wall time ~`31.446 s`;
- first cold case ~`29.394 s`;
- warm cases ~`0.849 s`, `0.586 s`, `0.617 s`;
- eval throughput by case ~`57.72`, `49.55`, `46.02`, `67.02 tok/s`;
- Ollama placement: `100% GPU`;
- model VRAM allocation ~`5.37 GiB`;
- total post-run GPU memory used `7487 MiB`, free `538 MiB`;
- post-run free physical RAM ~`21.47 GiB`.

Qualification:
`QUALIFIED_GENERAL_PLANNER`.

The speed result is not treated as a direct replacement comparison with historical Gate 005 gpt-oss because the benchmark matrix and Ollama runtime version differ.

Electronics/PCB/KiCad/ERC/DRC/SPICE capability remains:
`NOT_RUN_OUT_OF_SCOPE_GATE_008`.

Next step:
run only the Qwen2.5-Coder-7B-Instruct code/repository suite.


---

## 2026-09-19 — Gate 008 Qwen2.5-Coder first run exposed scorer false negative and tool transport limitation

Tested model:
`qwen2.5-coder:7b-instruct`, local ID `dae161e27b0e`, Q4_K_M, 7.6B.

Runtime:
- Ollama `0.34.2`;
- context `8192`;
- max output `2048`;
- reasoning argument omitted.

Observed attempt-1 result under the original scorer:
- `2 PASS / 2 FAIL / 0 INCONCLUSIVE`.

Case review:
- `code-clamp-repair`: model returned `return max(lo, min(hi, x))`, which is semantically correct; the scorer accepted only the bare expression and therefore produced a false negative;
- `code-off-by-one-repair`: `PASS`;
- `code-review-evidence`: `PASS`;
- `code-tool-proposal`: `FAIL`; the model wrote a JSON-shaped tool intent into `content` but returned no native `tool_calls`.

Correction:
- clamp scorer now accepts the same correct expression either with or without an explicit `return` prefix;
- tool-call scorer remains unchanged and still requires native inert `tool_calls`;
- a regression test explicitly proves that JSON in content does not count as native tool transport.

Resource observations:
- aggregate wall time ~`4.746 s`;
- first cold case ~`3.616 s`;
- warm cases ~`0.289 s`, `0.468 s`, `0.373 s`;
- placement `100% GPU`;
- model VRAM allocation ~`4.78 GiB`;
- total post-run GPU memory used `6164 MiB`, free `1861 MiB`;
- post-run free physical RAM ~`22.04 GiB`;
- no truncation, timeout, or provider error.

Classification:
- clamp failure = `BENCHMARK_FALSE_NEGATIVE_CORRECTED`;
- native tool transport failure = `REAL_RUNTIME_CONTRACT_FAILURE_ATTEMPT_1`.

Next step:
rerun the fixed code/repository suite on the corrected exact head before assigning any final Coder qualification state.


---

## 2026-09-19 — Gate 008 Qwen2.5-Coder corrected rerun confirmed limited qualification

Corrected rerun:
- model `qwen2.5-coder:7b-instruct`;
- context `8192`;
- max output `2048`;
- reasoning argument omitted;
- Ollama `0.34.2`.

Result:
- `3 PASS / 1 FAIL / 0 INCONCLUSIVE`;
- clamp repair: `PASS`;
- off-by-one repair: `PASS`;
- evidence review: `PASS`;
- native tool proposal: `FAIL`.

The remaining failure reproduced attempt 1 exactly:
the model emitted the correct JSON-shaped tool intent in ordinary response
`content` but returned no native `tool_calls`.

This is classified as a confirmed runtime-contract limitation, not a coding
correctness failure.

Performance/resource observations:
- aggregate wall time ~`1.680 s`;
- case wall times ~`0.639 s`, `0.308 s`, `0.476 s`, `0.255 s`;
- eval throughput ~`42.63`, `62.06`, `56.42`, `76.96 tok/s`;
- placement `100% GPU`;
- model VRAM allocation ~`4.78 GiB`;
- total post-run GPU memory used `6079 MiB`, free `1946 MiB`;
- post-run free physical RAM ~`22.08 GiB`;
- no truncation, timeout, or provider error.

Final Gate 008 role qualification:
`QUALIFIED_WITH_LIMITATIONS_CODE_REPOSITORY`.

Restriction:
`NO_NATIVE_TOOL_PROPOSALS_UNDER_CURRENT_OLLAMA_CONTRACT`.

The model may be used for code/repository analysis, repair, review, and
generation when required context is supplied by the deterministic Supervisor
or another authorized acquisition step. It must not be routed to a task that
requires it to originate native tool calls until separately corrected and
requalified.

Qwen3.5-9B remains:
`QUALIFIED_GENERAL_PLANNER`.

Electronics/PCB/KiCad/ERC/DRC/SPICE remains:
`NOT_RUN_OUT_OF_SCOPE_GATE_008`.

Next step:
final regression and exact-head CI, then human exact-SHA Gate 008 merge approval.


---

## 2026-09-19 — Gate 008 qualification evidence head validated

Qualification evidence head:
`d57c79dbeea54be42512146958e67526d1ad13af`.

Validation:
- deterministic tests: `56/56 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.

Qualification state:
- `qwen3.5:9b`: `QUALIFIED_GENERAL_PLANNER`;
- `qwen2.5-coder:7b-instruct`: `QUALIFIED_WITH_LIMITATIONS_CODE_REPOSITORY`;
- Coder limitation: `NO_NATIVE_TOOL_PROPOSALS_UNDER_CURRENT_OLLAMA_CONTRACT`;
- Electronics/PCB/KiCad/ERC/DRC/SPICE: `NOT_RUN_OUT_OF_SCOPE_GATE_008`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

One final exact-head CI run is required after this acceptance-state synchronization before explicit human squash-merge approval for PR #16.


---

## 2026-09-19 — Gate 008 accepted and merged

Final approved PR head:
`30ccc9c54e519885678d10c4eee72f428b17b079`.

Final validation:
- deterministic tests: `56/56 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`d797ac476cc6653932b683932d025de747f3e918`.

Issue #15 closed.

Accepted role qualifications:
- `qwen3.5:9b`: `QUALIFIED_GENERAL_PLANNER`;
- `qwen2.5-coder:7b-instruct`: `QUALIFIED_WITH_LIMITATIONS_CODE_REPOSITORY`;
- Coder limitation: `NO_NATIVE_TOOL_PROPOSALS_UNDER_CURRENT_OLLAMA_CONTRACT`;
- `gpt-oss:20b / medium` remains accepted baseline;
- Electronics/PCB/KiCad/ERC/DRC/SPICE remains `NOT_RUN_OUT_OF_SCOPE_GATE_008`.

Gate 008 state:
`ACCEPTED_MERGED`.

---

## 2026-09-19 — Gate 009 model capability registry and deterministic router opened

Issue:
`#17 — Gate 009 — Model capability registry and deterministic router`.

Branch:
`gate-009-model-capability-registry-router`.

Base:
Gate 008 squash merge `d797ac476cc6653932b683932d025de747f3e918`.

Draft PR:
`#18`.

Implemented scope:
- immutable evidence-backed model capability registry;
- explicit typed task classes;
- deterministic model Router;
- context/output/native-tool hard requirement matching;
- explicit `NO_ROUTE` when no qualified model satisfies requirements;
- Supervisor-owned `route_model()` selection boundary;
- evidence references on model capability records;
- no provider/model/tool execution in Router.

Initial route classes:
- `GENERAL_PLANNING -> qwen3.5:9b`;
- `CODE_REPOSITORY -> qwen2.5-coder:7b-instruct` when native model tool proposals are not required;
- `CODE_REPOSITORY + native tool proposal required -> NO_ROUTE`;
- `BASELINE_REASONING -> gpt-oss:20b / medium`.

Explicitly absent:
- free-text/LLM route classification;
- Electronics/PCB/KiCad/Vision routes;
- Task Blackboard;
- model hand-offs;
- project adapters;
- new model qualification.

Next step:
complete deterministic tests and generic/strict exact-head CI before requesting exact-SHA human merge approval.


---

## 2026-09-19 — Gate 009 routing implementation validated

Implementation validation head:
`6671d4e6fe9c11734f87ba23dba064e4d9a5ac50`.

Validated:
- immutable evidence-backed Model Capability Registry;
- deterministic explicit-task-class Router;
- Supervisor-owned `route_model()` boundary;
- context/output qualification limits;
- native-tool capability requirement;
- explicit `NO_ROUTE` behavior;
- deterministic tie-breaking;
- no provider/model/tool execution dependency;
- no Electronics/PCB/KiCad/Vision task classes.

Routing:
- `GENERAL_PLANNING -> qwen3.5:9b`;
- `CODE_REPOSITORY -> qwen2.5-coder:7b-instruct` when native tool proposals are not required;
- `CODE_REPOSITORY + native tool proposal required -> NO_ROUTE`;
- `BASELINE_REASONING -> gpt-oss:20b / medium`.

Validation:
- deterministic tests: `69/69 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.

CI during test development rejected incomplete test-only policy/state fixtures.
The production Router/Supervisor policy semantics were not weakened; fixtures
were corrected to satisfy the existing schema and mandatory approval boundaries.

Gate 009 state:
`IMPLEMENTED_VALIDATED_PENDING_HUMAN_APPROVAL`.

One final exact-head CI run is required after acceptance-state synchronization.


---

## 2026-09-19 — Gate 009 accepted and merged

Final approved PR head:
`507eeb5af13e9c138d8dfc023eb2bcd032e4b5c9`.

Final validation:
- deterministic tests: `69/69 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`711d23fb9739e7d9069e5d2569f00231988ef176`.

Issue #17 closed.

Accepted deterministic routing:
- `GENERAL_PLANNING -> qwen3.5:9b`;
- `CODE_REPOSITORY -> qwen2.5-coder:7b-instruct` when native tool proposals are not required;
- `CODE_REPOSITORY + native tool proposal required -> NO_ROUTE`;
- `BASELINE_REASONING -> gpt-oss:20b / medium`.

Gate 009 state:
`ACCEPTED_MERGED`.

---

## 2026-09-19 — Gate 010 Task Blackboard and supervised hand-offs opened

Issue:
`#19 — Gate 010 — Task Blackboard and supervised model hand-offs`.

Branch:
`gate-010-task-blackboard-handoffs`.

Base:
Gate 009 squash merge `711d23fb9739e7d9069e5d2569f00231988ef176`.

Draft PR:
`#20`.

Implemented scope:
- typed bounded append-only runtime Blackboard;
- read-only worker views;
- Supervisor-owned task/context/model/evidence/handoff write APIs;
- model claims and tool proposals remain `ADVISORY`;
- deterministic evidence requires deterministic-tool authority and explicit evidence refs;
- explicit visible record IDs on each handoff;
- hidden or cross-task evidence cannot satisfy required context;
- Coder handoff requires visible deterministic context completeness.

Context-resolution precedence:
1. `CONTEXT_READY` when required evidence is already present;
2. `DETERMINISTIC_ACQUISITION` when missing context is explicitly known;
3. `TOOL_PLANNER -> qwen3.5:9b` when missing context/tool need must be determined;
4. `DEEP_ESCALATION -> gpt-oss:20b / medium` when tool choice is explicitly ambiguous.

`qwen2.5-coder:7b-instruct` receives supplied context and is not given native-tool-proposal work.

Explicitly out of scope:
- Gate 011 independent disagreement review;
- Electronics/PCB/KiCad/Vision roles;
- project adapters/write authority;
- persistent memory/RAG;
- external bridge;
- direct worker-to-worker communication.

Next step:
run deterministic regression and exact-head CI for the Gate 010 implementation.


---

## 2026-09-19 — Gate 010 Blackboard implementation validated

Implementation validation head:
`2445de8c163e553bb2735ce21e6c0a5068aa912e`.

Validated:
- typed bounded append-only Task Blackboard;
- immutable/read-only worker-visible records;
- Supervisor-only control/evidence/handoff write boundary;
- model claims remain `ADVISORY`;
- model tool proposals remain `ADVISORY` and unexecuted;
- deterministic evidence requires deterministic-tool authority plus evidence references;
- explicit record-ID visibility on handoffs;
- hidden and cross-task evidence cannot satisfy required context;
- deterministic acquisition is selected when missing context is explicit;
- Qwen3.5-9B is selected for bounded missing-context tool planning;
- gpt-oss:20b / medium is selected for explicit ambiguous tool-planning escalation;
- Qwen2.5-Coder handoff requires complete visible deterministic context;
- Qwen2.5-Coder native-tool-required handoff remains `NO_ROUTE`;
- no Electronics/PCB/KiCad/Vision task class exists.

Validation:
- deterministic tests: `87/87 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.

Gate 010 state:
`IMPLEMENTED_VALIDATED_PENDING_HUMAN_APPROVAL`.

One final exact-head CI run is required after acceptance-state synchronization.


---

## 2026-09-19 — Gate 010 accepted and merged

Final approved PR head:
`f831c3126781ae5e63cbdadb077fb8d40f352885`.

Final validation:
- deterministic tests: `87/87 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`34d18a85b5a00510331b4c75501a0672bc607093`.

Issue #19 closed.

Accepted Blackboard/handoff semantics:
- typed bounded append-only Blackboard;
- read-only worker views;
- explicit visible record IDs;
- model claims/tool proposals remain advisory;
- deterministic evidence requires tool authority and evidence refs;
- deterministic acquisition before model tool planning;
- Qwen3.5 tool-planning path;
- gpt-oss deep escalation path;
- Qwen2.5-Coder supplied-context-only handoff.

Gate 010 state:
`ACCEPTED_MERGED`.

---

## 2026-09-19 — Gate 011 independent review and disagreement escalation opened

Issue:
`#21 — Gate 011 — Independent review and disagreement escalation`.

Branch:
`gate-011-independent-review-escalation`.

Base:
Gate 010 squash merge `34d18a85b5a00510331b4c75501a0672bc607093`.

Implemented scope:
- evidence-first disagreement controller;
- deterministic support/contradiction resolution;
- gpt-oss bounded independent review for Qwen-originated claims;
- distinct-model reviewer check;
- one bounded revision maximum;
- human escalation on self-review, exhausted revision, or inconclusive review;
- Blackboard disagreement/review/revision/escalation records.

Important semantics:
- deterministic evidence outranks model review;
- review records remain advisory;
- RESOLVED_AFTER_REVIEW is workflow resolution only, not evidence promotion;
- majority voting and confidence aggregation are absent;
- gpt-oss cannot independently review a gpt-oss-originated claim;
- no new reviewer model is qualified.

Explicitly out of scope:
- Electronics/PCB/KiCad/Vision roles;
- project adapters/write authority;
- external review bridge;
- persistent memory/RAG;
- unattended queue.

Next step:
open draft PR and run deterministic/generic/strict exact-head validation.


---

## 2026-09-19 — Gate 011 review implementation validated

Implementation validation head:
`117ee434e1b55faf06580bd8ae9474e5f1085107`.

Validated:
- deterministic evidence resolves support/contradiction before model review;
- Qwen-originated unresolved claims route to `gpt-oss:20b / medium`;
- gpt-oss-originated unresolved claims cannot self-review;
- same-model review is rejected;
- model review records remain `ADVISORY`;
- review does not promote model output to deterministic evidence;
- one bounded revision maximum;
- second revision request -> `NEEDS_HUMAN_APPROVAL`;
- inconclusive review -> `NEEDS_HUMAN_APPROVAL`;
- non-evidence records cannot be declared deterministic evidence;
- no majority voting or confidence aggregation;
- no Electronics/PCB/KiCad/Vision roles added.

Validation:
- deterministic tests: `99/99 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.

Gate 011 state:
`IMPLEMENTED_VALIDATED_PENDING_HUMAN_APPROVAL`.

One final exact-head CI run is required after acceptance-state synchronization.


---

## 2026-09-19 — Gate 011 accepted and merged

Final approved PR head:
`242d4bdf41d6fa6c31c1c23e56ceae5981a0ffbb`.

Final validation:
- deterministic tests: `99/99 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`da23f2c60a604f022ee91d6b129afc4ed2523a18`.

Issue #21 closed.

Accepted disagreement semantics:
- deterministic evidence first;
- independent gpt-oss review for Qwen-originated unresolved claims;
- no self-review;
- one bounded revision maximum;
- unresolved cases escalate human;
- model agreement remains advisory.

Gate 011 state:
`ACCEPTED_MERGED`.

---

## 2026-09-19 — Gate 012 PlataVM read-only adapter opened

Issue:
`#23 — Gate 012 — PlataVM read-only adapter`.

Branch:
`gate-012-platavm-readonly-adapter`.

Base:
Gate 011 squash merge `da23f2c60a604f022ee91d6b129afc4ed2523a18`.

Draft PR:
`#24`.

PlataVM mandatory governance was read in the order required by `AGENTS.md`.
The dynamic `Docs/PROJECT_STATUS.md` was observed to lag current GitHub state,
so Gate 012 treats governance/Git mismatch as explicit source conflict rather
than silently reconciling it.

Remote PlataVM state observed at Gate opening:
- PR #100: OPEN / DRAFT;
- base: `main@dcba77466d4800c0e7a336a2771684e066f845db`;
- head: `11e746cfea7f9200415cf817b6cde928b6a2651a`;
- repository workflow run `35105701408`: `completed/cancelled`;
- KiCad workflow run `35105701440`: `completed/cancelled`;
- exact-head PASS is therefore not claimed.

Implemented:
- strict PlataVM read-only profile/policy;
- mandatory governance and latest chronology resolution;
- safe Git branch/HEAD/origin-main/status snapshot;
- stale governance conflict detection;
- bounded `Hardware/KiCad` inventory;
- fixed read-only repository-integrity and semantic-gate validator profiles;
- post-validator Git-visible mutation detection;
- explicit CI state mapping preserving `CANCELLED` as non-PASS;
- local smoke harness.

The first Gate 012 CI attempt exposed a new-adapter inventory defect caused by
attempting to enumerate repository root through the generic filesystem
adapter's strict child-boundary rule. The generic security boundary was not
weakened. Inventory was narrowed to `Hardware/KiCad`.

Corrected implementation head:
`53d54fe8a27fa88f0381590fcca4a80b43b276f3`.

Corrected validation:
- deterministic tests: `108/108 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.

Remaining acceptance item:
local read-only smoke on `C:\workspace\repos\plataVM`, including the two
fixed validators and proof that Git-visible state is unchanged.

PlataVM barriers remain:
`PACKAGE_SET_NOT_READY / fabrication NOT_GRANTED / physical NOT_EXECUTED /
PROTOTYPE_BASIS_ONLY_NOT_RELEASED / UNDECIDED / series NOT_GRANTED`.


---

## 2026-09-19 — Gate 012 local smoke blocked by missing checkout

The first primary-workstation smoke attempt did not reach adapter validation.

Observed:
- Engineering AI Gate 012 checkout was correct at `0e675792d61a9b450cf9565380761d46b1a5c004`;
- `C:\workspace\repos\plataVM` did not exist;
- Git commands against that path failed with repository-path-not-found;
- the smoke script failed during strict Path resolution;
- no PlataVM repository content existed locally to read or modify;
- no validator executed against PlataVM;
- no PlataVM Git-visible state changed.

Classification:
`BLOCKED_LOCAL_REPOSITORY_NOT_FOUND`, not Gate failure.

The smoke harness was tightened to emit structured
`LOCAL_REPOSITORY_NOT_FOUND` with exit code 2 instead of an unhandled
traceback.

Next admissible step:
create a normal local clone at the profile path, then repeat the same strict
read-only smoke. No PlataVM GitHub Actions rerun or PR #100 mutation is
authorized by Gate 012.


---

## 2026-09-19 — Gate 012 real smoke exposed chronology-selection defect

A real local PlataVM checkout was created and the strict Gate 012 smoke ran on
the primary workstation.

Observed PlataVM state:
- `main@dcba77466d4800c0e7a336a2771684e066f845db`;
- `origin/main` same SHA;
- clean before/after smoke;
- 62 bounded KiCad assets;
- stale `PROJECT_STATUS` main pointer correctly surfaced as `SOURCE_CONFLICT`;
- repository integrity PASS: 365 tracked paths / 35 JSON;
- semantic Gates PASS: 47/47;
- process exit 0;
- physical state remained `PHYSICAL_NOT_EXECUTED`.

However, the adapter selected `Docs/chronology/README.md` as the latest
chronology item. That violates Gate 012's requirement to resolve the latest
dated chronology entry.

Classification:
`READ_ONLY_BOUNDARY_PASS_WITH_CHRONOLOGY_SELECTION_DEFECT`.

The defect was corrected without weakening the filesystem boundary:
- only `YYYY-MM-DD*.md` direct chronology entries are candidates;
- README/non-dated files are excluded;
- zero dated entries is a hard error;
- a regression fixture proves README cannot win selection.

Final corrected-head CI and one corrected-head local smoke remain required.


---

## 2026-09-19 — Gate 012 final corrected-head local smoke passed

Final corrected-head local smoke executed on the primary workstation after the
chronology-selection fix.

Engineering AI head at smoke:
`4ba5d7890f86648dfdcbc0ecab23508c4e0ebf3e`.

Observed PlataVM:
- `main@dcba77466d4800c0e7a336a2771684e066f845db`;
- `origin/main` same SHA;
- clean before/after smoke;
- latest chronology correctly resolved to
  `Docs/chronology/2026-09-11-post-pr96-status-roadmap-checkpoint-v1-9.md`;
- 62 KiCad assets;
- stale PROJECT_STATUS main pointer surfaced as `SOURCE_CONFLICT`;
- repository integrity PASS;
- semantic Gates `47/47 PASS`;
- process exit `0`;
- physical state remained `PHYSICAL_NOT_EXECUTED`.

No PlataVM Git-visible state changed. No GitHub Actions rerun and no PR #100
mutation occurred.

Gate 012 local-smoke state:
`PASS_READ_ONLY_WITH_EXPECTED_SOURCE_CONFLICT`.

Next step:
final acceptance-state generic + strict exact-head CI, scope review, and exact-SHA
human squash-merge approval for PR #24.


---

## 2026-09-19 — Gate 012 accepted and merged

Final approved PR head:
`cff21648524c667233daf9a765e161871ea23b7c`.

Final validation:
- deterministic tests: `110/110 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- final real local smoke: `PASS_READ_ONLY_WITH_EXPECTED_SOURCE_CONFLICT`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`6df110df27458e221fb2713439b5e778da1da57f`.

Issue #23 closed.

Accepted PlataVM connection:
- strict read-only adapter;
- mandatory governance resolution;
- dated latest chronology resolution;
- bounded KiCad inventory;
- fixed validators;
- Git/source conflict detection;
- no project write authority.

Gate 012 state:
`ACCEPTED_MERGED`.

---

## 2026-09-19 — Gate 013 PlataVM controlled engineering loop opened

Issue:
`#25 — Gate 013 — PlataVM controlled engineering loop`.

Branch:
`gate-013-platavm-controlled-engineering-loop`.

Base:
Gate 012 squash merge `6df110df27458e221fb2713439b5e778da1da57f`.

Draft PR:
`#26`.

Implemented controlled-write capability:
- isolated adapter-created Git worktree;
- `engineering-ai/` branch prefix;
- clean-primary precondition;
- explicit patch-path allow-list;
- exact before-content SHA-256 precondition;
- existing-file replacement only;
- root/path/symlink escape rejection;
- bounded write size;
- post-write diff capture;
- fixed PlataVM validator execution;
- success state limited to `READY_FOR_HUMAN_APPROVAL`.

Project policy:
- `read_repository / run_validator / propose_patch`: autonomous;
- `write_worktree`: explicit human approval required;
- `local_commit / push_remote / open_pr / merge_pr`: forbidden;
- architecture/physics/validator weakening/fabrication/release remain forbidden.

Real PlataVM constraint:
Gate 012 established an unresolved authoritative source conflict between stale
`Docs/PROJECT_STATUS.md` and current `origin/main`. Under Engineering AI
`AGENTS.md`, unresolved authoritative-source conflict is a stop condition.
Therefore Gate 013 real-project write must remain blocked before mutation.

Synthetic fixture validation proves the bounded write mechanism while real
PlataVM smoke must prove `BLOCKED_SOURCE_CONFLICT`.

Implementation head:
`9574f44c37189205ba8577096ce08b9dd893642f`.

Validation:
- deterministic tests: `119/119 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.

Remaining acceptance:
real primary-workstation policy-block smoke proving no worktree/project mutation.


---

## 2026-09-19 — Gate 013 real PlataVM policy-block smoke passed

Real local PlataVM smoke executed on the primary workstation against the
controlled-loop implementation.

Observed result:
- state: `BLOCKED_SOURCE_CONFLICT`;
- conflict: stale `PROJECT_STATUS` main
  `c9703c58486eb5efe6a1d1d3e1bbf37815cd2a65`
  vs actual `origin/main`
  `dcba77466d4800c0e7a336a2771684e066f845db`;
- worktree_created: `false`;
- before/after HEAD:
  `dcba77466d4800c0e7a336a2771684e066f845db`;
- before/after status:
  `## main...origin/main`;
- repository_unchanged: `true`;
- remote_mutation_attempted: `false`;
- physical validation: `PHYSICAL_NOT_EXECUTED`;
- process exit: `0`.

Classification:
`PASS_POLICY_BLOCK_BEFORE_MUTATION`.

This proves the real-project stop boundary: unresolved authoritative governance
conflict prevents controlled worktree creation and file mutation.

Next:
final acceptance-state CI, scope review, and exact-SHA human squash-merge
approval for PR #26.


---

## 2026-09-19 — Gate 013 accepted and merged

Final approved PR head:
`5822cc1a92dc1dbbd431f8f523b61e983efbfbfc`.

Final validation:
- deterministic tests: `119/119 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- real PlataVM policy-block smoke: `PASS_POLICY_BLOCK_BEFORE_MUTATION`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`2a8cdf6594d8eb6b29e2efb200683af95167bb20`.

Issue #25 closed.

Accepted capability:
- controlled isolated local worktree mechanism;
- exact before-content SHA-256 binding;
- explicit path allow-list;
- fixed validator loop;
- success bounded to `READY_FOR_HUMAN_APPROVAL`;
- commit/push/PR/merge still forbidden;
- real PlataVM write remains blocked by unresolved authoritative source conflict.

Gate 013 state:
`ACCEPTED_MERGED`.

---

## 2026-09-19 — Gate 014 BuoyCalc read-only adapter opened

Issue:
`#27 — Gate 014 — BuoyCalc read-only adapter`.

Branch:
`gate-014-buoycalc-readonly-adapter`.

Base:
Gate 013 squash merge `2a8cdf6594d8eb6b29e2efb200683af95167bb20`.

Current BuoyCalc main observed:
`0db1e7cc17e309fc1402fe58b265d2e95c2d4d39`.

Mandatory project authority read:
- `AGENTS.md`;
- `docs/OPTIMIZATION_PLAN.md`;
- `RELEASE.md`.

Implemented scope:
- strict read-only BuoyCalc profile/policy;
- governance SHA-256 provenance;
- Git branch/HEAD/origin-main/dirty snapshot;
- deterministic checks for frozen physics/release invariant markers;
- tracked-file inventory through fixed read-only `git ls-files`;
- conservative calculation-core/read-model/presentation/tooling classification;
- explicit CI states preserving CANCELLED/PENDING/MISSING as non-PASS;
- fixed release state
  `NOT_AUTHORIZED_REQUIRES_EXPLICIT_MANUAL_WINDOWS_RC_SMOKE`;
- local read-only smoke harness.

Remote evidence:
- PR #604 exact head `149c2eae96cd20f0ccff97ce18d51c2c36cc55c7`
  had successful .NET Build, Selected Shape Consumer Scan,
  Report Store Consumer Scan and Validation 601 Main Gate;
- current merge commit main returned no workflow runs;
- no release PASS is inferred from PR-head evidence.

Explicitly absent:
- calculation execution;
- physics/solver changes;
- UI/PDF/2D/report changes;
- validators in this Gate;
- project writes;
- RC packaging/trigger/tag/release;
- 3D.

Next:
open draft PR and run Engineering AI regression/CI before the local BuoyCalc
read-only smoke.
