# Gate 034 — Documented model/tool failure recovery acceptance

## Gate identity

- Issue: #68
- Branch: `gate-034-model-tool-failure-recovery`
- Base: Gate 033 squash merge
  `302d96a670f5197a496c583bc6faea60b16a5d87`
- State: `OPENING / READ_ONLY_RECONCILIATION_COMPLETE`

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

Validation on the implementation head remains pending. No PASS is claimed by
this documentation checkpoint until the harness and full deterministic
regression execute successfully.
