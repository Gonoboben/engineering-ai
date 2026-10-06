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

A required validator closes a job only when:
1. its validator ID is declared by the job;
2. the validator state is `PASS`;
3. it did not time out;
4. it carries non-empty evidence references;
5. its recorded repository HEAD equals the current exact repository HEAD.

Missing, `NOT_RUN`, timed-out, evidence-less or revision-mismatched required validators block completion. Explicit validator `FAIL` makes the job fail.

Jobs with an empty `required_validators` set retain the existing no-validator completion path.

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
- tool success + missing required validator -> not PASS;
- required validator FAIL -> FAIL;
- timeout / NOT_RUN -> not PASS;
- PASS from another repository revision -> not PASS;
- PASS without evidence -> not PASS;
- exact-revision PASS with evidence -> job may PASS;
- no-required-validator job -> existing PASS path preserved;
- undeclared validator result -> rejected;
- Reviewer ACCEPT cannot bypass a missing required validator;
- Reviewer ACCEPT plus exact validator evidence can complete.

Final exact-head CI and full regression remain required before any Ready for Review or merge decision.
