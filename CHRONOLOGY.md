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


---

## 2026-09-19 — Gate 014 BuoyCalc adapter implementation validated

Implementation head:
`facc9d8b4a514120ce5be3a886fc77c8eda87dcc`.

Validated:
- mandatory governance resolution;
- SHA-256 provenance;
- read-only Git snapshot;
- frozen invariant-marker checks;
- tracked-file inventory through fixed `git ls-files`;
- conservative source-boundary classification;
- presentation/report paths never physics-authoritative;
- CI state separation including CANCELLED/PENDING/MISSING as non-PASS;
- fixed release state remains unauthorized;
- strict read-only profile/policy schema;
- no write/calculation/release API;
- structured missing-checkout handling.

Validation:
- deterministic tests: `128/128 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.

Gate 014 state:
`IMPLEMENTED_CI_VALIDATED_PENDING_LOCAL_SMOKE`.

Remaining:
stable-head CI followed by one local strict read-only smoke on the real BuoyCalc
checkout.


---

## 2026-09-19 — Gate 014 final BuoyCalc read-only smoke passed

Final local strict read-only smoke executed on the primary workstation.

Engineering AI head at smoke:
`b17fa249f4d717ed24b74898285addefac79be6c`.

Observed BuoyCalc:
- `main@0db1e7cc17e309fc1402fe58b265d2e95c2d4d39`;
- `origin/main` same SHA;
- clean before/after smoke;
- all ten frozen invariant markers PASS;
- 471 tracked source entries inventoried;
- presentation/report physics-authority violation: false;
- release state remained
  `NOT_AUTHORIZED_REQUIRES_EXPLICIT_MANUAL_WINDOWS_RC_SMOKE`;
- physical validation remained `PHYSICAL_NOT_EXECUTED`;
- repository unchanged;
- smoke exit `0`.

Classification:
`PASS_STRICT_READ_ONLY_BASELINE`.

No calculation/solver execution, validation weakening, project write,
RC packaging, release trigger, tag, GitHub Release or other BuoyCalc mutation
occurred.

Next:
final acceptance-state CI, scope review, and exact-SHA human squash-merge
approval for PR #28.


---

## 2026-09-19 — Gate 014 accepted and merged

Final approved PR head:
`681707e85b87332e36c7de9b9516e2f998d5a9d0`.

Final validation:
- deterministic tests: `128/128 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- real BuoyCalc read-only smoke: `PASS_STRICT_READ_ONLY_BASELINE`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`0f7ec3c01829f9c193e5730ec5144eee77c00b52`.

Issue #27 closed.

Accepted BuoyCalc connection:
- strict read-only governance/Git/invariant/source-boundary inspection;
- release remains unauthorized;
- no project write/calculation/release authority.

Gate 014 state:
`ACCEPTED_MERGED`.

---

## 2026-09-19 — Gate 015 BuoyCalc controlled engineering loop opened

Issue:
`#29 — Gate 015 — BuoyCalc controlled engineering loop`.

Branch:
`gate-015-buoycalc-controlled-engineering-loop`.

Base:
Gate 014 squash merge `0f7ec3c01829f9c193e5730ec5144eee77c00b52`.

Implemented scope:
- isolated adapter-owned Git worktrees;
- `engineering-ai/buoycalc/` branch prefix;
- primary main/clean/HEAD==origin-main prerequisite;
- explicit target allow-list;
- exact before-content SHA-256 binding;
- governance writes blocked;
- calculation-core/physics-candidate writes blocked;
- fixed validator profiles derived from accepted BuoyCalc workflow commands;
- no arbitrary shell;
- tracked-state mutation guard around validators;
- structured bounded stdout/stderr SHA-256 evidence;
- successful software state limited to `READY_FOR_HUMAN_APPROVAL`;
- guarded disposable cleanup for generated bin/obj/artifacts only when HEAD remains
  at base and both tracked diffs are empty.

Project policy:
- autonomous: read_repository / run_validator / propose_patch;
- human approval required: write_worktree;
- forbidden: calculation/simulation as free actions, commit/push/PR/merge,
  physics/architecture change, validator weakening, fabrication/release,
  destructive/scope-expansion/external-disclosure actions.

Release remains:
`NOT_AUTHORIZED_REQUIRES_EXPLICIT_MANUAL_WINDOWS_RC_SMOKE`.

Physical validation remains:
`PHYSICAL_NOT_EXECUTED`.

Next:
Engineering AI regression/CI, then one explicitly approved real BuoyCalc
disposable-worktree validation smoke.


---

## 2026-09-19 — Gate 015 controlled BuoyCalc implementation validated

Validated implementation head:
`b40baea3294474fafa26936e06b0fa5c7d69ea86`.

Validated control boundaries:
- primary main/clean/HEAD==origin-main prerequisite;
- `engineering-ai/buoycalc/` controlled branch prefix;
- exact target allow-list and before-content SHA-256 binding;
- governance and calculation-core/solver target rejection;
- fixed shell-free validator profiles from accepted BuoyCalc workflows;
- validator tracked-state mutation detection;
- structured SOFTWARE_DETERMINISTIC evidence hashes;
- successful suite bounded to `READY_FOR_HUMAN_APPROVAL`;
- release remains unauthorized;
- physical validation remains `PHYSICAL_NOT_EXECUTED`;
- guarded disposable generated-artifact cleanup;
- explicit CLI human approval required for real worktree smoke;
- no remote/release mutation API.

Validation:
- deterministic tests: `143/143 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.

Gate 015 state:
`IMPLEMENTED_CI_VALIDATED_PENDING_REAL_SMOKE`.

Remaining:
stable-head CI and one explicit primary-workstation disposable-worktree
validation smoke on the real BuoyCalc checkout.


---

## 2026-09-19 — Gate 015 real smoke attempt 1 blocked by local runtime prerequisite

Real primary-workstation controlled validation smoke started from clean aligned
BuoyCalc `main@0db1e7cc17e309fc1402fe58b265d2e95c2d4d39`.

Validation did not start because the allow-listed local process runner could not
resolve `dotnet`.

Observed:
- `VALIDATION_EXECUTION_ERROR`;
- exact error: `allow-listed executable not found: dotnet`;
- no validation profile executed;
- disposable worktree removed;
- disposable branch removed;
- primary BuoyCalc before/after state identical;
- release remained unauthorized;
- physical remained `PHYSICAL_NOT_EXECUTED`.

Classification:
`INFRASTRUCTURE_PREREQUISITE_BLOCK`, not engineering validation FAIL.

Correction:
- runtime preflight now occurs before worktree creation;
- standard Windows dotnet/pwsh locations are supported when PATH is missing;
- fixed `dotnet --list-sdks` requires .NET 8 SDK;
- missing prerequisite returns `BLOCKED_RUNTIME_PREREQUISITE`.

Corrected head:
`b6a490377f98cbe5d063e2a7460a977309507fe1`.

Regression:
`144/144 PASS`; generic CI PASS; strict exact-head CI PASS.

Next:
stable corrected-head CI and real smoke attempt 2.


---

## 2026-09-19 — Gate 015 smoke attempt 2 confirmed missing .NET 8 and PowerShell 7

Corrected runtime-preflight smoke ran on the real primary workstation.

Result:
- `BLOCKED_RUNTIME_PREREQUISITE`;
- `dotnet_executable=null`;
- `pwsh_executable=null`;
- `.NET 8 SDK unavailable`;
- no worktree created;
- no validation profile executed;
- primary BuoyCalc main/head/status unchanged;
- release remained unauthorized;
- physical remained `PHYSICAL_NOT_EXECUTED`;
- exit `4`.

Classification:
`RUNTIME_PREREQUISITE_MISSING`.

Required before attempt 3:
Microsoft .NET 8 SDK and PowerShell 7.


---

## 2026-09-19 — Gate 015 smoke attempt 3 passed software validation; cleanup blocked

Real primary-workstation smoke executed after local .NET 8 SDK and PowerShell 7
became available.

BuoyCalc baseline before/after:
`main@0db1e7cc17e309fc1402fe58b265d2e95c2d4d39`, clean and unchanged.

All fixed profiles passed:
- `buoycalc.dotnet_build`;
- `buoycalc.selected_shape_consumer_scan`;
- `buoycalc.report_store_consumer_scan`;
- `buoycalc.validation_601`.

All steps completed with exit 0, no timeout and no truncation.
Tracked state remained unchanged.

Software terminal state:
`READY_FOR_HUMAN_APPROVAL`.

Release remained:
`NOT_AUTHORIZED_REQUIRES_EXPLICIT_MANUAL_WINDOWS_RC_SMOKE`.

Physical remained:
`PHYSICAL_NOT_EXECUTED`.

The only failure was disposable Windows worktree removal:
`Permission denied`.

The temporary branch/worktree remained and process exited 1.

Classification:
`PASS_SOFTWARE_VALIDATION_WITH_CLEANUP_INFRASTRUCTURE_BLOCK`.

Cleanup was hardened with retry plus a guarded Windows filesystem fallback and
Git worktree prune. A dedicated stale-worktree recovery harness was added.

Cleanup-hardening head:
`87354398cd745856d8ff89798b5527e51477641c`.

Regression:
`145/145 PASS`; generic CI PASS; strict exact-head CI PASS.

Next:
recover only the exact stale worktree/branch. Full BuoyCalc validation does not
need repetition solely for this cleanup defect.


---

## 2026-09-19 — Gate 015 stale recovery attempt found worktree already deregistered

Guarded stale-worktree recovery returned:
`REFUSED: worktree is not registered by Git`.

Primary BuoyCalc remained:
`main@0db1e7cc17e309fc1402fe58b265d2e95c2d4d39`, clean.

`git worktree list` showed only the primary checkout, proving the prior
cleanup attempt had already removed Git worktree registration.

The recovery harness was corrected for this exact Windows partial-cleanup state
while tightening identity checks to the exact Gate 015 smoke branch and
worktree names derived from base SHA.

Corrected head:
`d8405894bfb9152256e28ca49678f27ed8a2471d`.

Regression:
`147/147 PASS`; generic CI PASS; strict exact-head CI PASS.

Next:
repeat cleanup only; do not repeat the full BuoyCalc validator suite.


---

## 2026-09-19 — Gate 015 final controlled cleanup passed

The exact stale disposable worktree/branch from smoke attempt 3 was recovered
successfully.

Result:
- `STALE_DISPOSABLE_WORKTREE_CLEANED`;
- worktree_removed: true;
- branch_removed: true;
- registered_before_cleanup: false;
- fallback_used: true;
- git_remove_errors: none;
- primary BuoyCalc before/after state identical;
- exit: 0;
- physical validation remained `PHYSICAL_NOT_EXECUTED`.

Post-cleanup `git worktree list` contains only the primary BuoyCalc checkout.

Combined Gate 015 real-project evidence:
- all four fixed validation profiles PASS;
- all validator steps exit 0 with no timeout/truncation;
- tracked state unchanged;
- primary checkout unchanged;
- release remains unauthorized;
- physical remains not executed;
- disposable worktree and controlled branch removed.

Classification:
`PASS_CONTROLLED_BUOYCALC_VALIDATION_AND_CLEANUP`.

Next:
final acceptance-state generic + strict exact-head CI, final scope review, and
exact-SHA human squash-merge approval for PR #30.


---

## 2026-09-19 — Gate 015 accepted and merged

Final approved PR head:
`14b6f43d44785839972ca9bc0ee564e72d82af9b`.

Final validation:
- deterministic tests: `147/147 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- real BuoyCalc controlled validation: `PASS`;
- stale disposable worktree recovery: `PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`496896ebb368618cbd9f3c6f26e31fae4acb8922`.

Issue #29 closed.

Accepted capability:
- isolated controlled BuoyCalc worktrees;
- non-core bounded patching;
- fixed build/test/validation profiles;
- structured validator evidence;
- runtime prerequisite preflight;
- Windows-safe disposable cleanup/recovery;
- successful software terminal state limited to
  `READY_FOR_HUMAN_APPROVAL`;
- no commit/push/PR/merge/release authority.

Gate 015 state:
`ACCEPTED_MERGED`.

---

## 2026-09-19 — Gate 016 decision/evidence memory opened

Issue:
`#31 — Gate 016 — Decision/evidence memory`.

Branch:
`gate-016-decision-evidence-memory`.

Base:
Gate 015 squash merge
`496896ebb368618cbd9f3c6f26e31fae4acb8922`.

Implemented initial scope:
- local SQLite standard-library store;
- append-only immutable memory records;
- SQLite UPDATE/DELETE prohibition triggers;
- stable `memory_id` + monotonic revision;
- exact supersession chain;
- canonical SHA-256 integrity hash;
- project isolation;
- typed ADR/calculation/test/failure/source records;
- explicit authority and validation classes;
- model-authored memory restricted to `ADVISORY`;
- human-only accepted ADRs;
- explicit deterministic/physical evidence guards;
- bounded deterministic filter/keyword search;
- database reopen/integrity verification;
- local persistent/reopen smoke harness.

Explicitly deferred:
- semantic/vector retrieval;
- automatic context injection/RAG;
- model-managed truth;
- external/cloud memory;
- online fine-tuning;
- destructive migration/compaction.

ADR-0015 added as `PROPOSED_GATE_016`.

Next:
open draft PR and run deterministic/generic/strict exact-head validation before
the local persistent/reopen smoke.


---

## 2026-09-19 — Gate 016 decision/evidence memory implementation validated

Validated implementation head:
`436e040fdf2198f10c56061855a2c4437d4786fe`.

Validated:
- local SQLite standard-library store;
- append-only immutable revisions;
- SQLite UPDATE/DELETE protection;
- exact latest-record supersession;
- schema-version binding;
- canonical SHA-256 integrity;
- reopen persistence;
- project isolation;
- deterministic bounded filter/keyword search;
- model memory remains ADVISORY;
- accepted ADR requires HUMAN authority;
- deterministic/physical evidence promotion guards;
- tamper/hash mismatch detection;
- absence of generic SQL/update/delete/vector/context-injection API;
- persistent/reopen smoke harness regression.

Validation:
- deterministic tests: `161/161 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.

Gate 016 state:
`IMPLEMENTED_CI_VALIDATED_PENDING_LOCAL_SMOKE`.

Remaining:
stable pre-smoke exact-head CI and one primary-workstation persistent/reopen
memory smoke.


---

## 2026-09-19 — Gate 016 local persistent/reopen smoke passed

Primary-workstation smoke ran at Engineering AI head:
`e240f82176a18f21a81bae9318b7d4b714ffa023`.

Result:
- `PASS_LOCAL_PERSISTENT_REOPEN_MEMORY`;
- database created and reopened;
- integrity records: 3 initial / 3 reopened / 4 final;
- stored record hash preserved;
- exact supersession chain revision 1 -> 2;
- deterministic search returned expected records;
- model truth promotion: false;
- automatic context injection: false;
- vector search: false;
- temporary database removed on exit;
- physical validation remained `PHYSICAL_NOT_EXECUTED`;
- exit 0.

Gate 016 state:
`IMPLEMENTED_VALIDATED_PENDING_HUMAN_APPROVAL`.

Next:
final acceptance-state generic + strict exact-head CI, scope review, and exact-SHA
human squash-merge approval for PR #32.


---

## 2026-09-19 — Gate 016 accepted and merged

Final approved PR head:
`2f503df7750eafb4e19fed796dc2a6642d509616`.

Final validation:
- deterministic tests: `161/161 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- primary-workstation persistent/reopen memory smoke: `PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`a71c084078ae7c12361555eaed2f3d7c887d61d6`.

Issue #31 closed.

Accepted capability:
- local append-only SQLite decision/evidence memory;
- immutable exact supersession revisions;
- canonical SHA-256 integrity;
- project isolation;
- deterministic bounded search;
- model memory remains advisory;
- accepted ADRs remain human-only;
- physical validation class preserved.

ADR-0015 is accepted through Gate 016 merge.

Gate 016 state:
`ACCEPTED_MERGED`.

---

## 2026-09-19 — Gate 017 retrieval layer opened

Issue:
`#33 — Gate 017 — Retrieval layer`.

