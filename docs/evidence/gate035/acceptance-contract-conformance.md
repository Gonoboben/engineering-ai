# Gate 035 — deterministic acceptance-contract conformance

## Purpose

Gate 035 is a conformance remediation against the already accepted Engineering AI architecture. It does not introduce a new authority model.

Accepted architecture already requires:
- Supervisor validation before work is marked complete;
- jobs to carry required validators;
- deterministic evidence to outrank model/reviewer claims;
- completion states to reference actual validator/evidence results.

## Base

Exact accepted main before Gate 035:

`6db84082e45f3e00a555f5af79f66c1fc6b48ea6`

This is the squash merge commit for Gate 034 / PR #69.

## Scope

The generic Supervisor completion boundary now distinguishes:
- successful tool execution;
- required-validator closure;
- terminal job completion.

The effective required-validator set is the deterministic union of
project-policy `mandatory_validators` and job-declared `required_validators`.
A job may proceed through non-terminal work without duplicating policy validators
in its own declaration, but it cannot obtain terminal `PASS` while any effective
required validator remains unresolved.

A required validator closes a job only when:
1. its validator ID is declared by the job;
2. the validator state is `PASS`;
3. it did not time out;
4. it carries non-empty evidence references;
5. its recorded repository HEAD equals the current exact repository HEAD.

Missing, `NOT_RUN`, timed-out, evidence-less or revision-mismatched required validators block completion. Only an exact-revision validator `FAIL` with non-empty evidence fails the current job; stale or evidence-less `FAIL` remains non-authoritative for the current revision and blocks completion instead.

Jobs with an empty `required_validators` set retain the existing no-validator
completion path only when the project policy also declares no mandatory
validators. If policy validators exist, they remain effective completion
requirements even when the job-local list is empty.

The Planner/Executor/Reviewer loop uses the same deterministic completion boundary. Reviewer `ACCEPT` cannot substitute for a missing required validator.

## Explicit non-goals

Gate 035 does not:
- redesign the architecture;
- adopt ECC functionality;
- change PlataVM/BuoyCalc validator semantics;
- change model routing or qualification;
- create release/fabrication authority;
- claim physical validation.

## Validation semantics

`JOB PASS` remains distinct from:
- Gate acceptance;
- release authorization;
- fabrication authorization;
- physical validation.

Physical validation remains `PHYSICAL_NOT_EXECUTED`.

## Required evidence

Gate-specific deterministic coverage includes:
- project-policy mandatory validator omitted by the job -> execution may proceed, but terminal PASS is blocked until that validator closes;
- tool success + missing required validator -> not PASS;
- exact-revision evidence-backed required validator FAIL -> FAIL;
- stale-revision FAIL -> BLOCKED and is not promoted into current validation state;
- evidence-less FAIL -> BLOCKED and is not promoted into current validation state;
- timeout / NOT_RUN -> not PASS;
- PASS from another repository revision -> not PASS;
- PASS without evidence -> not PASS and is not promoted into current validation state;
- exact-revision PASS with evidence -> job may PASS;
- no-required-validator job -> existing PASS path preserved;
- undeclared validator result -> rejected;
- Reviewer ACCEPT cannot bypass a missing required validator;
- Reviewer ACCEPT plus exact validator evidence can complete.

Final exact-head CI and full regression remain required before any Ready for Review or merge decision.


## Current implementation/evidence checkpoint

The earlier checkpoint
`38b6db633c24963d6afbec1f62a6a817172129b1`
was superseded after post-review analysis found that project-policy
`mandatory_validators` were not included in the effective terminal completion
set.

Current exact checkpoint:
`e6770dff9a3c52124ae6e6650a64a7f696570343`

The effective required-validator set is now the deterministic union of
project-policy `mandatory_validators` and job-declared
`required_validators`. A policy-mandatory validator cannot be bypassed by
omitting it from the job-local list.

Hosted validation on the current exact checkpoint:
- Gate 035 workflow `37587374112`: `PASS`;
- generic validation `37587374030`: `PASS`;
- strict exact-head validation `37587374079`: `PASS`;
- Gate 034 `37587374040`: `PASS`;
- Gate 033 `37587374086`: `PASS`;
- Gate 032 `37587374074`: `PASS`;
- Gate 031 `37587374042`: `PASS`;
- Gate 030 `37587374041`: `PASS`;
- Gate 029 `37587374104`: `PASS`;
- Gate 028 `37587374026`: `PASS`;
- Gate 027 `37587374039`: `PASS`;
- Gate 026 `37587374052`: Ubuntu `PASS`; Windows `PASS` after rerunning
  the failed Windows job on the same exact checkpoint.

The first Windows Gate 026 attempt failed during temporary-directory cleanup in
the inherited Gate 034 timeout harness with `WinError 32/5`. Its failed-job
rerun passed on the unchanged source revision. No Gate 035 source, validator or
authority boundary was weakened to obtain PASS.

No local workstation or dedicated EngineeringAI-Ubuntu execution is claimed by
this Gate 035 checkpoint. The acceptance evidence above is GitHub-hosted CI on
the exact recorded revision.

Release authorization remains `NOT_GRANTED`.
Fabrication authorization remains `NOT_GRANTED`.
Physical validation remains `PHYSICAL_NOT_EXECUTED`.

The source-of-truth synchronization commit produced after this checkpoint must
pass its own full exact-head CI set before Ready for Review.

