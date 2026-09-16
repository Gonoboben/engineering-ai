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
- State: `INTERFACE_AND_RUNTIME_BASELINE_PASS_PENDING_MODEL_BENCHMARK`

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
- Initial runtime selection: `OLLAMA_PROVISIONAL_VALIDATED_ON_WORKSTATION`
- Initial model selection: `PENDING_MEASURED_BENCHMARK`
- Candidate A: `gpt-oss:20b` (~14 GB current Ollama package)
- Candidate B: `qwen3.6:27b-q4_K_M` (~17 GB current Ollama package)
- Stretch candidate: `qwen3.6:35b` (~23 GB current Ollama package) only if measured memory margin justifies it
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
- Gate 002–004 regression suite: `PASS`
- local Windows/Python 3.12 interface suite on `19d136a0b2a1b82385f31125d6d530d6d53fb3bc`: `34/34 PASS`
- local Git working tree after validation: `CLEAN`
- Ollama version on primary workstation: `0.34.1`
- Ollama API `/api/version`: `0.34.1`, `PASS`
- Ollama process list before model load: empty, expected
- local service host: `127.0.0.1:11434`, `PASS`
- model directory: `C:\workspace\models\ollama`, `PASS`
- `OLLAMA_NUM_PARALLEL=1`: `PASS`
- `OLLAMA_MAX_LOADED_MODELS=1`: `PASS`
- benchmark context baseline `OLLAMA_CONTEXT_LENGTH=8192`: `PASS`
- cloud disabled `OLLAMA_NO_CLOUD=1`: `PASS`
- NVIDIA GPU visible: `GeForce RTX 3060 Ti, 8192 MiB`, `PASS`
- measured candidate benchmark: `PENDING`
- selected initial engineering model: `PENDING`
- final strict exact-head CI after benchmark evidence: `PENDING`
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
Run the first measured local candidate benchmark (`gpt-oss:20b`) on the primary workstation, record CPU/GPU split, memory/resource data, throughput and machine-scored engineering results, then benchmark `qwen3.6:27b-q4_K_M` under the same settings before selecting the initial model.

Gate 006 — Planner / Executor / Reviewer loop — is not admissible until Gate 005 is reviewed and merged.