Branch:
`gate-017-retrieval-layer`.

Base:
Gate 016 squash merge
`a71c084078ae7c12361555eaed2f3d7c887d61d6`.

Implemented initial scope:
- typed project-scoped RetrievalRequest/ContextPackage;
- latest revision by default;
- MODEL/ADVISORY default exclusion;
- proposed ADR default exclusion;
- explicit advisory/proposed/history opt-in with labels preserved;
- deterministic lexical relevance ranking;
- bounded candidate/result/context budgets;
- no record truncation;
- provenance/evidence/source refs and integrity SHA preserved;
- memory integrity failures fail closed;
- no automatic Blackboard/model prompt injection;
- retrieval context JSON Schema;
- deterministic recall@3 benchmark against Gate 016 exact-substring search;
- semantic/vector backend remains
  `DEFERRED_NOT_JUSTIFIED`.

ADR-0016 added as `PROPOSED_GATE_017`.

Next:
open draft PR and validate retrieval implementation + benchmark before any
consideration of semantic/vector retrieval.


---

## 2026-09-19 — Gate 017 retrieval implementation validated

Validated implementation head:
`9e5874ec19b15b7d429f3fcb6752f73b3e8e7a28`.

Validated:
- deterministic provenance-preserving lexical retrieval;
- latest-only default;
- MODEL/ADVISORY default exclusion;
- PROPOSED ADR default exclusion;
- explicit advisory/proposed/history opt-in with labels preserved;
- stable lexical relevance ranking;
- bounded candidate/result/context budgets;
- no per-record truncation;
- provenance/evidence/source refs and integrity SHA preserved;
- project isolation;
- memory integrity failure fail-closed;
- retrieval context JSON Schema;
- no write/vector/context-injection API;
- deterministic recall benchmark smoke under CI;
- Supervisor-owned same-project retrieval boundary;
- cross-project Supervisor retrieval rejection;
- no automatic Blackboard/handoff creation.

Validation:
- deterministic tests: `178/178 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.

Semantic/vector backend remains:
`DEFERRED_NOT_JUSTIFIED`.

Gate 017 state:
`IMPLEMENTED_CI_VALIDATED_PENDING_LOCAL_BENCHMARK`.

Remaining:
stable pre-smoke exact-head CI and one primary-workstation retrieval
benchmark/smoke with metrics captured.


---

## 2026-09-19 — Gate 017 primary-workstation retrieval benchmark passed

Stable pre-smoke PR head:
`c5c2c5648efa7b12447ad5bffed9451c7b4c2868`.

Pre-smoke validation:
- generic workflow run `35463811833`: `PASS`;
- strict exact-head workflow run `35463811817`: `PASS`;
- deterministic regression: `178/178 PASS`;
- exact revision verification: `PASS`.

Primary-workstation benchmark:
- script: `scripts/gate017_retrieval_benchmark.py`;
- state: `PASS_DETERMINISTIC_RETRIEVAL_BENCHMARK`;
- exit code: `0`;
- k: `3`;
- baseline mean recall@3: `0.25`;
- retrieval mean recall@3: `1.0`;
- improved relevant cases: `3`;
- safety: `PASS`;
- retrieval not worse on every relevant case: `PASS`;
- automatic context injection: `false`;
- temporary database removed on exit: `true`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

Relevant benchmark cases:
- append-memory-noncontiguous: `0.0 -> 1.0`;
- windows-cleanup-reordered: `0.0 -> 1.0`;
- shape-validation-gap: `0.0 -> 1.0`;
- source-contiguous-baseline: `1.0 -> 1.0`.

Safety-only cases:
- advisory-safety: excluded as required;
- proposed-adr-safety: excluded as required.

Conclusion:
the deterministic lexical retrieval baseline materially improves measured recall while
preserving provenance and safety. Semantic/vector retrieval remains
`DEFERRED_NOT_JUSTIFIED`; no embeddings/vector database are added in Gate 017.

Gate 017 state:
`IMPLEMENTED_VALIDATED_PENDING_FINAL_ACCEPTANCE_CI`.

Next:
run final generic and strict exact-head CI on the post-benchmark evidence/status head,
perform final scope review, mark PR #34 ready for review, then request explicit human
exact-SHA squash-merge approval.


---

## 2026-09-19 — Gate 017 final acceptance checkpoint passed

Post-benchmark evidence head:
`578510beed676a1d6b71c8842e0ebace27564301`.

Final acceptance validation:
- generic workflow run `35464308651`: `PASS`;
- strict exact-head workflow run `35464308598`: `PASS`;
- deterministic regression: `178/178 PASS`;
- exact revision verification: `PASS`.

Final scope review:
`PASS`.

Confirmed absent from Gate 017:
- embeddings/vector database or semantic backend;
- automatic RAG/model prompt injection;
- memory write/update/delete through retrieval;
- evidence promotion through retrieval;
- unrestricted shell;
- model ownership of policy, permissions, state or tools;
- Gate 018 knowledge-lifecycle implementation.

Semantic/vector backend remains:
`DEFERRED_NOT_JUSTIFIED`.

Gate 017 state prepared for final documentation-head recheck:
`IMPLEMENTED_VALIDATED_PENDING_HUMAN_APPROVAL`.

ADR-0016 remains:
`PROPOSED_GATE_017`
until explicit exact-SHA human approval and squash merge.

Next:
run generic and strict exact-head CI on the final documentation-only head. If green,
mark PR #34 ready for review and request exact-SHA squash-merge approval.


---

## 2026-09-20 — Gate 017 accepted and merged

Final approved PR head:
`ee9f5ad0861a5188f8aa4086098f6f14a4fb74c3`.

Final validation:
- deterministic tests: `178/178 PASS`;
- final generic workflow run `35464391333`: `PASS`;
- final strict exact-head workflow run `35464391322`: `PASS`;
- exact revision verification: `PASS`;
- primary-workstation retrieval benchmark: `PASS_DETERMINISTIC_RETRIEVAL_BENCHMARK`;
- baseline mean recall@3: `0.25`;
- retrieval mean recall@3: `1.0`;
- safety/not-worse checks: `PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`f416799ca95f3bbe124b7bbfa62a86c1be0d1cbc`.

Issue #33 closed.

Accepted capability:
- deterministic project-scoped lexical retrieval over Gate 016 memory;
- latest revisions by default;
- MODEL/ADVISORY and PROPOSED ADR records excluded by default;
- explicit labelled opt-in for advisory/proposed/history;
- bounded candidate/result/context budgets with no per-record truncation;
- provenance/evidence/source references and integrity SHA preserved;
- Supervisor-owned retrieval boundary;
- no automatic Blackboard/model context injection;
- semantic/vector backend remains `DEFERRED_NOT_JUSTIFIED`.

ADR-0016 state:
`ACCEPTED_GATE_017`.

Gate 017 state:
`ACCEPTED_MERGED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-20 — Gate 018 knowledge lifecycle opened

Issue:
`#35 — Gate 018 — Knowledge lifecycle`.

Branch:
`gate-018-knowledge-lifecycle`.

Base:
Gate 017 squash merge
`f416799ca95f3bbe124b7bbfa62a86c1be0d1cbc`.

Declared scope:
- typed lifecycle states for observations/evidence/accepted knowledge/stale or invalid knowledge;
- deterministic policy-qualified promotion;
- source/evidence/provenance/integrity preservation;
- append-only lifecycle history/supersession;
- deterministic source-revision drift detection;
- Supervisor-controlled lifecycle evaluation;
- schemas/tests/evidence and regression validation.

Explicitly out of scope:
- semantic/vector retrieval;
- automatic model/Blackboard context injection;
- model-owned promotion/permissions;
- silent Gate 016 UPDATE/DELETE;
- physical validation inference;
- online learning/fine-tuning;
- Gate 019 job queue;
- Gate 023 vision worker/Qwen3-VL integration;
- architecture/physics changes;
- external/cloud bridge.

Next:
create the initial synchronization checkpoint commit, open one draft PR for Issue #35,
then implement and validate the deterministic knowledge lifecycle.


---

## 2026-09-20 — Gate 018 deterministic knowledge lifecycle implemented

Initial implementation head:
`e679067ca060d3182d4c51b18229c5c0d780a02e`.

Implemented:
- separate append-only local SQLite lifecycle ledger;
- exact binding to immutable Gate 016 memory record/revision/SHA identities;
- lifecycle stages OBSERVATION / EVIDENCE / ACCEPTED / INVALIDATED;
- advisory-only observation inputs;
- HUMAN/SUPERVISOR lifecycle transition authority;
- current non-model evidence qualification;
- CONTROL/ADR excluded from lifecycle evidence promotion;
- source/evidence revision drift assessment;
- append-only invalidation;
- Supervisor-owned project-scoped lifecycle API;
- lifecycle-record and assessment JSON Schemas;
- deterministic local smoke script;
- no automatic model/Blackboard context injection;
- no physical-validation inference.

Validation:
- deterministic regression: `191/191 PASS`;
- generic workflow run `35513495763`: `PASS`;
- strict exact-head workflow run `35513495762`: `PASS`.

Scope review found one lifecycle completeness gap:
after INVALIDATED there was no path to re-qualify the same knowledge identity
when updated evidence became available.

---

## 2026-09-20 — Gate 018 requalification gap closed

Corrected implementation head:
`72569edf34af12b78c0d3f04f6905c61e1d310d6`.

Correction:
- INVALIDATED knowledge may be re-qualified only with current evidence/source
  revisions;
- requalification appends a new EVIDENCE revision;
- acceptance then appends a new ACCEPTED revision;
- complete history remains intact;
- no old acceptance or invalidation is rewritten.

Additional boundary test:
an accepted human CONTROL/ADR memory record cannot be supplied as lifecycle
evidence, so the lifecycle cannot bypass human control authority.

Gate 023 isolation:
model-name strings in lifecycle fixtures were changed to generic vision fixtures;
no Qwen3-VL runtime, model route or vision worker is implemented in Gate 018.

Validation:
- deterministic regression: `193/193 PASS`;
- generic workflow run `35513601561`: `PASS`;
- strict exact-head workflow run `35513601565`: `PASS`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

ADR-0017 added as `PROPOSED_GATE_018`.

Next:
synchronize architecture/status/evidence documentation, re-run exact-head CI,
then perform one primary-workstation local lifecycle smoke.


---

## 2026-09-20 — Gate 018 primary-workstation lifecycle smoke passed

Exact Engineering AI head:
`7d23cfd62e616659a793d21c7cb22ee7af0ca388`.

Local primary-workstation result:
`PASS_APPEND_ONLY_KNOWLEDGE_LIFECYCLE`.

Observed:
- accepted state before source change: `ACCEPTED_CURRENT`;
- observation validation class: `ADVISORY`;
- source revision: `1 -> 2`;
- stale assessment: `STALE_SOURCE_REVISION`;
- explicit invalidation appended as lifecycle revision `4`;
- final assessment: `INVALIDATED`;
- lifecycle history revisions: `1 / 2 / 3 / 4`;
- lifecycle history stages:
  `OBSERVATION / EVIDENCE / ACCEPTED / INVALIDATED`;
- Gate 016 memory integrity: `PASS`;
- Gate 018 lifecycle integrity: `PASS`;
- automatic context injection: `false`;
- semantic/vector backend: `DEFERRED_NOT_JUSTIFIED`;
- physical validation inferred: `false`;
- physical validation: `PHYSICAL_NOT_EXECUTED`;
- script exit: `0`;
- repository branch remained clean and exact head unchanged.

Gate 018 state:
`IMPLEMENTED_VALIDATED_PENDING_FINAL_ACCEPTANCE_CI`.

Next:
record the smoke evidence, run final generic + strict exact-head CI on the
post-smoke documentation head, complete final scope review, then stop at
explicit human exact-SHA squash-merge approval.


---

## 2026-09-20 — Gate 018 final acceptance checkpoint passed

Post-smoke evidence head:
`6e02671de1d774f679372419ef24ba6d7db4b278`.

Validation:
- deterministic regression: `193/193 PASS`;
- generic workflow run `35513857456`: `PASS`;
- strict exact-head workflow run `35513857442`: `PASS`;
- exact revision verification: `PASS`;
- primary-workstation lifecycle smoke:
  `PASS_APPEND_ONLY_KNOWLEDGE_LIFECYCLE`.

Final scope review:
`PASS`.

Confirmed absent from Gate 018 runtime:
- Qwen3-VL/vision worker routing or model integration;
- embeddings/vector/semantic backend;
- automatic model or Blackboard context injection;
- PHYSICAL_PASS synthesis;
- generic SQL mutation API;
- Gate 019 queue implementation;
- Gate 023 vision implementation;
- architecture/physics/fabrication/release authority expansion.

SQLite UPDATE/DELETE occurrences are limited to append-only prohibition triggers
and tamper/fail-closed tests.

Gate 018 state:
`IMPLEMENTED_VALIDATED_PENDING_HUMAN_APPROVAL`.

ADR-0017 remains:
`PROPOSED_GATE_018`
until explicit exact-SHA human approval and squash merge.

Next:
run one final generic + strict exact-head CI on the final documentation-only
head, mark PR #36 ready for review if green, then stop at human approval.


---

## 2026-09-20 — Gate 018 accepted and merged

Final approved PR head:
`294bf424061102b4ee82c2f6e760ca9135330e94`.

Final validation:
- deterministic regression: `193/193 PASS`;
- generic workflow run `35513932000`: `PASS`;
- strict exact-head workflow run `35513931970`: `PASS`;
- exact revision verification: `PASS`;
- primary-workstation lifecycle smoke:
  `PASS_APPEND_ONLY_KNOWLEDGE_LIFECYCLE`;
- final scope review: `PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`75ee907446e952fbfc8a53006c1fd65f1257faea`.

Issue #35 closed as completed.

Accepted capability:
- separate append-only knowledge lifecycle ledger;
- exact immutable Gate 016 memory revision/SHA bindings;
- OBSERVATION / EVIDENCE / ACCEPTED / INVALIDATED stages;
- deterministic source/evidence staleness detection;
- append-only invalidation;
- current-evidence requalification after invalidation;
- model observations remain ADVISORY;
- CONTROL/ADR lifecycle evidence bypass prohibited;
- no physical validation inference;
- no automatic context injection.

ADR-0017 state:
`ACCEPTED_GATE_018`.

Gate 018 state:
`ACCEPTED_MERGED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-20 — Gate 019 persisted job queue opened

Issue:
`#37 — Gate 019 — Persisted job queue`.

Branch:
`gate-019-persisted-job-queue`.

Base:
Gate 018 squash merge
`75ee907446e952fbfc8a53006c1fd65f1257faea`.

Declared scope:
- local persistent Supervisor-owned job queue;
- deterministic FIFO claim ordering;
- persistence across process close/reopen;
- bounded retry/attempt state persistence;
- explicit timeout/run-deadline metadata;
- fail-closed recovery for interrupted RUNNING jobs;
- WAITING_FOR_APPROVAL persistence without automatic execution;
- terminal-state preservation;
- project isolation, integrity checks, schemas/tests/evidence;
- one primary-workstation reopen/recovery smoke.

