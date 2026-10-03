# Gate 033 — Persistent project memory with provenance acceptance

## Gate identity

- Issue: #66
- Branch: `gate-033-persistent-project-memory-provenance`
- Base: accepted Gate 032 squash merge
  `79fd557c645f9310c5729400cfe7ba5fcf61ffa0`
- Gate 032 final approved PR head:
  `a89a2c7fdb2e472dd422121695d8492a31387b80`
- State: `READY_FOR_REVIEW / FINAL_DOCUMENTATION_CI_REQUIRED`

## Objective

Close the Phase 8 / v1.0 persistent-project-memory criterion by revalidating
the already accepted Gate 016 decision/evidence memory, Gate 017 retrieval
layer and Gate 018 knowledge lifecycle as one end-to-end provenance-preserving
project-memory acceptance package.

This Gate is acceptance hardening. It does not redesign or replace the accepted
memory architecture.

## Opening reconciliation

The accepted baseline already provides:

- append-only SQLite decision/evidence memory;
- persistent close/reopen behavior;
- project-scoped storage and lookup;
- exact record revision and canonical content SHA-256;
- explicit provenance, evidence refs and source refs;
- deterministic retrieval that preserves provenance and authority labels;
- latest/history semantics;
- exact lifecycle bindings to memory record identity, revision and SHA-256;
- explicit stale source/evidence revision detection;
- model-authored memory constrained to ADVISORY authority;
- human-only accepted ADR authority;
- software/deterministic evidence prohibited from synthesizing PHYSICAL PASS;
- automatic model/Blackboard context injection disabled.

The opening read-only reconciliation found no justified memory-architecture
redesign requirement. The remaining criterion is an integrated v1.0 acceptance
proof across persistence, retrieval, lifecycle provenance and project isolation.

## Acceptance package

Gate 033 must prove, as one integrated package:

1. persistent memory records survive close/reopen without identity or hash drift;
2. same memory IDs in different projects remain isolated;
3. cross-project storage/retrieval/lifecycle access fails closed;
4. retrieval after reopen preserves exact project, record, memory, revision,
   provenance, evidence/source refs and content SHA-256;
5. accepted lifecycle knowledge binds exact source/evidence revisions and hashes;
6. source/evidence revision drift produces an explicit stale assessment;
7. prior accepted/history records remain append-only and reconstructable;
8. MODEL/ADVISORY records cannot self-promote to accepted evidence;
9. automatic model/Blackboard context injection remains disabled;
10. physical-validation semantics remain unchanged;
11. full deterministic regression remains green;
12. Gate-specific acceptance passes on Ubuntu and Windows;
13. strict exact-head validation passes before ready-for-review transition.

## Explicitly out of scope

- memory architecture redesign or migration;
- semantic/vector retrieval;
- automatic memory promotion;
- automatic model/Blackboard injection;
- new model qualification;
- connected-project production work;
- project lifecycle registry implementation;
- machine-local path-resolution architecture;
- MCP transport implementation;
- new tool/Git/network authority;
- validator weakening;
- release/fabrication authorization;
- physical-validation claims.

## Authority state

- architecture change: `NOT_GRANTED`
- validator weakening: `PROHIBITED`
- release authorization: `NOT_GRANTED`
- fabrication authorization: `NOT_GRANTED`
- physical validation: `PHYSICAL_NOT_EXECUTED`

## Planned route after Gate 033

1. Gate 034 — documented model/tool failure recovery acceptance.
2. PlataVM handoff/readiness read-only audit.
3. Gate 035 — successful controlled use on PlataVM and BuoyCalc.
4. Gate 036 — practical model/runtime replaceability.
5. Final v1.0 cold-start/source-of-truth readiness audit.


## Final local dual-platform validation checkpoint

Exact implementation/evidence checkpoint head:
`044c8dfffa5dc5d24ba45839ac7e950b83ef0aed`

Windows primary workstation:
- Python: `3.12.10`;
- Gate 033 acceptance harness:
  `PASS_V1_0_PERSISTENT_PROJECT_MEMORY_PROVENANCE`;
- Gate 033 wrapper: `1/1 PASS`;
- full deterministic regression: `318/318 PASS` in `137.732 s`;
- source HEAD preserved: `PASS`;
- worktree after validation: `CLEAN`.

Dedicated EngineeringAI-Ubuntu execution node:
- exact Gate 033 bundle transferred locally and checked out at the same head;
- Gate 033 acceptance harness: `PASS`;
- Gate 033 wrapper: `PASS`;
- full deterministic regression: `318/318 PASS` in `50.398 s`;
- source HEAD preserved: `PASS`;
- worktree after validation: `CLEAN`;
- root filesystem after run: `30G total / 5.2G used / 24G available / 19%`;
- visible memory: `1.8 GiB`, approximately `1.3 GiB available`;
- swap: `2.0 GiB total / 0 used`;
- retained local log:
  `/home/andrey/gate033-final-ubuntu-044c8dff.log`.

This checkpoint is deterministic/local software validation only and does not
create any physical-validation claim.

## Gate 033 integrated assertions

The exact checkpoint demonstrated:
- persistent memory and lifecycle databases reopen successfully;
- source content SHA-256 is preserved across reopen;
- same memory identity remains isolated by `project_id`;
- cross-project get, retrieval leakage and lifecycle binding fail closed;
- retrieval after reopen preserves record/memory identity, revision, provenance,
  source/evidence refs and content SHA-256;
- lifecycle records preserve exact source/evidence revision+SHA bindings;
- source revision drift yields `STALE_SOURCE_REVISION`;
- evidence revision drift yields `STALE_EVIDENCE_REVISION`;
- lifecycle history remains append-only and prior hashes remain unchanged;
- MODEL/ADVISORY evidence self-promotion is rejected;
- automatic model/Blackboard context injection remains `false`;
- semantic/vector backend remains `DEFERRED_NOT_JUSTIFIED`;
- release/fabrication authority remains false;
- physical validation remains `PHYSICAL_NOT_EXECUTED`.

## GitHub-hosted quota incident and recovery

Initial pull-request runs on exact head
`044c8dfffa5dc5d24ba45839ac7e950b83ef0aed` concluded `failure` before any
job step was recorded. Account billing evidence then showed:
- GitHub Free Actions included minutes: `2000 / 2000 used`;
- Actions budget: `$0`;
- stop usage: enabled.

The initial hosted failures are therefore retained as
`HOSTED_CI_NOT_EXECUTED / INCLUDED_ACTIONS_MINUTES_EXHAUSTED`, not as
deterministic project test failures.

After the monthly Actions allowance reset on 2026-10-03, the failed workflows
were rerun on the unchanged exact source head:
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

No source, test, validator, architecture, policy or authority change occurred
between the quota-blocked first attempts and the successful same-head reruns.

The quota incident is resolved. This final ready-state documentation commit must
still pass its automatically triggered exact-head CI set before PR #67 may be
treated as frozen for explicit human exact-SHA squash-merge approval.
