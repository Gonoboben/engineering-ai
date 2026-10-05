# Gate 034 — Documented model/tool failure recovery acceptance

## Gate identity

- Issue: #68
- Branch: `gate-034-model-tool-failure-recovery`
- Base: Gate 033 squash merge
  `302d96a670f5197a496c583bc6faea60b16a5d87`
- State: `IMPLEMENTATION_VALIDATED / FINAL_DOCUMENTATION_CI_REQUIRED`

## Objective

Close the v1.0 documented model/tool failure recovery criterion by integrating
and revalidating the recovery mechanisms already present in the accepted
Engineering AI architecture.

This Gate must not redesign the control plane merely to create a new recovery
layer. New implementation is justified only where the opening reconciliation
demonstrates a concrete gap.

## Opening reconciliation

Existing accepted mechanisms already include:

- bounded Supervisor tool retry using job `attempts` and `retry_limit`;
- explicit terminal FAIL after retry exhaustion;
- persisted job queue with append-only integrity-checked history;
- fail-closed interrupted RUNNING recovery;
- persisted run-deadline timeout recovery;
- rejection of late PASS after deadline expiry;
- WAITING_FOR_APPROVAL persistence across reopen without automatic approval;
- explicit process timeout results from the allow-listed process runner;
- bounded structured-output correction for Planner/Reviewer model protocol;
- local Ollama provider classification of transport/runtime failures as
  `ModelProviderUnavailable`;
- model protocol failures classified as `ModelProviderProtocolError`.

## Reconciled gaps to prove or close

1. Model-provider unavailability/timeout currently has a typed provider error
   boundary, but the Planner/Executor/Reviewer loop does not yet prove a
   deterministic fail-closed recovery result for that exception path.
2. Role-loop deterministic tool failure currently terminates the loop, while
   the lower-level Supervisor already owns a bounded retry contract; Gate 034
   must prove the intended integration without creating duplicate authority.

## Acceptance focus

- model runtime unavailable / model request timeout;
- malformed model protocol with bounded correction;
- deterministic tool failure with bounded retry;
- process timeout;
- interrupted persisted RUNNING job recovery;
- persisted deadline expiry;
- policy/offline/authority denial remains non-retriable unless explicitly
  classified otherwise;
- WAITING_FOR_APPROVAL never self-approves after restart;
- recovery preserves project/job identity, attempt count, blockers, evidence
  provenance and append-only history;
- no failure path can be converted into a false PASS.

## Explicitly out of scope

- architecture redesign;
- unbounded retry;
- automatic approval;
- new model qualification;
- new tool/Git/network authority;
- connected-project production work;
- validator weakening;
- release/fabrication authorization;
- physical-validation claims.

## Authority state

- architecture change: `NOT_GRANTED`
- validator weakening: `PROHIBITED`
- release authorization: `NOT_GRANTED`
- fabrication authorization: `NOT_GRANTED`
- physical validation: `PHYSICAL_NOT_EXECUTED`


## Implementation integration checkpoint

Gate 034 adds no new recovery subsystem.

The minimal integration is:
- `Supervisor.classify_tool_failure(...)` exposes the existing
  attempts/retry_limit classification as a side-effect-free policy helper;
- the existing `Supervisor.execute(...)` failure path is refactored to call
  that same classifier, preserving prior behavior;
- Planner/Executor/Reviewer orchestration catches typed `ModelProviderError`
  failures and converts them into bounded `QUEUED` retry or terminal `FAIL`
  job state instead of allowing an uncontrolled provider exception to escape;
- failed model calls are auditable `MODEL_CALL / FAIL` events;
- role-loop deterministic tool failures use the Supervisor classifier and
  return `QUEUED` or `FAIL` according to the same job retry contract;
- recovery retry blockers are cleared after a later non-QUEUED terminal result.

Gate-specific acceptance harness:
`scripts/gate034_model_tool_failure_recovery.py`

Regression wrapper:
`tests/test_gate034_model_tool_failure_recovery.py`

Cross-platform workflow:
`.github/workflows/gate034-model-tool-failure-recovery.yml`

## Validation checkpoint

Implementation head:
`146c16e20d0a80c5a722560226c55af9886d1207`

Gate-specific acceptance state:
`PASS_V1_0_DOCUMENTED_MODEL_TOOL_FAILURE_RECOVERY`

Validated behavior:
- model-provider unavailability enters bounded `QUEUED` retry and preserves
  the incremented attempt count across persisted queue reopen;
- successful provider recovery can later complete `PASS` without resetting
  the recorded attempt;
- model-provider retry exhaustion terminates `FAIL`;
- failed model calls are recorded as `MODEL_CALL / FAIL`;
- role-loop deterministic tool failures reuse
  `Supervisor.classify_tool_failure(...)` and the existing
  attempts/retry_limit contract;
- successful tool retry can later complete `PASS`;
- tool retry exhaustion terminates `FAIL`;
- malformed structured model output can recover within the bounded correction
  allowance and terminates `FAIL` after exhaustion;
- allow-listed process timeout is returned as structured non-PASS evidence;
- offline mode blocks network-capable process execution before launch;
- persisted interrupted RUNNING work recovers to
  `INTERRUPTED_RECOVERY / BLOCKED`;
- persisted late PASS after deadline expiry is rejected as
  `TIMEOUT_RECOVERY / BLOCKED`;
- policy denial calls no tool and consumes no retry attempt;
- WAITING_FOR_APPROVAL survives reopen without synthesized approval;
- queue integrity remains valid;
- no tested failure/recovery path produced false PASS.

### Local Windows

- Gate 034 harness: `PASS`;
- Gate 034 wrapper: `PASS`;
- deterministic regression: `319/319 PASS` in `129.396 s`;
- exact source revision preserved:
  `146c16e20d0a80c5a722560226c55af9886d1207`;
- final worktree: `CLEAN`.

The first wrapper command was interrupted by Windows PowerShell interpreting
unittest stderr output as `NativeCommandError` even though the test itself had
reported `ok`. The wrapper invocation was corrected by capturing stdout and
stderr separately. No Engineering AI source, test or validator change was made
between attempts.

### Dedicated EngineeringAI-Ubuntu

- Ubuntu 24.04.5 LTS;
- Python 3.12.3;
- exact source revision transferred by verified Git bundle;
- Gate 034 harness: `PASS`;
- Gate 034 wrapper: `PASS`;
- deterministic regression: `319/319 PASS` in `51.121 s`;
- exact source revision preserved:
  `146c16e20d0a80c5a722560226c55af9886d1207`;
- final worktree: `CLEAN`;
- queue/recovery validation did not require external network authority;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

An initial SSH transfer attempt used a stale dynamic Hyper-V Default Switch
guest address while the VM was powered off. The running VM was then identified
by its fixed virtual NIC MAC, its current DHCP address was resolved, and the
SSH host key was verified before transfer. This was retained as infrastructure
transport evidence and required no Engineering AI source/test/validator change.

### Hosted CI on the same implementation head

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

### Remaining acceptance step

This file is part of the final documentation-only synchronization. The
resulting documentation head must pass its own hosted CI set before Gate 034
may move from Draft to Ready for Review.

PR #69 remains `DRAFT`.

Ready for Review: `NOT_AUTHORIZED`.

Merge: `NOT_AUTHORIZED`.

Release authorization: `NOT_GRANTED`.

Fabrication authorization: `NOT_GRANTED`.

Physical validation: `PHYSICAL_NOT_EXECUTED`.
