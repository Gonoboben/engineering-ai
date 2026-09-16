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
- Control-plane architecture: `ACCEPTED_BASELINE`
- Human architecture approval: `APPROVED`

## Current Gate
- Gate: `005 — Local model interface and measured runtime selection`
- Issue: `#9`
- PR: `#10`
- Branch: `gate-005-local-model-interface`
- State: `MODEL_SELECTED_PENDING_FINAL_VALIDATION`

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
- Initial model selection: `GPT_OSS_20B_MEDIUM_SELECTED_PENDING_FINAL_VALIDATION`
- Selected model: `gpt-oss:20b`
- Selected baseline reasoning level: `medium`
- Baseline context: `8192`
- Benchmark-equivalent max output: `2048`
- Candidate A: `gpt-oss:20b` — `4/4 PASS` at `medium`; `high` reproducibly truncates two structured-output cases and is not the default
- Candidate B: `qwen3.6:27b-q4_K_M` — `3 PASS / 1 INCONCLUSIVE_TRUNCATED`; memory-stable but ~2.45–2.55 eval tok/s and ~37.7 min aggregate benchmark time on this workstation
- Stretch candidate: `qwen3.6:35b` — `DEFERRED_NOT_JUSTIFIED_ON_CURRENT_WORKSTATION` after measured 27B CPU-heavy performance
- Engineering memory runtime: `DESIGNED_NOT_IMPLEMENTED`
- Multi-agent routing: `DEFERRED`
- Vision/image/CAD workers: `DEFERRED`
- External/OpenAI bridge: `OPTIONAL_NOT_IMPLEMENTED`

## Connected engineering projects
- PlataVM: `NOT_CONNECTED`
- BuoyCalc: `NOT_CONNECTED`

Gate 005 does not access or modify either engineering project.

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
- strict exact-head CI on implementation head `19d136a0b2a1b82385f31125d6d530d6d53fb3bc`: `34/34 PASS`
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
- local Windows/Python 3.12 interface suite on implementation baseline: `34/34 PASS`
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
- final strict exact-head CI after selection/evidence commit: `PENDING`
- final local Windows regression on final Gate 005 head: `PENDING`
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
- loopback/local-only exposure is mandatory in Gate 005;
- no cloud model execution is used for Gate 005 acceptance evidence.

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
Run the final local Windows regression suite on the final Gate 005 branch head and confirm strict exact-head CI on the same head. If both pass, review PR #10 and request explicit human squash-merge approval for the exact final head SHA.

Gate 006 — Planner / Executor / Reviewer loop — is not admissible until Gate 005 is reviewed and merged.
