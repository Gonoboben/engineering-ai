# STATUS.md

## Project
`Gonoboben/engineering-ai`

## Mission
Build a local-first, auditable engineering AI control plane that can safely continue real engineering projects using replaceable AI models plus deterministic tools and validators.

## Accepted baseline
- Gate 001: `ACCEPTED_MERGED`
- Gate 001 merge commit: `e10f949a6e860deed2104af770909bae1d043a53`
- Gate 002: `ACCEPTED_MERGED`
- Gate 002 merge commit: `90df86ceebfb3ee6166a959fcf84172e989c646a`
- Gate 003: `ACCEPTED_MERGED`
- Gate 003 merge commit: `bb073ea212676ecc17d50131beee41842bd2eed2`
- Gate 004: `ACCEPTED_MERGED`
- Gate 004 merge commit: `bc950ded14487b0de90e9209589486fe6bfd83f2`
- Gate 005: `ACCEPTED_MERGED`
- Gate 005 merge commit: `ddf6fd9420bc60d3d812a17b948f7319e2cb63cd`
- Control-plane architecture: `ACCEPTED_BASELINE`
- Human architecture approval: `APPROVED`

## Current Gate
- Gate: `006 — Planner / Executor / Reviewer loop`
- Issue: `#11`
- PR: `PENDING_DRAFT`
- Branch: `gate-006-planner-executor-reviewer`
- State: `RUNTIME_SMOKE_PASS_PENDING_FINAL_EXACT_HEAD_CI_AND_HUMAN_APPROVAL`

## Architecture / implementation state
- Python package skeleton: `IMPLEMENTED_VALIDATED`
- Gate 002 schemas/semantic validation: `IMPLEMENTED_VALIDATED`
- Deterministic Supervisor: `IMPLEMENTED_VALIDATED`
- Approval/forbidden/retry/audit enforcement: `IMPLEMENTED_VALIDATED`
- Root-bounded read-only filesystem adapter: `IMPLEMENTED_VALIDATED`
- Read-only Git adapter: `IMPLEMENTED_VALIDATED`
- Allow-listed fixed-profile process runner: `IMPLEMENTED_VALIDATED`
- Arbitrary shell execution: `NOT_IMPLEMENTED_PROHIBITED`
- Filesystem writes/deletes: `NOT_IMPLEMENTED`
- Git mutation operations: `NOT_IMPLEMENTED`
- Replaceable model request/response interface: `IMPLEMENTED_VALIDATED`
- Provider-neutral benchmark harness: `IMPLEMENTED_VALIDATED`
- Loopback-only Ollama provider: `IMPLEMENTED_VALIDATED_INTERFACE`
- Model-proposed tool execution inside provider: `NOT_IMPLEMENTED_PROHIBITED`
- Initial runtime selection: `OLLAMA_VALIDATED_ON_WORKSTATION`
- Initial model selection: `GPT_OSS_20B_MEDIUM_ACCEPTED`
- Selected model: `gpt-oss:20b`
- Selected baseline reasoning level: `medium`
- Baseline context: `8192`
- Benchmark-equivalent max output: `2048`
- Candidate A: `gpt-oss:20b` — `4/4 PASS` at `medium`; `high` reproducibly truncates two structured-output cases and is not the default
- Candidate B: `qwen3.6:27b-q4_K_M` — `3 PASS / 1 INCONCLUSIVE_TRUNCATED`; memory-stable but ~2.45–2.55 eval tok/s and ~37.7 min aggregate benchmark time on this workstation
- Stretch candidate: `qwen3.6:35b` — `DEFERRED_NOT_JUSTIFIED_ON_CURRENT_WORKSTATION` after measured 27B CPU-heavy performance
- Planner / Executor / Reviewer loop: `IMPLEMENTED_RUNTIME_VALIDATED`
- Engineering memory runtime: `DESIGNED_NOT_IMPLEMENTED`
- Multi-agent routing: `DEFERRED`
- Vision/image/CAD workers: `DEFERRED`
- External/OpenAI bridge: `OPTIONAL_NOT_IMPLEMENTED`