Explicitly out of scope:
- Gate 020 scheduled/overnight runner;
- automatic approval acquisition;
- daemon/service lifecycle;
- parallel/distributed workers;
- external/cloud queue;
- external AI bridge;
- semantic/vector retrieval;
- Vision/CAD workers;
- architecture/physics/fabrication/release authority changes.

Next:
publish the initial synchronization checkpoint, open one draft PR for Issue #37,
then implement the persisted queue without broadening execution authority.


---

## 2026-09-20 — Gate 019 persisted job queue implemented

Initial implementation head:
`63b612fd64e7317cf4dad218bce63f130f966ae8`.

Implemented:
- local SQLite append-only queue-event ledger;
- complete schema-valid job snapshot per event;
- deterministic FIFO claim ordering;
- retry results re-entering at queue tail;
- persisted attempts/retry state;
- per-run timeout/deadline metadata;
- late-result deadline rejection to BLOCKED;
- fail-closed interrupted/expired RUNNING recovery;
- WAITING_FOR_APPROVAL persistence;
- terminal-state preservation;
- project isolation;
- SHA-256 event integrity and exact supersession chain;
- Supervisor queue surface;
- JSON Schema and deterministic smoke harness.

Validation:
- deterministic regression: `208/208 PASS`;
- generic workflow run `35516817721`: `PASS`;
- strict exact-head workflow run `35516817717`: `PASS`.

API scope review tightened the approval boundary: low-level queue code should
not expose a public option that can resume WAITING_FOR_APPROVAL.

---

## 2026-09-20 — Gate 019 approval-resume boundary tightened

Corrected head:
`f65ca9c7cce403511a2e685dd6baf8b0fbc70a0e`.

Correction:
- public queue begin_run accepts QUEUED only;
- approval-waiting resume moved to an internal queue primitive;
- Supervisor claim_approved_persisted_job requires the exact waiting action,
  a named human approver, and a fresh current PolicyEngine ALLOW decision;
- queue still performs no tool execution or approval granting.

Validation:
- deterministic regression: `208/208 PASS`;
- generic workflow run `35516884394`: `PASS`;
- strict exact-head workflow run `35516884392`: `PASS`.

Final acceptance-test head:
`983dafc9da4df41094961d4ce438cec7f4c8623e`.

Additional tests:
- direct low-level resume of WAITING_FOR_APPROVAL is rejected;
- Gate 019 smoke script executes under regression CI.

Validation:
- deterministic regression: `209/209 PASS`;
- generic workflow run `35516965090`: `PASS`;
- strict exact-head workflow run `35516965135`: `PASS`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

ADR-0018 added as `PROPOSED_GATE_019`.

Next:
synchronize architecture/status/evidence documentation, re-run exact-head CI,
then execute one primary-workstation persistence/reopen/recovery smoke.


---

## 2026-09-20 — Gate 019 primary-workstation persistence/reopen smoke passed

Exact Engineering AI head:
`f423f16d4895049121026386f37a9c9c68b8bf89`.

Local result:
`PASS_PERSISTED_JOB_QUEUE_REOPEN_RECOVERY`.

Observed:
- database created: `true`;
- database reopened: `true`;
- FIFO retry tail preserved: `true`;
- retry attempts preserved after reopen: `1`;
- retry final state: `PASS`;
- WAITING_FOR_APPROVAL survived reopen: `true`;
- explicitly approved job final state: `PASS`;
- interrupted RUNNING recovery event: `INTERRUPTED_RECOVERY`;
- interrupted job final state: `BLOCKED`;
- queue events checked: `13`;
- queue jobs checked: `3`;
- queue integrity: `PASS`;
- automatic approval: `false`;
- scheduled execution: `false`;
- distributed workers: `false`;
- physical validation: `PHYSICAL_NOT_EXECUTED`;
- script exit: `0`;
- repository branch remained clean and exact head unchanged.

Gate 019 state:
`IMPLEMENTED_VALIDATED_PENDING_FINAL_ACCEPTANCE_CI`.

Next:
record smoke evidence, run final generic + strict exact-head CI on the
post-smoke documentation head, complete final scope review, then stop at
explicit human exact-SHA squash-merge approval.


---

## 2026-09-20 — Gate 019 post-smoke predecessor-integrity hardening

The first primary-workstation smoke passed on:
`f423f16d4895049121026386f37a9c9c68b8bf89`.

Subsequent final scope review identified one fail-closed robustness gap:
`list_current()` validated each latest event hash, while full predecessor-chain
validation occurred through get()/history()/verify_integrity() and again before
a claim. A control-state listing should itself fail closed if an older queue
event has been corrupted.

Hardening head:
`5f1f3a480042180b31b75df50a8736f3386e1ac7`.

Correction:
- list_current() now validates the complete append-only history for every
  returned job before exposing current control state;
- a regression test tampers an old ENQUEUED predecessor while leaving the latest
  event untouched and requires list_current() to fail closed.

Validation:
- deterministic regression: `210/210 PASS`;
- generic workflow run `35519588215`: `PASS`;
- strict exact-head workflow run `35519588222`: `PASS`;
- runtime scope review: `PASS`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

Because runtime code changed after the first primary-workstation smoke, that
smoke is retained as valid historical evidence but is not presented as exact
validation of the hardened runtime.

Next:
freeze documentation, re-run CI, then repeat the short primary-workstation
persistence/reopen smoke on the hardened runtime before final acceptance.


---

## 2026-09-20 — Gate 019 repeat primary-workstation smoke passed on hardened runtime

Exact Engineering AI head:
`165e85404e42f1db457572842cf21fc80d08f4da`.

Local result:
`PASS_PERSISTED_JOB_QUEUE_REOPEN_RECOVERY`.

Observed:
- database created: `true`;
- database reopened: `true`;
- FIFO retry tail preserved: `true`;
- retry attempts preserved after reopen: `1`;
- retry final state: `PASS`;
- WAITING_FOR_APPROVAL survived reopen: `true`;
- explicitly approved job final state: `PASS`;
- interrupted RUNNING recovery event: `INTERRUPTED_RECOVERY`;
- interrupted job final state: `BLOCKED`;
- queue events checked: `13`;
- queue jobs checked: `3`;
- queue integrity: `PASS`;
- automatic approval: `false`;
- scheduled execution: `false`;
- distributed workers: `false`;
- physical validation: `PHYSICAL_NOT_EXECUTED`;
- script exit: `0`;
- repository branch remained clean and exact head unchanged.

This repeat smoke validates the post-hardening runtime that performs full
predecessor-chain integrity validation during current-state reads.

Gate 019 state:
`IMPLEMENTED_VALIDATED_PENDING_FINAL_ACCEPTANCE_CI`.

Next:
record final local evidence, run final acceptance CI and scope review, prepare
the final documentation-only acceptance head, then stop at explicit exact-SHA
human squash-merge approval.


---

## 2026-09-20 — Gate 019 final acceptance checkpoint passed

Post-repeat-smoke evidence head:
`1248e2a1fd13f7d1aeb12ee3b523848d3e9dc503`.

Validation:
- deterministic regression: `210/210 PASS`;
- generic workflow run `35521519407`: `PASS`;
- strict exact-head workflow run `35521519425`: `PASS`;
- exact revision verification: `PASS`;
- repeat primary-workstation persistence/reopen smoke:
  `PASS_PERSISTED_JOB_QUEUE_REOPEN_RECOVERY`.

Final runtime scope review:
`PASS`.

Confirmed absent from Gate 019 runtime:
- scheduler/cron/time-of-day runner;
- daemon/service lifecycle;
- automatic approval granting;
- queue-owned tool execution;
- distributed workers;
- semantic/vector backend;
- vision/Qwen runtime integration;
- PHYSICAL_PASS synthesis;
- generic SQL write API;
- architecture/physics/fabrication/release authority expansion.

Gate 019 state:
`IMPLEMENTED_VALIDATED_PENDING_HUMAN_APPROVAL`.

ADR-0018 remains:
`PROPOSED_GATE_019`
until explicit exact-SHA human approval and squash merge.

Next:
run one final generic + strict exact-head CI on the final documentation-only
head, mark PR #38 ready for review if green, then stop at human approval.


---

## 2026-09-20 — Gate 019 accepted and merged

Final approved PR head:
`a12dc51c7022ce218efb571fa7d34f06ea6753b1`.

Final validation:
- deterministic regression: `210/210 PASS`;
- generic workflow run `35521603454`: `PASS`;
- strict exact-head workflow run `35521603447`: `PASS`;
- exact revision verification: `PASS`;
- primary-workstation hardened-runtime smoke:
  `PASS_PERSISTED_JOB_QUEUE_REOPEN_RECOVERY`;
- final runtime scope review: `PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`f8e4a6c7893c67bbc81c98bb89698ab6b91553c7`.

Issue #37 closed as completed.

Accepted capability:
- local append-only persisted Supervisor job queue;
- deterministic FIFO claim ordering;
- bounded retry/attempt persistence;
- timeout/deadline state;
- WAITING_FOR_APPROVAL persistence;
- Supervisor-only named-approval resume;
- fail-closed interrupted/expired RUNNING recovery to BLOCKED;
- terminal-state preservation;
- project isolation;
- exact predecessor-chain and SHA-256 integrity.

ADR-0018 state:
`ACCEPTED_GATE_019`.

Gate 019 state:
`ACCEPTED_MERGED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-20 — Gate 020 scheduled/overnight engineering runs opened

Issue:
`#39 — Gate 020 — Scheduled/overnight engineering runs`.

Branch:
`gate-020-scheduled-overnight-runs`.

Base:
Gate 019 squash merge
`f8e4a6c7893c67bbc81c98bb89698ab6b91553c7`.

Declared scope:
- typed local persisted one-shot schedules with explicit UTC due times;
- deterministic due-run selection;
- bounded unattended sessions over the accepted Gate 019 queue;
- unattended execution only for current Supervisor/PolicyEngine autonomous
  actions and explicitly supplied narrow tools;
- approval-required jobs preserved WAITING_FOR_APPROVAL without tool execution;
- forbidden/non-autonomous work blocked without execution;
- bounded max-jobs and max-session-duration budgets;
- Gate 019 interrupted RUNNING recovery before new unattended claims;
- append-only scheduled-run/session history;
- deterministic summary counts for PASS / FAIL / BLOCKED /
  WAITING_FOR_APPROVAL / CANCELLED plus evidence references;
- one-shot local CLI/harness suitable for later invocation by a user-selected
  OS scheduler.

Explicitly out of scope:
- installing/configuring Windows Task Scheduler/systemd/launchd;
- long-lived daemon/service;
- remote/cloud scheduler;
- automatic approval acquisition;
- parallel/distributed workers;
- unrestricted shell;
- external AI bridge;
- semantic/vector retrieval;
- Vision/CAD/image workers;
- architecture/physics/fabrication/release authority changes.

Next:
publish the initial synchronization checkpoint, open one draft PR for Issue #39,
then implement Gate 020 without broadening Supervisor authority.


---

## 2026-09-20 — Gate 020 scheduled/unattended run layer implemented

Initial implementation head:
`d455738ee9522aa7c1c2671cc3cd9bf6f1e567e5`.

Implemented:
- local append-only SQLite one-shot schedule/session ledger;
- explicit timezone-aware due_at;
- deterministic due selection by due_at then append sequence;
- schedule allowed_actions as a narrowing constraint only;
- current Supervisor/PolicyEngine re-authorization before every unattended
  execution;
- unattended tool execution only for current ALLOW plus schedule allow-list;
- approval-required jobs -> WAITING_FOR_APPROVAL with no tool call;
- denied/forbidden jobs -> BLOCKED with no tool call;
- autonomous schedule-unlisted jobs remain QUEUED;
- ambiguous multi-action jobs block without tool execution;
- missing tool bindings block fail-closed;
- bounded max-job and max-session-duration budgets;
- Gate 019 interrupted RUNNING recovery before new work;
- interrupted scheduled sessions terminally block on next invocation;
- deterministic session summaries with state counts and evidence refs;
- physical validation summary fixed to PHYSICAL_NOT_EXECUTED;
- JSON Schema, deterministic tests and local smoke harness.

Validation:
- deterministic regression: `226/226 PASS`;
- generic workflow run `35522348903`: `PASS`;
- strict exact-head workflow run `35522348911`: `PASS`.

Follow-up chronology hardening head:
`a61a3e1fa16341265396b66a9db73700bfaabc7c`.

Added:
- completed_at cannot precede started_at;
- regression coverage for invalid summary chronology.

Validation:
- deterministic regression: `227/227 PASS`;
- generic workflow run `35522438419`: `PASS`;
- strict exact-head workflow run `35522438328`: `PASS`.

Runtime scope review:
`PASS`.

Confirmed absent:
- Windows Task Scheduler/systemd/launchd installation;
- daemon/service implementation;
- automatic approval API;
- unrestricted shell;
- remote/cloud scheduler;
- distributed workers;
- semantic/vector backend;
- vision runtime;
- PHYSICAL_PASS synthesis;
- generic SQL write API.

ADR-0019 added as `PROPOSED_GATE_020`.

Next:
synchronize architecture/status/evidence documentation, re-run exact-head CI,
then perform one primary-workstation scheduled/unattended smoke.


---

## 2026-09-20 — Gate 020 primary-workstation scheduled/unattended smoke passed

Exact Engineering AI head:
`82ead2e02f381a9ce988263058662c2614b23428`.

Local result:
`PASS_SCHEDULED_UNATTENDED_RUN_SESSION`.

Observed:
- due schedule executed: `true`;
- future schedule remained SCHEDULED: `true`;
- autonomous schedule-allowed job final state: `PASS`;
- approval-required job final state: `WAITING_FOR_APPROVAL`;
- forbidden job final state: `BLOCKED`;
- autonomous schedule-unlisted job final state: `QUEUED`;
- interrupted prior RUNNING job final state: `BLOCKED`;
- summary counts: PASS=1 / BLOCKED=2 / WAITING_FOR_APPROVAL=1 /
  FAIL=0 / CANCELLED=0 / QUEUED=0;
- summary evidence refs: `ev-gate020-read`;
- approval tool calls: none;
- forbidden tool calls: none;
- schedule-unlisted tool calls: none;
- schedule database created and reopened: `true`;
- schedule events checked before/after reopen: `4 / 4`;
- schedule integrity: `PASS`;
- queue events checked: `13`;
- queue integrity: `PASS`;
- automatic approval: `false`;
- OS scheduler installation: `false`;
- daemon/service: `false`;
- distributed workers: `false`;
- physical validation: `PHYSICAL_NOT_EXECUTED`;
- script exit: `0`;
- repository branch remained clean and exact head unchanged.

Gate 020 state:
`IMPLEMENTED_VALIDATED_PENDING_FINAL_ACCEPTANCE_CI`.

Next:
record local smoke evidence, run final acceptance CI and runtime scope review,
prepare the final documentation-only acceptance head, then stop at explicit
exact-SHA human squash-merge approval.


---

## 2026-09-20 — Gate 020 final acceptance checkpoint passed

Post-smoke evidence head:
`42e9fd0fe6ea9db05751a78e2a0ecd5327fe32d1`.

Validation:
- deterministic regression: `227/227 PASS`;
- generic workflow run `35523735071`: `PASS`;
- strict exact-head workflow run `35523735159`: `PASS`;
- exact revision verification: `PASS`;
- primary-workstation scheduled/unattended smoke:
  `PASS_SCHEDULED_UNATTENDED_RUN_SESSION`.

