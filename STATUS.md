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
- Branch: `gate-005-local-model-interface`
- State: `INTERFACE_IMPLEMENTED_PENDING_CI_AND_LOCAL_RUNTIME_BENCHMARK`

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
- Replaceable model request/response interface: `IMPLEMENTED_PENDING_VALIDATION`
- Provider-neutral benchmark harness: `IMPLEMENTED_PENDING_VALIDATION`
- Loopback-only Ollama provider: `IMPLEMENTED_PENDING_VALIDATION`
- Model-proposed tool execution inside provider: `NOT_IMPLEMENTED_PROHIBITED`
- Initial runtime selection: `OLLAMA_PROVISIONAL_PENDING_LOCAL_INSTALL_VALIDATION`
- Initial model selection: `PENDING_MEASURED_BENCHMARK`
- Candidate A: `gpt-oss:20b`
- Candidate B: `qwen3.6:27b`
- Stretch candidate: `qwen3.6:35b` only if measured memory margin justifies it
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
- stable request/response type tests: `NOT_RUN`
- loopback-only provider boundary tests: `NOT_RUN`
- Ollama request/response translation tests: `NOT_RUN`
- malformed tool-call rejection test: `NOT_RUN`
- benchmark harness tests: `NOT_RUN`
- Gate 002–004 regression suite: `NOT_RUN_ON_GATE_005_HEAD`
- strict exact-head CI: `PENDING`
- local Windows/Python 3.12 interface suite: `PENDING`
- Ollama installation on primary workstation: `PENDING`
- `gpt-oss:20b` local benchmark: `PENDING`
- `qwen3.6:27b` local benchmark: `PENDING`
- selected initial engineering model: `PENDING`
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
- Ollama: `NOT_INSTALLED_OR_NOT_YET_VALIDATED`

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
Validate Gate 005 interface/provider code in strict exact-head CI, then install/configure Ollama loopback-only on the primary workstation and execute the recorded local candidate benchmarks before selecting the initial engineering model.

Gate 006 — Planner / Executor / Reviewer loop — is not admissible until Gate 005 is reviewed and merged.