## Connected engineering projects
- PlataVM: `NOT_CONNECTED`
- BuoyCalc: `NOT_CONNECTED`

Gate 006 does not access or modify either engineering project.

## Gate 004 validation state
- Gate 002/003 regression suite: `PASS`
- tool adapter suite: `PASS`
- local Windows/Python 3.12 validation: `28/28 PASS`, working tree clean
- strict exact-head workflow on final PR head `0fa74070764587e3959a15afa0148491fb6a944e`: `PASS`
- human merge approval: `PASS`
- squash merge: `PASS`

Historical CI note:
- the original generic `pull_request` workflow validates GitHub's merge ref;
- strict branch-head validation is performed by `.github/workflows/validate-exact-head.yml`, added in Gate 004.

## Gate 005 validation state
- stable request/response type tests: `PASS`
- loopback-only provider boundary tests: `PASS`
- Ollama request/response translation tests: `PASS`
- malformed tool-call rejection test: `PASS`
- benchmark harness tests: `PASS`
- Unicode-safe JSON evidence output regression: `PASS`
- output-budget/done-reason evidence handling: `PASS`
- truncation classified as `INCONCLUSIVE`, not deterministic FAIL: `PASS`
- provider timeout preserved as benchmark evidence instead of aborting the whole run: `IMPLEMENTED_VALIDATED`
- Gate 002–004 regression suite: `PASS`
- Ollama version on primary workstation: `0.34.1`
- local service host: `127.0.0.1:11434`, `PASS`
- model directory: `C:\workspace\models\ollama`, `PASS`
- `OLLAMA_NUM_PARALLEL=1`: `PASS`
- `OLLAMA_MAX_LOADED_MODELS=1`: `PASS`
- benchmark context baseline `OLLAMA_CONTEXT_LENGTH=8192`: `PASS`
- cloud disabled `OLLAMA_NO_CLOUD=1`: `PASS`
- NVIDIA GPU visible: `GeForce RTX 3060 Ti, 8192 MiB`, `PASS`
- Candidate A measured benchmark: `PASS`, `gpt-oss:20b / medium / 8192 / 2048`, `4/4`
- Candidate A active placement: `57% CPU / 43% GPU`, ~`7.38 GB` observed VRAM use, ~`16.3 GB` free RAM
- Candidate A `high` diagnostic: two independent runs reproduced `2 PASS + 2 INCONCLUSIVE_TRUNCATED`
- Candidate B measured benchmark: `3 PASS + 1 INCONCLUSIVE_TRUNCATED`, no deterministic FAIL
- Candidate B placement: `69% CPU / 31% GPU`, ~`7.62 GB` observed VRAM use, ~`12.8–13.4 GB` free RAM during run
- Candidate B throughput: ~`2.45–2.55 eval tokens/s`; aggregate four-case wall time ~`37.7 min`
- selected initial engineering model: `gpt-oss:20b`
- selected baseline reasoning: `medium`
- final Gate 005 branch head: `9d6677290ee5bbaf0253234c7b8d479c6a3f948e`
- final local Windows regression on final head: `39/39 PASS`
- final generic CI on final head: `PASS`
- final strict exact-head CI on final head: `PASS`
- human squash-merge approval: `PASS`
- squash merge commit: `ddf6fd9420bc60d3d812a17b948f7319e2cb63cd`
- Gate 005 state: `ACCEPTED_MERGED`
- physical validation: `PHYSICAL_NOT_EXECUTED`