Final runtime scope review:
`PASS`.

Confirmed absent from Gate 020 runtime:
- Windows Task Scheduler/systemd/launchd installation;
- long-lived daemon/service lifecycle;
- automatic approval granting;
- unrestricted shell;
- distributed worker runtime;
- external/cloud scheduler;
- semantic/vector backend;
- vision/Qwen runtime integration;
- PHYSICAL_PASS synthesis;
- generic SQL write API;
- architecture/physics/fabrication/release authority expansion.

Gate 020 state:
`IMPLEMENTED_VALIDATED_PENDING_HUMAN_APPROVAL`.

ADR-0019 remains:
`PROPOSED_GATE_020`
until explicit exact-SHA human approval and squash merge.

Next:
run one final generic + strict exact-head CI on the final documentation-only
head, mark PR #40 ready for review if green, then stop at human approval.


---

## 2026-09-20 — Gate 020 accepted and merged

Final approved PR head:
`ea05b8625c93cacbadca5a20c9a8126dc590dff9`.

Final validation:
- deterministic regression: `227/227 PASS`;
- generic workflow run `35523817968`: `PASS`;
- strict exact-head workflow run `35523817970`: `PASS`;
- exact revision verification: `PASS`;
- primary-workstation smoke:
  `PASS_SCHEDULED_UNATTENDED_RUN_SESSION`;
- final runtime scope review: `PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`5e4fb761ed4f7c8730b1ddf9acc3d0a842751e35`.

Issue #39 closed as completed.

ADR-0019 state:
`ACCEPTED_GATE_020`.

Gate 020 state:
`ACCEPTED_MERGED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-20 — Gate 021 external controlled reasoning/review bridge opened

Issue:
`#41 — Gate 021 — External controlled reasoning/review bridge`.

Branch:
`gate-021-external-controlled-review-bridge`.

Base:
Gate 020 squash merge
`5e4fb761ed4f7c8730b1ddf9acc3d0a842751e35`.

Declared scope:
- provider-neutral external consultation interface;
- explicit bounded outbound context manifest only;
- current Supervisor/PolicyEngine external_disclosure authorization;
- named human approval where current policy requires it;
- request/response identity, provider metadata and SHA-256 audit;
- external response classified ADVISORY only;
- fail-closed provider error/malformed response/budget behavior;
- local core remains fully functional offline and without bridge.

Explicitly out of scope:
- real OpenAI/ChatGPT credential setup or production network call;
- automatic external disclosure approval;
- Gate 022 MCP/tool exposure;
- unrestricted file upload/shell/filesystem/Git authority;
- semantic/vector retrieval;
- Vision/CAD/image workers;
- architecture/physics/fabrication/release authority changes.

Next:
publish synchronization checkpoint and open one draft PR for Gate 021.


---

## 2026-09-20 — Gate 021 controlled external advisory bridge implemented

Initial implementation head:
`8ed0f345ef7f2904041f1b14a08403b846f7141b`.

Implemented:
- provider-neutral external review protocol;
- explicit project-scoped outbound context items;
- exact source refs, context SHA-256 and character counts;
- current external_disclosure policy check through Supervisor/PolicyEngine;
- named approval enforcement where required;
- zero provider calls on missing approval or policy denial;
- provider request surface with no local tools/filesystem/shell/Git/queue/scheduler;
- ADVISORY-only external review result;
- evidence_eligible=false and PHYSICAL_NOT_EXECUTED;
- append-only SQLite consultation metadata ledger;
- request/response hashes and provider/model identity audit;
- no outbound context or purpose text persisted;
- provider exception text omitted from persistent audit;
- malformed/oversized/provider failures fail closed;
- fake-provider smoke harness, no real network dependency.

Validation:
- deterministic regression: `245/245 PASS`;
- generic workflow run `35524343520`: `PASS`;
- strict exact-head workflow run `35524343416`: `PASS`.

Hardening head:
`bca9381cf10462cc66e0b92c324fb0225acaada7`.

Added:
- hard bounds for purpose/source_ref/kind outbound text;
- deeply immutable persisted manifest snapshots;
- corresponding regression tests.

Hardening CI exposed one test-only defect:
- generic run `35524431902`: `FAIL`;
- strict run `35524431903`: `FAIL`;
- deterministic suite ran 247 tests with one error;
- the new test attempted `json.dumps(dict(mappingproxy))` instead of using the
  public serializable snapshot representation;
- no runtime bridge failure was indicated.

Corrected head:
`f6ed7a9a36c75f08248efe6fbe8148b5fa75a2c8`.

Correction:
- regression now validates the public `as_dict()` audit representation.

Validation:
- deterministic regression: `247/247 PASS`;
- generic workflow run `35524489887`: `PASS`;
- strict exact-head workflow run `35524489903`: `PASS`.

Runtime scope review:
`PASS`.

Confirmed absent:
- concrete external network client;
- credentials/API-key handling;
- local tool/filesystem/shell/Git authority exposed to provider;
- automatic approval;
- MCP runtime;
- semantic/vector backend;
- PHYSICAL_PASS synthesis.

ADR-0020 added as `PROPOSED_GATE_021`.

Next:
synchronize architecture/status/evidence documentation, re-run exact-head CI,
then perform one primary-workstation fake-provider smoke.


---

## 2026-09-20 — Gate 021 primary-workstation fake-provider smoke passed

Exact Engineering AI head:
`306466507f5ead228b4efd7194df9a85512d80cf`.

Local result:
`PASS_EXTERNAL_CONTROLLED_ADVISORY_BRIDGE`.

Observed:
- unapproved status: `NEEDS_HUMAN_APPROVAL`;
- unapproved provider called: `false`;
- approved status: `PASS`;
- approved provider called: `true`;
- provider call count: `1`;
- exact explicit context sent: `true`;
- outbound context persisted: `false`;
- request manifest hash recorded: `true`;
- response hash recorded: `true`;
- review authority: `ADVISORY`;
- review evidence eligible: `false`;
- tool surface exposed: `false`;
- ledger database created and reopened: `true`;
- ledger events checked before/after reopen: `4 / 4`;
- ledger integrity: `PASS`;
- real external network call: `false`;
- automatic external approval: `false`;
- physical validation: `PHYSICAL_NOT_EXECUTED`;
- script exit: `0`;
- repository branch remained clean and exact head unchanged.

This smoke validates the actual Gate 021 runtime on the primary Windows
workstation without any real external disclosure or network dependency.

Gate 021 state:
`IMPLEMENTED_VALIDATED_PENDING_FINAL_ACCEPTANCE_CI`.

Next:
record local smoke evidence, run final acceptance CI and runtime scope review,
prepare the final documentation-only acceptance head, then stop at explicit
exact-SHA human squash-merge approval.


---

## 2026-09-20 — Gate 021 final acceptance checkpoint passed

Post-smoke evidence head:
`cf57c13890637d3e1d072e0d83e66f97cb13e365`.

Validation:
- deterministic regression: `247/247 PASS`;
- generic workflow run `35525232870`: `PASS`;
- strict exact-head workflow run `35525232786`: `PASS`;
- exact revision verification: `PASS`;
- primary-workstation fake-provider smoke:
  `PASS_EXTERNAL_CONTROLLED_ADVISORY_BRIDGE`.

Final runtime scope review:
`PASS`.

Confirmed absent from Gate 021 runtime:
- concrete external network client;
- credentials/API-key handling;
- local tool/filesystem/shell/Git authority exposed to provider;
- automatic approval granting;
- MCP runtime;
- semantic/vector backend;
- PHYSICAL_PASS synthesis;
- architecture/physics/fabrication/release authority expansion.

Gate 021 state:
`IMPLEMENTED_VALIDATED_PENDING_HUMAN_APPROVAL`.

ADR-0020 remains:
`PROPOSED_GATE_021`
until explicit exact-SHA human approval and squash merge.

Next:
run one final generic + strict exact-head CI on the final documentation-only
head, mark PR #42 ready for review if green, then stop at human approval.


---

## 2026-09-20 — Gate 021 accepted and merged

Final approved PR head:
`75a87489affac650455a4456d3b982d1a3f1496a`.

Final validation:
- deterministic regression: `247/247 PASS`;
- generic workflow run `35525309946`: `PASS`;
- strict exact-head workflow run `35525309947`: `PASS`;
- exact revision verification: `PASS`;
- primary-workstation fake-provider smoke:
  `PASS_EXTERNAL_CONTROLLED_ADVISORY_BRIDGE`;
- final runtime scope review: `PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`992b2ac07ea1a192919be286eef026a2fa255e73`.

Issue #41 closed as completed.

ADR-0020 state:
`ACCEPTED_GATE_021`.

Gate 021 state:
`ACCEPTED_MERGED`.

Real external network call:
`NOT_RUN / NOT_REQUIRED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-20 — Gate 022 controlled MCP/tool exposure opened

Issue:
`#43 — Gate 022 — Controlled MCP/tool exposure`.

Branch:
`gate-022-controlled-mcp-tool-exposure`.

Base:
Gate 021 squash merge
`992b2ac07ea1a192919be286eef026a2fa255e73`.

Declared scope:
- typed explicit local capability registry;
- existing narrow local capability implementations only;
- explicit action mapping and project binding;
- current Supervisor/PolicyEngine authorization for every invocation;
- named approval when the mapped action currently requires it;
- zero tool calls for denied/missing-approval/unregistered capability requests;
- bounded request/response/timeout behavior;
- append-only invocation audit with request/response hashes;
- fake/in-process transport acceptance before any concrete MCP transport binding.

Explicitly out of scope:
- unrestricted MCP server exposing the workstation;
- generic shell/process command surface;
- arbitrary filesystem write/delete;
- generic Git mutation/push/merge;
- automatic human approval;
- credentials/secrets relay;
- public internet listener;
- semantic/vector retrieval;
- Vision/CAD/image workers;
- architecture/physics/fabrication/release authority expansion.

Next:
publish the Gate 022 synchronization checkpoint and open one draft PR for
Issue #43.


---

## 2026-09-20 — Gate 022 controlled registered tool exposure implemented

Initial implementation head:
`cc7a315fa58aa1be34daada3530305b6a918840c`.

Implemented:
- immutable project-scoped capability registry;
- deep-immutable public capability descriptors;
- JSON Schema input/output contracts;
- READ_ONLY-only side-effect acceptance;
- real `filesystem.read_text` binding over the accepted root-bounded adapter;
- real `git.status` binding over the accepted read-only Git adapter;
- current Supervisor/PolicyEngine action re-evaluation;
- named approval enforcement;
- zero-call unregistered/project/schema/budget rejection;
- bounded request/result serialization;
- fail-closed handler exception/timeout/invalid-output behavior;
- append-only SQLite invocation metadata ledger;
- request/result hashes without persisting request/result payloads;
- tamper-detection regression;
- fake-transport smoke harness.

Validation:
- deterministic regression: `266/266 PASS`;
- generic workflow run `35525960611`: `PASS`;
- strict exact-head workflow run `35525960343`: `PASS`.

Security review identified two authority/exposure gaps before local smoke:
1. returning local tool output through an external/MCP transport is itself
   `external_disclosure`; checking only `read_repository` was insufficient;
2. root-bounded arbitrary relative file reads were too broad for an external
   tool surface.

Hardening head:
`6a51beef91b1396a0afe816d4852287e95b4079b`.

Corrections:
- every registered invocation now requires both current
  `external_disclosure` ALLOW and mapped-action ALLOW;
- named approval metadata is preserved for the combined policy boundary;
- audit records a combined disclosure/action decision string;
- `filesystem.read_text` now requires an explicit configured relative-path
  allow-list reflected directly in its input schema;
- regression and smoke coverage prove disclosure-missing zero-call behavior and
  path allow-list rejection.

Validation:
- deterministic regression: `268/268 PASS`;
- generic workflow run `35526184987`: `PASS`;
- strict exact-head workflow run `35526184994`: `PASS`.

Runtime scope review:
`PASS`.

Confirmed absent:
- public network listener/concrete MCP server;
- dynamic import/eval/reflection-selected callables;
- generic shell/process command exposure;
- project filesystem write/delete exposure;
- Git mutation/push/merge exposure;
- automatic approval granting;
- credential/API-key relay;
- PHYSICAL_PASS synthesis.

ADR-0021 added as `PROPOSED_GATE_022`.

Next:
synchronize architecture/status/evidence documentation, re-run exact-head CI,
then perform one primary-workstation fake-transport smoke.


---

## 2026-09-20 — Gate 022 primary-workstation fake-transport smoke passed

Exact Engineering AI head:
`2d48e3cde3c2536565b90f65e39af2490fa8d53f`.

Local result:
`PASS_CONTROLLED_MCP_TOOL_EXPOSURE`.

Observed:
- registered capability count: `3`;
- handler objects exposed in listing: `false`;
- external-disclosure missing status: `NEEDS_HUMAN_APPROVAL`;
- external-disclosure missing handler called: `false`;
- registered read-only capability status: `PASS`;
- registered read-only result exact: `true`;
- unregistered status: `BLOCKED`;
- unregistered handler called: `false`;
- approval-missing status: `NEEDS_HUMAN_APPROVAL`;
- approval-missing handler called: `false`;
- named-approval status: `PASS`;
- named-approval handler call count: `1`;
- forbidden status: `BLOCKED`;
- forbidden handler called: `false`;
- request/result payload persisted: `false`;
- ledger database created and reopened: `true`;
- ledger events checked before/after reopen: `12 / 12`;
- ledger invocations checked: `6`;
- ledger integrity: `PASS`;
- generic shell surface: `false`;
- filesystem-write surface: `false`;
- Git-mutation surface: `false`;
- dynamic import/eval surface: `false`;
- public network listener: `false`;
- automatic approval: `false`;
- physical validation: `PHYSICAL_NOT_EXECUTED`;
- script exit: `0`;
- repository branch remained clean and exact head unchanged.

This smoke validates the hardened Gate 022 runtime on the primary Windows
workstation without a real MCP server, network listener or credential setup.

Gate 022 state:
`IMPLEMENTED_VALIDATED_PENDING_FINAL_ACCEPTANCE_CI`.

Next:
record local smoke evidence, run final acceptance CI and runtime scope review,
prepare the final documentation-only acceptance head, then stop at explicit
exact-SHA human squash-merge approval.


---

## 2026-09-20 — Gate 022 final acceptance checkpoint passed

Post-smoke evidence head:
`4a341253e2adcf74beeda2d01fe75b023178e0b7`.

Validation:
- deterministic regression: `268/268 PASS`;
- generic workflow run `35526705661`: `PASS`;
- strict exact-head workflow run `35526705659`: `PASS`;
- exact revision verification: `PASS`;
- primary-workstation fake-transport smoke:
  `PASS_CONTROLLED_MCP_TOOL_EXPOSURE`.

Final runtime scope review:
`PASS`.

Confirmed absent from Gate 022 runtime:
- public network listener/concrete MCP transport;
- dynamic import/eval/reflection-selected callables;
- generic shell/process command surface;
- project filesystem write/delete surface;
- Git mutation/push/merge surface;
- automatic approval granting;
- credentials/API-key relay;
- PHYSICAL_PASS synthesis;
- architecture/physics/fabrication/release authority expansion.

Confirmed present:
- current `external_disclosure` policy check before registered handler execution;
- mapped-action current policy check;
- explicit file path allow-list for `filesystem.read_text`;
- payload-free append-only invocation metadata audit.

Gate 022 state:
`IMPLEMENTED_VALIDATED_PENDING_HUMAN_APPROVAL`.

ADR-0021 remains:
`PROPOSED_GATE_022`
until explicit exact-SHA human approval and squash merge.

