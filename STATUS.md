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
- Control-plane architecture: `ACCEPTED_BASELINE`
- Human architecture approval: `APPROVED`

## Current Gate
- Gate: `004 — Tool adapter foundation`
- Issue: `#7`
- PR: `#8`
- Branch: `gate-004-tool-adapter-foundation`
- State: `VALIDATION_PASS_PENDING_FINAL_EXACT_HEAD_CI_AND_REVIEW`

## Architecture / implementation state
- Python package skeleton: `IMPLEMENTED_VALIDATED`
- Gate 002 schemas/semantic validation: `IMPLEMENTED_VALIDATED`
- Deterministic policy engine: `IMPLEMENTED_VALIDATED`
- Supervisor state machine: `IMPLEMENTED_VALIDATED`
- Approval/forbidden/retry/audit enforcement: `IMPLEMENTED_VALIDATED`
- Root-bounded read-only filesystem adapter: `IMPLEMENTED_VALIDATED`
- Read-only Git adapter: `IMPLEMENTED_VALIDATED`
- Allow-listed fixed-profile process runner: `IMPLEMENTED_VALIDATED`
- Arbitrary shell execution: `NOT_IMPLEMENTED_PROHIBITED`
- Filesystem writes/deletes: `NOT_IMPLEMENTED`
- Git mutation operations: `NOT_IMPLEMENTED`
- Project-specific adapters: `NOT_IMPLEMENTED`
- Model interface runtime: `DESIGNED_NOT_IMPLEMENTED`
- Local model runtime: `NOT_SELECTED`
- Engineering memory runtime: `DESIGNED_NOT_IMPLEMENTED`
- Multi-agent routing: `DEFERRED`
- Vision/image/CAD workers: `DEFERRED`
- External/OpenAI bridge: `OPTIONAL_NOT_IMPLEMENTED`

## Connected engineering projects
- PlataVM: `NOT_CONNECTED`
- BuoyCalc: `NOT_CONNECTED`

Gate 004 does not access or modify either engineering project.

## Gate 003 validation state
- Gate 002 regression tests: `PASS`
- Supervisor tests: `PASS`
- local Windows/Python 3.12 exact-branch-head validation: `18/18 PASS`
- human merge approval: `PASS`
- squash merge: `PASS`

Historical CI note:
- the original `pull_request` workflow used the default GitHub PR merge-ref checkout;
- prior Gate 002/003 GitHub Actions results were therefore merge-ref validation, not strict branch-head validation;
- this terminology was corrected during Gate 004;
- local Gate 002/003 Windows validations were executed on the stated branch heads and remain valid evidence.

## Gate 004 validation state
- Gate 002/003 regression suite: `PASS`
- filesystem root-boundary/read-limit tests: `PASS`
- symlink/root escape test on Linux CI: `PASS`
- process allow-list test: `PASS`
- process timeout test: `PASS`
- bounded stdout/stderr test: `PASS`
- root-bounded process cwd test: `PASS`
- Git read-only status/branch/head/log/diff tests: `PASS`
- generic Git command API absence test: `PASS`
- Linux CI tests run: `28`; result: `OK`
- exact-head workflow added: `PASS`
- exact-head revision verification on `73c025b5d8676c464beeb059cb5cbc3b0980488e`: `PASS`
- exact-head revision verification on documentation head `aea2921caad82b6792e3d6adb3eb7518f2b89afd`: `PASS`
- local Windows/Python 3.12 validation on `aea2921caad82b6792e3d6adb3eb7518f2b89afd`: `PASS`
- local tests run: `28`; failures: `0`; errors: `0`; result: `OK`; working tree: `CLEAN`
- final exact-head CI after this validation-record commit: `PENDING`
- physical validation: `PHYSICAL_NOT_EXECUTED`

## Primary workstation status
- host: Windows 11 Pro build `10.0.22000` (`KNOWN_PLATFORM_RISK`, not a current blocker)
- Git: `2.55.0.windows.3`
- GitHub CLI: `2.101.0`, authenticated as `Gonoboben`
- Python: `3.12.10`
- NVIDIA GPU: `GeForce RTX 3060 Ti, 8192 MiB`
- repository checkout: `C:\workspace\repos\engineering-ai`
- local `.venv`: present and ignored by Git

Security constraint for future local services:
default to loopback/local-only exposure until an explicit network-security decision permits broader access.

## Global invariants
- repository/project state is authoritative, not chat/model memory;
- offline-first operation;
- replaceable models;
- deterministic validators outrank model claims;
- non-LLM Supervisor controls policy and state transitions;
- runtime state may tighten project policy but may not relax it;
- tool adapters expose narrow typed operations rather than arbitrary command execution;
- project repositories remain independent;
- validator weakening for PASS is prohibited;
- simulation does not imply physical validation;
- material actions are auditable;
- human approval remains mandatory at defined irreversible/architecture/physics boundaries;
- single-agent core precedes multi-agent expansion.

## Next admissible action
Confirm final exact-head GitHub Actions PASS for the head containing this local-validation record, complete PR #8 consistency review, and mark PR #8 ready for human merge approval.

Gate 005 — Local model interface — is not admissible until Gate 004 is reviewed and merged.