## Gate 006 validation state
- Issue #11: `OPEN`
- draft PR #12: `OPEN`
- branch from Gate 005 merge commit: `PASS`
- typed Planner / Executor / Reviewer role separation: `IMPLEMENTED_VALIDATED`
- deterministic role state machine and illegal-transition rejection: `PASS`
- existing Supervisor remains authoritative for model-proposed tool policy/execution: `PASS`
- executor restricted to approved-plan and declared-job actions: `PASS`
- missing deterministic evidence cannot be promoted to completion: `PASS`
- bounded reviewer revision/retry behavior: `PASS`
- reviewer rejection -> terminal failure: `PASS`
- approval-required tool proposal -> no tool call / waiting boundary: `PASS`
- model/runtime/role audit identity: `PASS`
- Gate 002–005 regression suite: `PASS`
- deterministic suite on implementation head `61f8bc469e3ab827749d7a94a6a393e5715a237a`: `46/46 PASS`
- generic CI on implementation head `61f8bc469e3ab827749d7a94a6a393e5715a237a`: `PASS`
- strict exact-head CI on implementation head `61f8bc469e3ab827749d7a94a6a393e5715a237a`: `PASS`
- narrow local runtime smoke harness: `scripts/gate006_role_smoke.py`, `IMPLEMENTED`
- local `gpt-oss:20b / medium / 8192 / 2048` role-loop smoke attempt 1 on `30ade24c9128a0c44cd81a7e90f0740237d1711c`: `FAIL_RUNTIME_CONTRACT`, diagnosed and corrected
- corrected Executor tool-only response contract regression: `47/47 PASS` on `00b17d498f90e3970352f6264584f8b1fdb60d53`
- corrected-head generic CI: `PASS`
- corrected-head strict exact-head CI: `PASS`
- local runtime smoke attempt 2 on `7e20a4beaf617dfd118e4f7d1cb1c6ecc3e96942`: `FAIL_RUNTIME_CONTRACT` at Reviewer structured JSON boundary after successful deterministic evidence collection
- bounded structured-role protocol recovery regression: `50/50 PASS` on `0cb1756ebb8eb50ee4f45d883b42a0c14b1d2cca`
- corrected-head generic CI after Reviewer recovery: `PASS`
- corrected-head strict exact-head CI after Reviewer recovery: `PASS`
- local runtime smoke attempt 3 on `f3c434e630a10bbf016e28d6c873df4f79783c28`: `PASS` — `COMPLETE / PASS`, `read_repository`, evidence `sha256:STATUS.md:ac9f1cb5c40f9793a0342df00f7926b9b95af12e9f7e70b2f27b5710097b4b45`, Reviewer `ACCEPT`
- final strict exact-head CI after evidence/documentation updates: `NOT_RUN`
- physical validation: `PHYSICAL_NOT_EXECUTED`

## Primary workstation status
- host: Windows 11 Pro build `10.0.22000` (`KNOWN_PLATFORM_RISK`, not a current blocker)
- CPU: Intel Core i7-11700K
- RAM: 31.9 GB
- Git: `2.55.0.windows.3`
- GitHub CLI: `2.101.0`, authenticated as `Gonoboben`
- Python: `3.12.10`
- NVIDIA GPU: `GeForce RTX 3060 Ti, 8192 MiB`
- NVIDIA driver: `591.86`
- repository checkout: `C:\workspace\repos\engineering-ai`
- local `.venv`: present and ignored by Git
- Ollama: `0.34.1`, locally reachable on loopback

Security constraint for local model services:
- loopback/local-only exposure remains mandatory;
- no cloud model execution is used for Gate 006 acceptance evidence.

## Global invariants
- repository/project state is authoritative, not chat/model memory;
- offline-first operation;
- replaceable models;
- deterministic validators outrank model claims;
- non-LLM Supervisor controls policy and state transitions;
- runtime state may tighten project policy but may not relax it;
- tool adapters expose narrow typed operations rather than arbitrary command execution;
- model providers transport advisory output and proposed tool calls but never execute tools directly;
- project repositories remain independent;
- validator weakening for PASS is prohibited;
- simulation does not imply physical validation;
- material actions are auditable;
- human approval remains mandatory at defined irreversible/architecture/physics boundaries;
- single-agent core precedes multi-agent expansion.

## Next admissible action
Run final regression and strict exact-head CI on the final Gate 006 evidence/documentation head. If green, request explicit human squash-merge approval for PR #12 at that exact head SHA. Physical validation remains `PHYSICAL_NOT_EXECUTED`.