Next:
run one final generic + strict exact-head CI on the final documentation-only
head, mark PR #44 ready for review if green, then stop at human approval.


---

## 2026-09-20 — Gate 022 accepted and merged

Final approved PR head:
`e3d3d6e67dbd782fc7df1e420424ec1fedf32c02`.

Final validation:
- deterministic regression: `268/268 PASS`;
- generic workflow run `35526813486`: `PASS`;
- strict exact-head workflow run `35526813470`: `PASS`;
- exact revision verification: `PASS`;
- primary-workstation fake-transport smoke: `PASS_CONTROLLED_MCP_TOOL_EXPOSURE`;
- final runtime scope review: `PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`3111a1d793c05ead0292839500e698a9c5fe2c56`.

PR #44:
`MERGED`.

Issue #43:
`CLOSED / COMPLETED`.

ADR-0021 state:
`ACCEPTED_GATE_022`.

Gate 022 state:
`ACCEPTED_MERGED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-20 — Gate 023 provenance-preserving Vision worker opened

Issue:
`#45 — Gate 023 — Provenance-preserving Vision worker`.

Branch:
`gate-023-provenance-preserving-vision-worker`.

Base:
Gate 022 squash merge
`3111a1d793c05ead0292839500e698a9c5fe2c56`.

Declared scope:
- explicit bounded image inputs with project/source provenance and SHA-256;
- transient image payload transport only;
- loopback-only Ollama multimodal request support;
- deterministic Vision routing/capability requirement;
- structured model observations tied to supplied source refs;
- ADVISORY-only result semantics with `evidence_eligible=false`;
- fail-closed media/hash/size/source/provider/schema handling;
- no automatic Blackboard evidence promotion.

Explicitly out of scope:
- deterministic-evidence OCR promotion;
- unmeasured production qualification of a new Vision model;
- live camera/video ingestion;
- external/cloud vision APIs;
- arbitrary filesystem/URL loading;
- CAD manipulation;
- image generation;
- architecture/physics/fabrication/release authority expansion.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

Next:
implement the bounded Vision input/worker boundary and deterministic regression,
then run generic + strict exact-head CI.


---

## 2026-09-20 — Gate 023 Vision worker implementation checkpoint

Initial implementation head:
`bb48c4ff1af907e324455e0979208192ac972a6c`.

Implemented:
- explicit transient image attachments with source refs and SHA-256 identity;
- PNG/JPEG/WebP media allow-list and bounded payloads;
- inline-only loopback Ollama image transport;
- distinct `VISION_ANALYSIS` deterministic routing class;
- Vision routing requires explicit measured `supports_vision_inputs`;
- accepted registry intentionally contains no unmeasured production Vision route;
- bounded Vision worker request/result contract;
- exact source-ref constrained structured observations;
- provider tool calls rejected on Vision path;
- result fixed to `ADVISORY`, `evidence_eligible=false`;
- no automatic Blackboard/evidence/knowledge promotion.

Validation:
- deterministic regression: `278/278 PASS`;
- generic workflow run `35527536750`: `PASS`;
- strict exact-head workflow run `35527536771`: `PASS`.

Input hardening then added basic declared-media signature validation. Intermediate
head `f33f2ba785e37d43d96a4e5293a013af4047c222` correctly failed CI because
the pre-existing synthetic image fixtures did not yet carry valid signatures.

Corrected hardening/smoke head:
`539d8dfb328aefa496b957110f1e903036844357`.

Validation:
- signature-valid fixtures: `PASS`;
- Gate 023 smoke harness included in deterministic regression;
- deterministic regression: `279/279 PASS`;
- generic workflow run `35527660162`: `PASS`;
- strict exact-head workflow run `35527660202`: `PASS`;
- smoke: `PASS_PROVENANCE_PRESERVING_VISION_BOUNDARY`;
- default accepted Vision route: `NO_ROUTE`;
- provider calls before qualified synthetic route: `0`;
- production Vision model qualified: `false`;
- result authority: `ADVISORY`;
- evidence eligible: `false`;
- external network: `false`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

Runtime scope review:
`PASS`.

Confirmed absent:
- arbitrary filesystem/URL image acquisition;
- camera/live-video capture;
- shell/process/Git authority;
- generic tool execution from Vision provider;
- automatic approval;
- automatic evidence promotion;
- external/cloud Vision provider;
- CAD manipulation;
- image generation;
- architecture/physics/fabrication/release authority expansion.

ADR-0022 state:
`PROPOSED_GATE_023`.

Next:
run final documentation/evidence exact-head validation, update PR #46 to ready
for review when green, then stop at explicit exact-SHA human squash-merge
approval.


---

## 2026-09-20 — Gate 023 final hardening checkpoint passed

Validated hardening head:
`82ca772902738de0670fab84bbd28914d0684e44`.

Additional hardening:
- raw Vision input bytes hidden from normal object representation;
- provider response identity must match the deterministic routed provider;
- explicit negative regression for provider mismatch.

Validation:
- deterministic regression: `280/280 PASS`;
- generic workflow run `35527817840`: `PASS`;
- strict exact-head workflow run `35527817828`: `PASS`;
- smoke: `PASS_PROVENANCE_PRESERVING_VISION_BOUNDARY`;
- production Vision model qualification: `NOT_RUN / NOT_QUALIFIED`;
- default accepted Vision route: `NO_ROUTE`;
- model result authority: `ADVISORY`;
- evidence eligible: `false`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

Final runtime scope review:
`PASS`.

Gate 023 state:
`IMPLEMENTED_VALIDATED_PENDING_HUMAN_APPROVAL`.

ADR-0022 remains:
`PROPOSED_GATE_023`
until explicit exact-SHA human approval and squash merge.

Next:
run final generic + strict exact-head CI on the final documentation head, mark
PR #46 ready for review if green, freeze the branch, and stop at explicit human
exact-SHA squash-merge approval.


---

## 2026-09-20 — Gate 023 ready-for-review consistency checkpoint

PR #46 was marked ready for review after the previous final-head validation
passed without changing branch content.

A subsequent source-of-truth consistency review found two stale status entries:
- PR #46 was still labelled DRAFT in STATUS.md;
- Next admissible action still referred to completed Gate 022 / PR #44.

Those documentation-only inconsistencies were corrected before final branch
freeze.

Runtime implementation remains unchanged from validated hardening head:
`82ca772902738de0670fab84bbd28914d0684e44`.

Gate 023 remains:
`IMPLEMENTED_VALIDATED_PENDING_HUMAN_APPROVAL`.

ADR-0022 remains:
`PROPOSED_GATE_023`.

Physical validation remains:
`PHYSICAL_NOT_EXECUTED`.

Next:
the exact PR head after this documentation-only consistency checkpoint must pass
both generic and strict exact-head CI. If green, freeze the branch and stop at
explicit human exact-SHA squash-merge approval.


---

## 2026-09-20 — Gate 023 accepted and merged

Final approved PR head:
`880a8d4fce352e5c614254119192d7bf7d283e27`.

Final validation:
- deterministic regression: `280/280 PASS`;
- generic workflow run `35529619290`: `PASS`;
- strict exact-head workflow run `35529619244`: `PASS`;
- deterministic smoke: `PASS_PROVENANCE_PRESERVING_VISION_BOUNDARY`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`f3c826a434eca8e5d7163f5cf4166560717bdbc2`.

PR #46:
`MERGED`.

Issue #45:
`CLOSED / COMPLETED`.

ADR-0022 state:
`ACCEPTED_GATE_023`.

Production Vision model:
`NOT_QUALIFIED`; default accepted Vision route remains `NO_ROUTE`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-20 — Gate 024 controlled parametric CAD worker opened

Issue:
`#47 — Gate 024 — Controlled parametric CAD worker`.

Branch:
`gate-024-controlled-parametric-cad-worker`.

Base:
Gate 023 squash merge
`f3c826a434eca8e5d7163f5cf4166560717bdbc2`.

Declared scope:
- immutable bounded parametric CAD specification;
- axis-aligned box/cylinder baseline with explicit millimetre parameters;
- deterministic per-entity and assembly geometry checks;
- canonical design SHA-256;
- trusted data-only FreeCAD bridge with fixed repository-owned helper;
- root-bounded proposal artifact publication;
- existing Supervisor `propose_patch` policy authority only;
- zero backend calls on policy denial;
- deterministic post-runtime geometry/report verification;
- CI-capable fake-backend smoke without requiring FreeCAD installation.

Explicitly out of scope:
- new autonomous CAD/write authority;
- model-supplied Python/CAD scripts;
- shell/eval/exec/dynamic command execution;
- arbitrary filesystem writes;
- boolean/CSG/sketch/assembly/FEM expansion;
- production CAD-specialist model qualification;
- fabrication/release authorization;
- Gate 025 image generation.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

Next:
publish the synchronization checkpoint, open one draft PR for Issue #47, then
implement and validate the bounded Gate 024 runtime.


---

## 2026-09-20 — Gate 024 controlled parametric CAD worker implementation checkpoint

Implemented:
- immutable bounded millimetre CAD specification;
- axis-aligned box/cylinder primitives with translation-only placement;
- canonical design SHA-256;
- analytical primitive volume and per-entity/assembly AABB calculation;
- existing Supervisor `propose_patch` authority as the only CAD publication gate;
- zero CAD backend calls when current policy denies the proposal;
- fixed repository-owned FreeCADCmd helper with data-only JSON and `shell=False`;
- no model-supplied Python/macros/shell/eval/exec/dynamic command surface;
- root-bounded FCStd candidate publication;
- temporary candidate/report staging;
- deterministic runtime geometry comparison before target publication;
- artifact/design/geometry SHA-256 preservation;
- result authority `PROPOSED_PATCH_ONLY`;
- geometry consistency evidence separated from engineering-design correctness;
- physical state fixed to `PHYSICAL_NOT_EXECUTED`.

Deterministic smoke:
`PASS_CONTROLLED_PARAMETRIC_CAD_BOUNDARY`.

Corrected full-suite checkpoint:
`bd9ebd15206be83f012e4ddd5625257247d37653`.

Validation:
- deterministic regression: `289/289 PASS`;
- generic workflow `35530909113`: `PASS`;
- strict exact-head workflow `35530909124`: `PASS`.

Earlier test-fixture-only failures were caused by an invalid synthetic Git SHA
that violated the pre-existing project-state schema. The fixture was corrected
without weakening any schema, validator, policy or CAD check.

Hardened runtime head:
`a02822fdecb8573fb20b33fb70b94e6ca5ac16cc`.

Additional hardening:
- primitive kind cannot be caller-overridden;
- placement and entity objects are explicitly typed;
- temporary artifact/report symlinks are rejected;
- artifact publication failures fail closed;
- trusted FreeCAD helper requires positive dimensions.

Validation:
- generic workflow `35530942168`: `PASS`;
- strict exact-head workflow `35530942160`: `PASS`.

Architecture:
- section 4.22 records the proposal-only CAD authority/evidence boundary;
- ADR-0023 added as `PROPOSED_GATE_024`.

Real FreeCAD workstation runtime:
`NOT_RUN`.

Fabrication authorization:
`NOT_GRANTED`.

Release authorization:
`NOT_GRANTED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

Next:
run final exact-head CI on the documentation/evidence head, mark PR #48 ready
for review if green, synchronize any ready-state documentation, freeze the
branch, and stop at explicit human exact-SHA squash-merge approval.


---

## 2026-09-20 — Gate 024 ready-for-review checkpoint

Final documentation/evidence head before ready transition:
`a3f979ce4035a64981af911807b7f6fdfcd1c7f3`.

Validation:
- generic workflow `35531115705`: `PASS`;
- strict exact-head workflow `35531115699`: `PASS`;
- deterministic regression remains `289/289 PASS`;
- smoke remains `PASS_CONTROLLED_PARAMETRIC_CAD_BOUNDARY`.

PR #48 was marked:
`READY FOR REVIEW`.

No runtime, CAD authority, geometry semantics, fabrication/release state or
physical-validation state changed by the ready transition.

A final documentation-only source-of-truth consistency commit now requires one
last generic + strict exact-head CI before branch freeze and explicit human
exact-SHA squash-merge approval.

ADR-0023 remains:
`PROPOSED_GATE_024`.

Physical validation remains:
`PHYSICAL_NOT_EXECUTED`.


---

## 2026-09-20 — Gate 024 accepted and merged

Final approved PR head:
`8330aa62964ec2f9b38873b69a7591a44e1fa5a4`.

Final validation:
- deterministic regression: `289/289 PASS`;
- generic workflow `35531166350`: `PASS`;
- strict exact-head workflow `35531166349`: `PASS`;
- smoke: `PASS_CONTROLLED_PARAMETRIC_CAD_BOUNDARY`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`99a8e216dc2c8ec7b98c445f0e1909479bff6b52`.

PR #48:
`MERGED`.

Issue #47:
`CLOSED / COMPLETED`.

ADR-0023 state:
`ACCEPTED_GATE_024`.

Real FreeCAD workstation smoke:
`NOT_RUN`.

Fabrication authorization:
`NOT_GRANTED`.

Release authorization:
`NOT_GRANTED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-20 — Gate 025 non-authoritative image-generation worker opened

Issue:
`#49 — Gate 025 — Non-authoritative image-generation worker`.

Branch:
`gate-025-non-authoritative-image-generation-worker`.

Base:
Gate 024 squash merge
`99a8e216dc2c8ec7b98c445f0e1909479bff6b52`.

Declared scope:
- provider-neutral typed text-to-image request/response;
- explicit evidence-qualified IMAGE_GENERATION routing;
- no unmeasured production route in accepted registry;
- bounded PNG output only;
- deterministic PNG signature/IHDR/CRC/dimension validation;
- existing Supervisor `propose_patch` authority before provider call/publication;
- root-bounded PNG publication with SHA-256 identity;
- result fixed to `ADVISORY_CONCEPT_ONLY`, `evidence_eligible=false`,
  `engineering_drawing=false`;
- synthetic-provider CI smoke without requiring a real image model.

Explicitly out of scope:
- image editing/reference-image transformation;
- arbitrary filesystem/URL acquisition;
- external/cloud generation API;
- automatic production model qualification;
- generated imagery as drawing/CAD/schematic/measurement/evidence;
- shell/Git/tool authority;
- fabrication/release/physical-validation authority expansion.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

Next:
publish the synchronization checkpoint, open one draft PR for Issue #49, then
implement and validate the bounded Gate 025 runtime.


---

## 2026-09-20 — Gate 025 non-authoritative image-generation implementation checkpoint

Implemented:
- explicit `IMAGE_GENERATION` deterministic task class;
- evidence-qualified image-generation capability flag;
- no unmeasured production route in accepted registry;
- provider-neutral local-only text-to-image protocol;
- bounded prompt, dimensions, seed and provider/model identity;
- existing Supervisor `propose_patch` as the sole publication authority;
- zero provider calls when accepted route is absent;
- zero provider calls when current policy denies `propose_patch`;
- deterministic PNG signature/chunk/CRC/IHDR/IDAT/IEND validation;
- zlib raster decoding and scanline filter validation;
- exact requested dimension enforcement;
- root-bounded forward-slash PNG target paths;
- symlink/traversal rejection;
- atomic publication only after deterministic PNG PASS;
- SHA-256 identity for prompt and generated PNG;
- fixed result authority `ADVISORY_CONCEPT_ONLY`;
- `evidence_eligible=false`;
- `engineering_drawing=false`;
- `PHYSICAL_NOT_EXECUTED`.

Full smoke checkpoint:
`a5bb614a430a0d5b00d3adab57c4a62fd1b41e7f`.

Validation:
- deterministic regression: `301/301 PASS`;
- generic workflow `35531846754`: `PASS`;
- strict exact-head workflow `35531846777`: `PASS`;
- smoke: `PASS_NON_AUTHORITATIVE_IMAGE_GENERATION_BOUNDARY`.

PNG hardening head:
`93991af1b5b7505ce0546dd58297daf810d6409e`.

Additional hardening:
- provider PNG must be 8-bit RGB/RGBA;
- interlaced output rejected;
- IDAT zlib stream must decode;
- decompressed raster length must match exact dimensions/channels;
- each scanline filter byte must be valid;
- ambiguous backslash target paths rejected.

Hardening validation:
- generic workflow `35531878630`: `PASS`;
- strict exact-head workflow `35531878735`: `PASS`.

Architecture:
- section 4.23 records the non-authoritative image-generation boundary;
- ADR-0024 added as `PROPOSED_GATE_025`.

Production image-generation model/provider:
`NOT_QUALIFIED`.

Default accepted route:
`NO_ROUTE`.

Real local image-generation provider call:
`NOT_RUN`.

External/cloud generation:
`NOT_RUN / OUT_OF_SCOPE`.

Fabrication authorization:
`NOT_GRANTED`.

Release authorization:
`NOT_GRANTED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

Next:
run final exact-head CI on the documentation/evidence head, mark PR #50 ready
for review if green, synchronize any ready-state documentation, freeze the
branch, and stop at explicit human exact-SHA squash-merge approval.


---

## 2026-09-20 — Gate 025 ready-for-review checkpoint

Final documentation/evidence head before ready transition:
`81fc9256b737a9110037f5f9695e76d40634ff0c`.

Validation:
- deterministic regression remains `301/301 PASS`;
- generic workflow `35531984785`: `PASS`;
- strict exact-head workflow `35531984758`: `PASS`;
- smoke remains `PASS_NON_AUTHORITATIVE_IMAGE_GENERATION_BOUNDARY`.

PR #50 was marked:
`READY FOR REVIEW`.

No runtime, routing, provider, PNG validation, artifact authority,
fabrication/release state or physical-validation state changed by the ready
transition.

A final documentation-only source-of-truth consistency commit now requires one
last generic + strict exact-head CI before branch freeze and explicit human
exact-SHA squash-merge approval.

ADR-0024 remains:
`PROPOSED_GATE_025`.

Production image-generation model/provider remains:
`NOT_QUALIFIED`.

Default accepted image-generation route remains:
`NO_ROUTE`.

Physical validation remains:
`PHYSICAL_NOT_EXECUTED`.


---

## 2026-09-20 — Gate 025 accepted and merged

Final approved PR head:
`eca63b5c28ea908c6cb43900aa97909d0fb289bc`.

Final validation:
- deterministic regression: `301/301 PASS`;
- generic workflow `35532035872`: `PASS`;
- strict exact-head workflow `35532035537`: `PASS`;
- smoke: `PASS_NON_AUTHORITATIVE_IMAGE_GENERATION_BOUNDARY`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`171ff20125389d2d953576a0d3340c13dc1dc53f`.

PR #50:
`MERGED`.

Issue #49:
`CLOSED / COMPLETED`.

ADR-0024 state:
`ACCEPTED_GATE_025`.

Production image-generation model/provider:
`NOT_QUALIFIED`.

Default accepted image-generation route:
`NO_ROUTE`.

Real image-generation provider call:
`NOT_RUN`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-20 — Gate 026 reproducible local installation opened

Issue:
`#51 — Gate 026 — Reproducible local installation`.

Branch:
`gate-026-reproducible-local-installation`.

Base:
Gate 025 squash merge
`171ff20125389d2d953576a0d3340c13dc1dc53f`.

Objective:
close the first Phase 8 / v1.0 criterion, reproducible local installation,
without changing Engineering AI runtime authority or feature architecture.

Measured runtime dependency closure from accepted Gate 025 CI
`35532035872`:
- `jsonschema==4.26.0`;
- `attrs==26.1.0`;
- `jsonschema-specifications==2025.9.1`;
- `referencing==0.37.0`;
- `rpds-py==2026.6.3`;
- `typing-extensions==4.16.0`.

Build/install tool versions remain to be measured before freezing.

Explicitly out of scope:
- offline wheelhouse/dependency packaging;
- model/routing changes;
- new tool/permission authority;
- connected-project behavioral changes;
- containerization requirement;
- package publication;
- fabrication/release;
- validator weakening.

Next:
publish the Gate 026 synchronization checkpoint, open one draft PR for Issue
#51, then add and validate the clean-install contract.


---

## 2026-09-20 — Gate 026 cross-platform installation implementation validated

Validated implementation head:
`6c7bfbd9f8d07b96adeb3014b2071a4bc8a0793e`.

Implemented:
- Python 3.12.x canonical install contract;
- exact install-tool lock:
  `packaging==26.3`, `pip==26.2.1`, `setuptools==84.0.0`,
  `wheel==0.48.0`;
- exact runtime dependency closure;
- clean fresh-venv bootstrap;
- double wheel build with repeated SHA-256 equality requirement;
- non-editable wheel installation;
- installed package/version verification;
- 14 installed JSON Schema documents verified independently of source checkout;
- `pip check`;
- full deterministic regression from the installed package;
- Ubuntu + Windows Gate 026 acceptance workflow.

The stricter install path exposed and corrected:
- missing schema data in built wheels;
- SQLite handle retention after failed memory initialization;
- Windows CRLF assumptions in exact-byte controlled-worktree tests;
- incomplete Windows timeout-process cleanup.

Production exact-byte stale-patch protection, Supervisor authority and existing
validator semantics were not weakened.

Validation:
- generic workflow `35535616430`: `PASS`;
- strict exact-head workflow `35535616425`: `PASS`;
- Gate 026 install workflow `35535616417`: `PASS`;
- Ubuntu installed-package regression: `306/306 PASS`;
- Windows installed-package regression: `306/306 PASS`;
- Ubuntu repeated wheel SHA-256 match: `PASS`;
- Windows repeated wheel SHA-256 match: `PASS`.

Ubuntu and Windows wheel hashes are distinct from each other. Gate 026 claims
repeated deterministic wheel identity within each validated platform, not
byte-identical cross-platform wheel artifacts.

Offline dependency acquisition:
`NOT_CLAIMED_GATE_026`.

Offline continuation of connected projects:
`NOT_CLAIMED_GATE_026`.

Package publication:
`NOT_RUN / OUT_OF_SCOPE`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

Next:
run the documentation/evidence exact-head validation checkpoint. If green, mark
PR #52 ready for review, synchronize ready-state documentation, freeze the
branch, run final exact-head validation, and stop for explicit human exact-SHA
squash-merge approval.


---

## 2026-09-20 — Gate 026 ready-for-review checkpoint

Documentation/evidence checkpoint head before ready transition:
`a04337bbfbc0d9306b4f9a8a2f4d93dbc62bfb5b`.

Validation:
- generic workflow `35535865183`: `PASS`;
- strict exact-head workflow `35535865222`: `PASS`;
- Gate 026 install workflow `35535865187`: `PASS`;
- Ubuntu clean non-editable install: `PASS`;
- Windows clean non-editable install: `PASS`.

PR #52 was marked:
`READY FOR REVIEW`.

No architecture, model-routing, Supervisor authority, offline-continuation,
publication, release, fabrication or physical-validation state changed by the
ready transition.

A final source-of-truth consistency head now requires one last generic + strict
exact-head + Gate 026 cross-platform install validation before branch freeze and
explicit human exact-SHA squash-merge approval.

Offline continuation remains:
`NOT_CLAIMED_GATE_026`.

Physical validation remains:
`PHYSICAL_NOT_EXECUTED`.


---

## 2026-09-20 — Gate 026 accepted and merged

Final approved PR head:
`8e27641c250a0b3f0061c9de41e9ecdd13d17f20`.

Final exact-head validation:
- generic workflow `35536044039`: `PASS`;
- strict exact-head workflow `35536043981`: `PASS`;
- Gate 026 install workflow `35536044021`: `PASS`;
- Ubuntu installed-package regression: `306/306 PASS`;
- Windows installed-package regression: `306/306 PASS`.

Squash merge on `main`:
`d1d93c7a3c17ffbd1c4bd7d7820ca75d8f9bcc4d`.

PR #52:
`MERGED`.

Issue #51:
`CLOSED / COMPLETED`.

Phase 8 reproducible-local-installation criterion:
`CLOSED_BY_GATE_026`.

Offline continuation:
`NOT_CLAIMED_GATE_026`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-20 — Gate 027 offline continuation boundary opened

Issue:
`#53 — Gate 027 — Offline continuation boundary for connected projects`.

Branch:
`gate-027-offline-continuation-boundary`.

Base:
Gate 026 squash merge
`d1d93c7a3c17ffbd1c4bd7d7820ca75d8f9bcc4d`.

Objective:
close the next Phase 8 criterion by making process-step network requirements
explicit and proving connected-project local continuation in a fail-closed
offline mode.

The Gate will not emulate an OS firewall or claim that arbitrary project-owned
scripts are network-free. Commands classified as network-capable must be
rejected before subprocess execution when offline mode is active.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.


---

## 2026-09-20 — Gate 027 offline continuation implementation validated

Validated implementation/architecture checkpoint:
`323b2db90c1470634ea816a4a96eb1f9dcc47ed9`.

Implemented:
- mandatory explicit `NetworkRequirement` for every `CommandSpec`;
- `LOCAL_ONLY` and `NETWORK_CAPABLE` process classifications;
- offline process mode that blocks `NETWORK_CAPABLE` before executable
  resolution/subprocess creation;
- PlataVM read-only and controlled offline propagation;
- BuoyCalc restore classification as network-capable;
- structured BuoyCalc
  `BLOCKED_RUNTIME_PREREQUISITE / OFFLINE_NETWORK_REQUIRED` evidence;
- local-only classification for static scans and no-restore/no-build steps;
- cross-platform synthetic connected-project offline smoke.

Validation:
- deterministic regression: `312/312 PASS`;
- generic workflow `35537733809`: `PASS`;
- strict exact-head workflow `35537733812`: `PASS`;
- Gate 027 offline workflow `35537733811`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 026 install workflow `35537733819`:
  Ubuntu `PASS`, Windows `PASS`;
- installed-package regression: `312/312 PASS` on Ubuntu and Windows.

Gate 027 smoke:
- state: `PASS_OFFLINE_CONTINUATION_BOUNDARY`;
- external network intentionally exercised: false;
- PlataVM controlled offline state: `READY_FOR_HUMAN_APPROVAL`;
- BuoyCalc network block state: `BLOCKED_RUNTIME_PREREQUISITE`;
- blocked reason: `OFFLINE_NETWORK_REQUIRED`;
- primary synthetic repositories unchanged.

Evidence limitation:
this proves the Engineering AI control-plane network boundary and local-resource
smoke path. It does not claim OS-level packet filtering or formal proof that
arbitrary project-owned script internals can never open a socket.

Release authorization:
`NOT_GRANTED`.

Fabrication authorization:
`NOT_GRANTED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

Next:
run documentation/evidence exact-head validation. If green, mark PR #54 ready
for review, synchronize ready-state source-of-truth, freeze the branch and stop
at explicit human exact-SHA squash-merge approval after final validation.


---

## 2026-09-21 — Gate 027 ready-for-review checkpoint

Implementation/evidence head before ready transition:
`25401cdd3b15b5979d22ca44603e56425876b5e6`.

Validation:
- deterministic regression: `312/312 PASS`;
- generic workflow `35537939691`: `PASS`;
- strict exact-head workflow `35537939692`: `PASS`;
- Gate 027 offline workflow `35537939698`: `PASS`;
- inherited Gate 026 install workflow `35537939708`: `PASS`.

PR #54 was marked:
`READY FOR REVIEW`.

No architecture/physics, remote Git mutation, package-download, external-model,
release, fabrication or physical-validation authority changed by the ready
transition.

A final source-of-truth consistency head now requires one last exact-head
validation set before branch freeze and explicit human squash-merge approval.

Physical validation remains:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-21 — Gate 027 accepted and merged

Final approved PR head:
`dbb6c19a6ead1525cfdb922dda5ed91d8d59b035`.

Final exact-head validation:
- generic workflow `35538670272`: `PASS`;
- strict exact-head workflow `35538670265`: `PASS`;
- Gate 027 offline continuation workflow `35538670312`: `PASS`;
- inherited Gate 026 install workflow `35538670420`: `PASS`;
- Ubuntu reproducible install: `PASS`;
- Windows reproducible install: `PASS`.

Explicit human exact-SHA squash-merge approval:
`PASS`.

Squash merge on `main`:
`39ab8ee30364cafaebe87d6d9b5ab17430f5031e`.

PR #54:
`MERGED`.

Issue #53:
`CLOSED / COMPLETED`.

Phase 8 offline-continuation criterion:
`CLOSED_BY_GATE_027`.

Release authorization:
`NOT_GRANTED`.

Fabrication authorization:
`NOT_GRANTED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-21 — Gate 028 policy/approval enforcement acceptance opened

Issue:
`#55 — Gate 028 — v1.0 policy and approval enforcement acceptance`.

Branch:
`gate-028-policy-approval-enforcement`.

Base:
accepted Gate 027 squash merge
`39ab8ee30364cafaebe87d6d9b5ab17430f5031e`.

Objective:
close the next Phase 8 / v1.0 criterion by revalidating already-accepted
policy and explicit-human-approval boundaries as a single deterministic
cross-platform acceptance package.

Initial implementation:
- Gate-specific acceptance smoke over Supervisor policy, controlled BuoyCalc
  mutation, external review and controlled tool exposure modules;
- reuse of Gate 019 persisted approval-wait smoke;
- reuse of Gate 021 external-disclosure approval smoke;
- reuse of Gate 022 controlled-tool approval smoke;
- exact-head Ubuntu/Windows Gate 028 workflow;
- no policy-semantic or architecture change.

Stop boundaries remain unchanged:
- no validator weakening;
- no remote Git mutation authority granted to Engineering AI;
- no release/fabrication authority;
- no project-physics expansion;
- no physical-validation claim.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-21 — Gate 028 ready-for-review checkpoint

Validated implementation head:
`5458c1bdd930d0d80671f42bc665807f12c8d215`.

Validation:
- deterministic regression: `313/313 PASS`;
- generic workflow `35625528735`: `PASS`;
- strict exact-head workflow `35625528753`: `PASS`;
- Gate 028 policy/approval workflow `35625528680`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 027 offline workflow `35625528713`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 026 install workflow `35625528728`:
  Ubuntu `PASS`, Windows `PASS`.

Gate 028 acceptance state:
`PASS_V1_0_POLICY_APPROVAL_ENFORCEMENT`.

PR #56 was marked:
`READY FOR REVIEW`.

No policy-semantic or architecture expansion occurred. Remote Git mutation,
release, fabrication and physical-validation authority remain ungranted.

A final source-of-truth synchronization head now requires one last exact-head
validation set before explicit human squash-merge approval.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-21 — Gate 028 accepted and merged

Final approved PR head:
`fe120ee8d1e95d06600a4b3c43b769a4f4c63772`.

Final validation:
- deterministic regression: `313/313 PASS`;
- generic workflow `35626063568`: `PASS`;
- strict exact-head workflow `35626063362`: `PASS`;
- Gate 028 policy/approval workflow `35626063495`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 027 workflow `35626063616`: `PASS`;
- inherited Gate 026 install workflow `35626063014`:
  Ubuntu `PASS`, Windows `PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`e6e6dcf2dff3d081f2fb3c394b919f60b43e2c78`.

PR #56:
`MERGED`.

Issue #55:
`CLOSED / COMPLETED`.

Phase 8 tested policy/approval enforcement criterion:
`CLOSED_BY_GATE_028`.

Release authorization:
`NOT_GRANTED`.

Fabrication authorization:
`NOT_GRANTED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-21 — Gate 029 deterministic tool/validator integration acceptance opened

Issue:
`#57 — Gate 029 — v1.0 deterministic tool and validator integration acceptance`.

Branch:
`gate-029-deterministic-tool-validator-integration`.

Base:
accepted Gate 028 squash merge
`e6e6dcf2dff3d081f2fb3c394b919f60b43e2c78`.

Objective:
close the next Phase 8 / v1.0 criterion by revalidating existing root-bounded
tool adapters and PlataVM/BuoyCalc validator integration as one deterministic
cross-platform acceptance package.

Initial implementation:
- Gate-specific acceptance smoke over tools, PlataVM read-only/controlled and
  BuoyCalc read-only/controlled test modules;
- inherited Gate 027 structured offline-continuation smoke;
- exact-head Ubuntu/Windows Gate 029 workflow;
- no tool-authority, project-physics, architecture or validator-semantic change.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-21 — Gate 029 ready-for-review checkpoint

Validated implementation head:
`028ad1aad83a51657e7256de4b3f1841ffc0d1b5`.

Validation:
- deterministic regression: `314/314 PASS`;
- generic workflow `35627468692`: `PASS`;
- strict exact-head workflow `35627468743`: `PASS`;
- Gate 029 tool/validator workflow `35627468703`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 028 policy/approval workflow `35627468809`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 027 offline workflow `35627468716`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 026 install workflow `35627468832`:
  Ubuntu `PASS`, Windows `PASS`.

Gate 029 acceptance state:
`PASS_V1_0_DETERMINISTIC_TOOL_VALIDATOR_INTEGRATION`.

PR #58 was marked:
`READY FOR REVIEW`.

No tool-authority, project-physics, architecture or validator-semantic expansion
occurred. Remote Git mutation, generic filesystem write, release, fabrication
and physical-validation authority remain ungranted.

A final source-of-truth synchronization head now requires one last exact-head
validation set before explicit human squash-merge approval.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-21 — Gate 029 accepted and merged

Final approved PR head:
`e768210216cabd21fd977179b3397f42ea09a1a5`.

Final validation:
- deterministic regression: `314/314 PASS`;
- generic workflow `35628058655`: `PASS`;
- strict exact-head workflow `35628058907`: `PASS`;
- Gate 029 tool/validator workflow `35628058641`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 028 policy/approval workflow `35628058617`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 027 offline workflow `35628058634`: `PASS`;
- inherited Gate 026 install workflow `35628058638`:
  Ubuntu `PASS`, Windows `PASS`;
- explicit exact-SHA human squash-merge approval: `PASS`.

Squash merge on `main`:
`f76cc2a2db329a43bff2ff47f9dcd2039e37e05d`.

PR #58:
`MERGED`.

Issue #57:
`CLOSED / COMPLETED`.

Phase 8 deterministic tool/validator integration criterion:
`CLOSED_BY_GATE_029`.

Release authorization:
`NOT_GRANTED`.

Fabrication authorization:
`NOT_GRANTED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-21 — Gate 030 auditable state transitions acceptance opened

Issue:
`#59 — Gate 030 — v1.0 auditable state transitions acceptance`.

Branch:
`gate-030-auditable-state-transitions`.

Base:
accepted Gate 029 squash merge
`f76cc2a2db329a43bff2ff47f9dcd2039e37e05d`.

Objective:
close the next Phase 8 / v1.0 criterion by revalidating existing Supervisor
state/audit transitions, append-only memory/lifecycle, persisted job/schedule
state and controlled external/tool ledgers as one deterministic cross-platform
acceptance package.

Initial implementation:
- Gate-specific acceptance smoke over Supervisor, memory, lifecycle, job queue,
  scheduled runs, external review and tool bridge deterministic modules;
- reuse of Gate 018/019/020/021/022 structured smoke evidence;
- exact-head Ubuntu/Windows Gate 030 workflow;
- no state-machine, history-mutability, integrity or authority expansion.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-21 — Gate 030 ready-for-review checkpoint

Validated implementation head:
`bbb5067c9da5f235d191077e6591f8c3bc8bb78b`.

Validation:
- deterministic regression: `315/315 PASS`;
- generic workflow `35628992570`: `PASS`;
- strict exact-head workflow `35628992420`: `PASS`;
- Gate 030 auditable-state workflow `35628992522`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 029 tool/validator workflow `35628992451`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 028 policy/approval workflow `35628992587`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 027 offline workflow `35628992616`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 026 install workflow `35628992397`:
  Ubuntu `PASS`, Windows `PASS`.

Gate 030 acceptance state:
`PASS_V1_0_AUDITABLE_STATE_TRANSITIONS`.

PR #60 was marked:
`READY FOR REVIEW`.

No state-machine semantic, history-mutability, integrity-check or authority
expansion occurred. Automatic approval remains prohibited. Release/fabrication
and physical-validation authority remain ungranted.

A final source-of-truth synchronization head now requires one last exact-head
validation set before explicit human squash-merge approval.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.


---

## 2026-09-22 — Gate 030 accepted and merged

Final approved PR head:
`88b9d74fa0456eb9bea92e89e8b572646ed4723c`.

Final exact-head validation:
- deterministic regression: `315/315 PASS`;
- generic workflow `35629679136`: `PASS`;
- strict exact-head workflow `35629678851`: `PASS`;
- Gate 030 auditable-state workflow `35629679112`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 029 workflow `35629678990`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 028 workflow `35629679002`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 027 workflow `35629679048`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 026 workflow `35629679029`:
  Ubuntu `PASS`, Windows `PASS`.

Explicit human exact-SHA squash-merge approval:
`PASS`.

Squash merge on `main`:
`82ec76013e28c2d7db5644c1b99565170418f9a9`.

PR #60:
`MERGED`.

Issue #59:
`CLOSED / COMPLETED`.

Phase 8 auditable-state-transitions criterion:
`CLOSED_BY_GATE_030`.

Release authorization:
`NOT_GRANTED`.

Fabrication authorization:
`NOT_GRANTED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-22 — Gate 031 measured and replaceable multi-model routing acceptance opened

Issue:
`#62 — Gate 031 — v1.0 measured and replaceable multi-model routing acceptance`.

Branch:
`gate-031-measured-replaceable-routing`.

Base:
accepted Gate 030 squash merge
`82ec76013e28c2d7db5644c1b99565170418f9a9`.

Repository audit before implementation confirmed:
- Gate 005 contains measured baseline evidence for `gpt-oss:20b / medium`;
- Gate 008 contains measured qualification evidence for `qwen3.5:9b` and
  `qwen2.5-coder:7b-instruct`;
- Gate 009 implements the immutable evidence-backed
  `ModelCapabilityRegistry` and pure deterministic
  `DeterministicModelRouter`;
- accepted route decisions preserve provider/model identity and evidence refs;
- over-envelope or unqualified requirements fail closed as `NO_ROUTE`;
- Router has no provider/tool execution dependency.

Gate 031 acceptance implementation adds:
- a deterministic acceptance harness over the accepted Gate 005/008/009
  evidence and current routing runtime;
- a test-only alternate registry entry proving that route selection changes
  through registry data without Supervisor/Router architecture changes;
- explicit checks that this synthetic replacement is not a production
  qualification or practical runtime-replacement claim;
- an exact-head Ubuntu/Windows Gate-specific workflow;
- evidence/status/roadmap synchronization.

Separate Phase 8 criterion
`model/runtime replaceability demonstrated in practice`
remains open and must not be inferred from this Gate.

Release authorization:
`NOT_GRANTED`.

Fabrication authorization:
`NOT_GRANTED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.


---

## 2026-09-22 — Gate 031 implementation checkpoint validated

Validated head:
`84fd6695076951a02e5a3e34186891b629db1eff`.

Validation:
- deterministic regression: `316/316 PASS`;
- generic workflow `35771368101`: `PASS`;
- strict exact-head workflow `35771367774`: `PASS`;
- Gate 031 measured-routing workflow `35771367743`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 030 workflow `35771367958`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 029 workflow `35771367984`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 028 workflow `35771367685`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 027 workflow `35771367656`:
  Ubuntu `PASS`, Windows `PASS`.

Inherited Gate 026 workflow `35771368266`:
- Ubuntu clean install/regression: `PASS`;
- Windows attempt 1: `FAIL` in the pre-existing
  `test_timeout_is_terminal_and_structured` cleanup path after timeout,
  reporting `WinError 32/5` while removing the temporary directory;
- the same test had passed on the prior accepted Gate 030 Windows Gate 026 run;
- a failed-jobs rerun was executed on the identical Gate 031 head;
- no source, test or validator change occurred between attempts;
- Windows rerun: `PASS`.

Interpretation:
the first Windows result is retained as observed failure evidence. The subsequent
same-head PASS supports classification as a transient Windows process-handle
cleanup race, not a Gate 031 routing regression. No validator or test was
weakened to obtain PASS.

Gate 031 criterion state:
`IMPLEMENTED_VALIDATED_PENDING_FINAL_EXACT_HEAD_CHECK`.

The separate Phase 8 practical model/runtime replacement criterion remains open.

Release authorization:
`NOT_GRANTED`.

Fabrication authorization:
`NOT_GRANTED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.


---

## 2026-09-22 — Gate 031 ready-for-review checkpoint

Ready-transition source head before documentation synchronization:
`4aad08ad402cf248796c61a5e05219e26f59eb21`.

Validation on that exact head:
- deterministic regression: `316/316 PASS`;
- generic workflow `35774754266`: `PASS`;
- strict exact-head workflow `35774754209`: `PASS`;
- Gate 031 workflow `35774754510`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 030 workflow `35774754315`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 029 workflow `35774754322`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 028 workflow `35774754475`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 027 workflow `35774754239`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 026 workflow `35774754526`: Ubuntu `PASS`, Windows `PASS`.

PR #63 was marked:
`READY FOR REVIEW`.

No architecture, routing-runtime, qualification, provider, tool-authority,
validator, release, fabrication or physical-validation semantics changed by the
ready transition.

A final documentation-only source-of-truth head now requires one last exact-head
validation set before branch freeze and explicit human exact-SHA squash-merge
approval.

Practical model/runtime replacement remains:
`NOT_CLAIMED_GATE_031`.

Release authorization:
`NOT_GRANTED`.

Fabrication authorization:
`NOT_GRANTED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.


---

## 2026-09-22 — Gate 031 accepted and merged

Final approved PR head:
`0910527c514ea1e13c7bf0f56f7e04a33a9efd72`.

Final exact-head validation:
- deterministic regression: `316/316 PASS`;
- generic workflow `35775473139`: `PASS`;
- strict exact-head workflow `35775472629`: `PASS`;
- Gate 031 measured-routing workflow `35775472868`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 030 workflow `35775472574`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 029 workflow `35775472587`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 028 workflow `35775473357`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 027 workflow `35775472579`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 026 workflow `35775473035`:
  Ubuntu `PASS`, Windows `PASS` on same-head failed-job rerun.

The earlier Windows timeout-cleanup `WinError 32/5` evidence remains retained.
No source, test or validator weakening was used to obtain the subsequent
same-head PASS.

Explicit human exact-SHA squash-merge approval:
`PASS`.

Squash merge on `main`:
`be30ad6de5092220be662b932c21198efcde9db8`.

PR #63:
`MERGED`.

Issue #62:
`CLOSED / COMPLETED`.

Phase 8 measured-and-replaceable multi-model routing criterion:
`CLOSED_BY_GATE_031`.

The separate practical model/runtime replacement criterion remains open.

Release authorization:
`NOT_GRANTED`.

Fabrication authorization:
`NOT_GRANTED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.

---

## 2026-09-22 — Gate 032 opened and remaining Phase 8 route fixed

Issue:
`#64 — Gate 032 — v1.0 controlled model-to-model hand-offs with provenance acceptance`.

PR:
`#65 — DRAFT`.

Branch:
`gate-032-controlled-handoffs-provenance`.

Base:
accepted Gate 031 squash merge
`be30ad6de5092220be662b932c21198efcde9db8`.

Gate 032 objective:
revalidate the accepted Gate 010 Blackboard/handoff runtime together with Gate
011 evidence-first independent review as one Supervisor-controlled,
provenance-preserving acceptance package.

The remaining Phase 8 execution route is now recorded in source of truth:

1. Gate 032 — controlled model-to-model hand-offs with provenance acceptance.
2. Gate 033 — persistent project memory with provenance acceptance.
3. Gate 034 — documented model/tool failure recovery acceptance.
4. PlataVM handoff/readiness audit — read-only preparation before real
   connected-project acceptance.
5. Gate 035 — successful controlled use on PlataVM and BuoyCalc.
6. Gate 036 — model/runtime replaceability demonstrated in practice.
7. Final v1.0 readiness audit — cold-start/source-of-truth continuation without
   hidden chat context.

This route does not grant architecture, model, tool, Git, connected-project
physics, release, fabrication or physical-validation authority.

Release authorization:
`NOT_GRANTED`.

Fabrication authorization:
`NOT_GRANTED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.


---

## 2026-09-23 — Gate 032 reconciliation and implementation checkpoint

Read-only reconciliation before implementation confirmed:
- `main`: `be30ad6de5092220be662b932c21198efcde9db8`;
- Issue #64: `OPEN`;
- PR #65: `DRAFT`;
- Gate 032 branch was based exactly on the accepted Gate 031 squash merge;
- pre-implementation PR head: `88ce9157d938a2965a469d9817b32e073357c423`;
- pre-implementation changed files were only `ROADMAP.md`, `STATUS.md` and
  `CHRONOLOGY.md`;
- inherited CI on that pre-implementation head was green;
- no source-of-truth conflict was found.

Gate 010 and Gate 011 were re-read from source, evidence and deterministic
tests. Existing accepted behavior already provided Supervisor-only handoffs,
read-only worker views, visible-record context, hidden/cross-task exclusion,
fail-closed missing context, coder native-tool rejection, evidence-first review
and same-model self-review rejection.

The objective gap was narrow: HANDOFF records did not explicitly carry all
originating role/model/provider and source/version provenance required by the
Gate 032 acceptance criterion.

Gate 032 therefore added only additive provenance hardening and an acceptance
package. No routing table, model qualification, policy authority, tool
authority, connected-project physics, release/fabrication or physical state was
expanded.

First implementation head:
`e93e6ac1a8de9570a3ef3098073f80b8b4275dcd`.

Gate 032 workflow `35785749569` failed on Ubuntu because the new Gate-specific
smoke fixture used a non-SHA repository-head placeholder rejected by the
existing project-state schema. Generic and strict exact-head regression failed
for the same fixture defect. No validator was changed or weakened.

Correction head:
`acfd937cce15981d72aed902c1705d60171aaf7d`.

Validation on the corrected exact head:
- deterministic regression: `317/317 PASS`;
- generic workflow `35785822365`: `PASS`;
- strict exact-head workflow `35785821993`: `PASS`;
- Gate 032 workflow `35785822002`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 031 workflow `35785821972`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 030 workflow `35785822032`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 029 workflow `35785822009`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 028 workflow `35785822123`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 027 workflow `35785822081`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 026 workflow `35785822177`: Ubuntu `PASS`, Windows `PASS`.

PR #65 remains:
`DRAFT`.

Gate 032 is not yet accepted or merged. A ready-state synchronization and final
exact-head validation remain required before explicit human squash-merge
approval.

Release authorization:
`NOT_GRANTED`.

Fabrication authorization:
`NOT_GRANTED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.


---

## 2026-09-23 — Gate 032 ready-for-review checkpoint

Ready transition source head:
`0e0b571cf6c03033ee0142a5c69dcaeda1ccfbaf`.

Validation on that exact head:
- deterministic regression: `317/317 PASS`;
- generic workflow `35786526609`: `PASS`;
- strict exact-head workflow `35786526597`: `PASS`;
- Gate 032 workflow `35786526598`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 031 workflow `35786526681`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 030 workflow `35786526617`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 029 workflow `35786526856`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 028 workflow `35786526778`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 027 workflow `35786526782`: Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 026 workflow `35786526859`: Ubuntu `PASS`, Windows `PASS`.

PR #65 was marked:
`READY FOR REVIEW`.

No architecture, model qualification, routing decision table, tool/Git/network
authority, connected-project physics, validator semantics, release/fabrication
or physical-validation state changed by the ready transition.

The retained first-implementation fixture failure on
`e93e6ac1a8de9570a3ef3098073f80b8b4275dcd` remains part of Gate 032
evidence and was not hidden.

A final documentation/source-of-truth head now requires one last exact-head
validation set before branch freeze and explicit human exact-SHA squash-merge
approval.

Release authorization:
`NOT_GRANTED`.

Fabrication authorization:
`NOT_GRANTED`.

Physical validation:
`PHYSICAL_NOT_EXECUTED`.


---

## 2026-09-27 — Gate 032 accepted and merged

Issue #64 completed and PR #65 squash-merged.

Final approved PR head:
`a89a2c7fdb2e472dd422121695d8492a31387b80`

Squash merge on `main`:
`79fd557c645f9310c5729400cfe7ba5fcf61ffa0`

Gate 032 state became:
`ACCEPTED_MERGED`

Controlled model-to-model hand-off provenance acceptance closed without granting
direct peer-to-peer authority, new model/tool authority, release/fabrication
authority or physical-validation claims.

---

## 2026-09-27 — Dedicated EngineeringAI-Ubuntu execution node validated

Engineering AI source at exact main revision
`79fd557c645f9310c5729400cfe7ba5fcf61ffa0` was transferred by local Git bundle
to the dedicated Ubuntu node and installed through the Gate 026 reproducible
installation contract.

Result:
- Ubuntu 24.04.5 LTS / Python 3.12.3;
- deterministic regression: `317/317 PASS`;
- repeated wheel SHA-256: identical;
- installed-package boundary: `PASS`;
- pip dependency check: `PASS`;
- repository HEAD preserved;
- generated `build/` residue removed after verifying it contained no tracked files;
- final worktree: `CLEAN`.

This validates the node as a real Linux Engineering AI execution environment,
not as a second control plane.

---

## 2026-09-27 — Gate 033 opened

Issue #66 / draft PR #67.

Branch:
`gate-033-persistent-project-memory-provenance`

Base:
`79fd557c645f9310c5729400cfe7ba5fcf61ffa0`

Purpose:
close the v1.0 persistent project memory with provenance criterion by integrated
acceptance of the already-accepted Gate 016 memory, Gate 017 retrieval and
Gate 018 lifecycle mechanisms without memory-architecture redesign.

---

## 2026-09-27 — Gate 033 dual-platform local acceptance checkpoint

Exact checkpoint head:
`5fefd2229c9d502f1e7cff712aa8b5fd7473d564`

Windows result:
- Gate 033 harness: `PASS_V1_0_PERSISTENT_PROJECT_MEMORY_PROVENANCE`;
- wrapper: `PASS`;
- deterministic regression: `318/318 PASS`;
- exact HEAD preserved;
- worktree clean.

Dedicated EngineeringAI-Ubuntu result:
- exact local Git-bundle checkout at the same head: `PASS`;
- Gate 033 harness: `PASS`;
- wrapper: `PASS`;
- deterministic regression: `318/318 PASS` in `50.565 s`;
- exact HEAD preserved;
- worktree clean.

Integrated assertions include persistence across reopen, project isolation,
provenance-preserving retrieval, exact source/evidence revision+SHA lifecycle
bindings, explicit source/evidence stale states, append-only history, advisory
model boundary and no automatic model/Blackboard context injection.

GitHub-hosted pull-request jobs on this checkpoint currently terminate before
any job step is recorded. That hosted execution condition remains unresolved
and is retained separately from the successful deterministic local validation.

Gate 033 remains:
`IMPLEMENTED_LOCAL_VALIDATED / HOSTED_CI_PENDING`

Release/fabrication:
`NOT_GRANTED`

Physical validation:
`PHYSICAL_NOT_EXECUTED`


---

## 2026-10-03 — Gate 033 hosted CI quota recovery

The Gate 033 PR had previously produced hosted workflow failures before any job
step executed. Billing inspection established the cause:
- GitHub Free Actions allowance exhausted: `2000 / 2000` minutes;
- Actions budget: `$0`;
- stop-usage: enabled.

No Gate 033 source correction was made for that condition.

After the monthly Actions allowance reset, the exact unchanged implementation
and evidence checkpoint
`044c8dfffa5dc5d24ba45839ac7e950b83ef0aed`
was rerun.

Results:
- generic validation `36308233803`: `PASS`;
- strict exact-head validation `36308233920`: `PASS`;
- Gate 033 `36308233810`: Ubuntu `PASS`, Windows `PASS`;
- Gate 032 `36308233969`: Ubuntu `PASS`, Windows `PASS`;
- Gate 031 `36308233951`: Ubuntu `PASS`, Windows `PASS`;
- Gate 030 `36308233801`: Ubuntu `PASS`, Windows `PASS`;
- Gate 029 `36308233830`: Ubuntu `PASS`, Windows `PASS`;
- Gate 028 `36308233887`: Ubuntu `PASS`, Windows `PASS`;
- Gate 027 `36308233860`: Ubuntu `PASS`, Windows `PASS`;
- Gate 026 `36308233804`: Ubuntu `PASS`, Windows `PASS`.

The successful same-head reruns confirm that the earlier pre-step failures were
external quota enforcement rather than an Engineering AI implementation failure.

Gate 033 now enters the ready-for-review documentation synchronization. The
resulting documentation head must pass its own exact-head CI set before branch
freeze and explicit human exact-SHA squash-merge approval.

Release/fabrication:
`NOT_GRANTED`

Physical validation:
`PHYSICAL_NOT_EXECUTED`


---

## 2026-10-03 — Gate 033 final acceptance and Gate 034 opening

Gate 033 final approved PR head:
`6d2cdd1e98741ea5cc11562c4f20382bd1fef10b`

All final hosted workflows on that exact head passed, including generic,
strict exact-head, Gate 033 and inherited Gates 026–032.

PR #67 was squash-merged as:
`302d96a670f5197a496c583bc6faea60b16a5d87`

Issue #66 was closed as:
`COMPLETED`

Gate 034 was then opened from that exact accepted main:
- Issue #68: `OPEN`;
- branch: `gate-034-model-tool-failure-recovery`;
- Draft PR #69;
- opening head: `b15c231d7adc56bce8100ce2fb2ba3fa228d2304`.

Opening reconciliation found that bounded Supervisor tool retry, persisted queue
restart/deadline recovery, process timeout handling, approval persistence and
bounded structured-output correction already exist. The implementation scope is
therefore limited to the demonstrated integration gaps: model-provider failure
must become a bounded fail-closed orchestration result, and role-loop tool
failure must reuse the existing Supervisor retry classification rather than
invent a second authority path.

Release/fabrication:
`NOT_GRANTED`

Physical validation:
`PHYSICAL_NOT_EXECUTED`


---

## 2026-10-05 — Gate 034 dual-platform implementation validation checkpoint

Implementation head:
`146c16e20d0a80c5a722560226c55af9886d1207`

Gate 034 acceptance harness on the implementation head reported:
`PASS_V1_0_DOCUMENTED_MODEL_TOOL_FAILURE_RECOVERY`.

Validated recovery properties include:
- model-provider failure enters bounded `QUEUED` retry or terminal `FAIL`;
- failed model calls are auditable;
- model retry state persists across queue reopen and can recover to `PASS`;
- deterministic role-loop tool failure reuses the Supervisor-owned
  attempts/retry_limit classifier;
- malformed structured model output remains bounded and fails closed after
  retry exhaustion;
- process timeout is structured;
- offline network-capable process execution is blocked before execution;
- interrupted persisted RUNNING work recovers to `BLOCKED`;
- late PASS after persisted deadline expiry is rejected as
  `TIMEOUT_RECOVERY`;
- policy denial consumes no retry and calls no tool;
- WAITING_FOR_APPROVAL survives reopen and never self-approves;
- no tested failure/recovery boundary produced false PASS.

Local Windows:
- Gate 034 harness: `PASS`;
- wrapper: `PASS`;
- deterministic regression: `319/319 PASS`;
- exact implementation HEAD preserved;
- final worktree: `CLEAN`.

The first Windows wrapper invocation was interrupted by Windows PowerShell
stderr-to-NativeCommandError handling even though unittest had already reported
the Gate 034 test as `ok`. The invocation wrapper was corrected to capture
stdout/stderr separately; no Engineering AI source, test or validator change
was made, and the same exact head then passed wrapper and full regression.

Dedicated EngineeringAI-Ubuntu:
- Ubuntu 24.04.5 LTS / Python 3.12.3;
- exact implementation HEAD imported by verified Git bundle;
- Gate 034 harness: `PASS`;
- wrapper: `PASS`;
- deterministic regression: `319/319 PASS` in `51.121 s`;
- exact implementation HEAD preserved;
- final worktree: `CLEAN`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

The initial transfer attempt targeted a stale dynamic Hyper-V Default Switch
guest address while the VM was powered off. After startup, the VM was
identified by its fixed virtual NIC MAC and current DHCP address; SSH host
identity was verified before transfer. This was infrastructure transport
recovery, not a Gate 034 source failure, and no source/test/validator change
was made.

Hosted validation on the same implementation head:
- Gate 034 workflow `37111284820`: Ubuntu `PASS`, Windows `PASS`;
- strict exact-head workflow `37111284731`: `PASS`;
- generic workflow `37111284747`: `PASS`;
- Gate 026 workflow `37111284752`: `PASS`;
- Gate 027 workflow `37111284755`: `PASS`;
- Gate 028 workflow `37111284732`: `PASS`;
- Gate 029 workflow `37111284805`: `PASS`;
- Gate 030 workflow `37111284730`: `PASS`;
- Gate 031 workflow `37111284751`: `PASS`;
- Gate 032 workflow `37111284750`: `PASS`;
- Gate 033 workflow `37111284728`: `PASS`.

Gate 034 now enters final documentation-only synchronization. The resulting
documentation head must pass its own hosted CI before any Ready for Review
transition. PR #69 remains `DRAFT`.

Release authorization:
`NOT_GRANTED`

Fabrication authorization:
`NOT_GRANTED`

Physical validation:
`PHYSICAL_NOT_EXECUTED`

---

## 2026-10-07 — Gate 034 final acceptance and Gate 035 opening

Gate 034 source-of-truth reconciliation confirmed:
- Issue #68: `CLOSED / COMPLETED`;
- PR #69: `MERGED`;
- final PR head: `30da5eb9ba1dbeaf54cbc2eacd3e0802ab99fcfe`;
- squash merge: `6db84082e45f3e00a555f5af79f66c1fc6b48ea6`;
- final Gate 034 workflow `37251626010`: `PASS`;
- final strict exact-head workflow `37251626074`: `PASS`;
- final generic workflow `37251626129`: `PASS`;
- inherited Gate 026–033 workflows on the same exact head: `PASS`.

The ECC comparative audit exposed that generic `Supervisor.execute()` could mark a
job `PASS` from `ToolOutcome.ok=true` without proving closure of the job's
declared `required_validators`. Read-only reconciliation against
`ARCHITECTURE.md` and `DECISIONS.md` established that this is not a new
architecture requirement: accepted architecture already requires validation
before work is marked complete and requires completion states to reference
actual validator/evidence results.

Human authorization therefore opened Gate 035 as a narrow v1.0 conformance
remediation, not an architecture redesign.

Gate 035 opening:
- Issue #72: `OPEN`;
- branch: `gate-035-deterministic-acceptance-contract-conformance`;
- base: `6db84082e45f3e00a555f5af79f66c1fc6b48ea6`;
- Draft PR #73: `OPEN`.

Authorized scope:
- close declared `required_validators` against explicit validator outcome,
  evidence and exact repository revision before generic job `PASS`;
- keep jobs with genuinely empty `required_validators` working;
- prevent Reviewer/model `ACCEPT` from replacing deterministic validation;
- add deterministic negative/positive regression evidence;
- synchronize source of truth after the already-completed Gate 034 merge.

Explicitly out of scope:
- architecture redesign;
- ECC feature adoption;
- retrieval/context/memory changes;
- model routing/qualification changes;
- PlataVM/BuoyCalc project-specific validator semantic changes;
- release/fabrication authority;
- physical-validation claims.

Planned post-Gate-035 route:
Gate 036 controlled PlataVM+BuoyCalc use -> Gate 037 practical model/runtime
replacement -> final v1.0 cold-start/source-of-truth readiness audit.

Release authorization:
`NOT_GRANTED`

Fabrication authorization:
`NOT_GRANTED`

Physical validation:
`PHYSICAL_NOT_EXECUTED`

---

## 2026-10-07 — Gate 035 implementation/evidence checkpoint

Exact implementation/evidence checkpoint:
`38b6db633c24963d6afbec1f62a6a817172129b1`

Gate 035 closes the generic required-validator completion gap against the
already accepted architecture without introducing a new authority model.

Validated behavior:
- tool `ok=true` does not imply job `PASS` when declared required validators
  remain unresolved;
- exact-revision, evidence-backed validator `PASS` may close its declared
  requirement;
- exact-revision, evidence-backed validator `FAIL` fails the job;
- missing, `NOT_RUN`, timed-out, revision-mismatched or evidence-less
  validator outcomes cannot produce job `PASS`;
- stale or evidence-less decisive `PASS/FAIL` results are not promoted into
  current validation state;
- Reviewer `ACCEPT` cannot replace deterministic required validation;
- jobs with genuinely empty `required_validators` preserve the accepted
  no-validator completion path.

Hosted validation on the exact checkpoint:
- Gate 035 `37535951540`: Ubuntu `PASS`, Windows `PASS`;
- generic `37535951408`: `PASS`;
- strict exact-head `37535951618`: `PASS`;
- Gate 034 `37535951403`: `PASS`;
- Gate 033 `37535952500`: `PASS`;
- Gate 032 `37535951506`: `PASS`;
- Gate 031 `37535951440`: `PASS`;
- Gate 030 `37535951456`: `PASS`;
- Gate 029 `37535951415`: `PASS`;
- Gate 028 `37535951821`: `PASS`;
- Gate 027 `37535951394`: `PASS`;
- Gate 026 `37535951426`: Ubuntu `PASS`, Windows `PASS`.

PR #73 remains `DRAFT`. A final documentation/source-of-truth exact-head CI
set remains required before any Ready for Review transition.

Release authorization:
`NOT_GRANTED`

Fabrication authorization:
`NOT_GRANTED`

Physical validation:
`PHYSICAL_NOT_EXECUTED`

