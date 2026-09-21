# Gate 030 — v1.0 auditable state transitions acceptance

## Gate identity
- Issue: #59
- PR: #60 (DRAFT)
- Branch: `gate-030-auditable-state-transitions`
- Base: accepted Gate 029 squash merge
  `f76cc2a2db329a43bff2ff47f9dcd2039e37e05d`

## Objective
Close the Phase 8 / v1.0 criterion for auditable state transitions by
revalidating the already-accepted Supervisor, memory, queue, schedule and
controlled-ledger transition boundaries as one cross-platform acceptance
package.

Gate 030 is an acceptance Gate. It does not redefine state-machine semantics,
add automatic approval, make history mutable, weaken integrity checks, or
expand tool/Git/network/release/fabrication authority.

## Acceptance basis
The Gate 030 smoke executes the existing deterministic test modules for:
- Supervisor policy/state/audit transitions;
- append-only decision/evidence memory;
- append-only knowledge lifecycle;
- persisted job queue;
- scheduled unattended runs;
- external controlled review ledger;
- controlled registered tool invocation ledger.

It also executes the accepted Gate 018, 019, 020, 021 and 022 smoke harnesses
and checks their structured results.

The acceptance package proves the following existing properties together:
- Supervisor execution/approval/blocked paths emit deterministic audit records;
- approval-blocked and forbidden actions do not silently advance state;
- knowledge lifecycle history is append-only and source-revision drift is
  detected and invalidated;
- persisted job state survives reopen and interrupted RUNNING work recovers
  fail-closed;
- WAITING_FOR_APPROVAL survives reopen without automatic approval;
- schedule state survives reopen with integrity verification;
- controlled external review/tool ledgers survive reopen and preserve
  integrity;
- tamper-detection tests remain part of the deterministic suites;
- no physical-validation status is inferred from software/audit state.

## Cross-platform validation
Gate-specific workflow:
`.github/workflows/gate030-auditable-state-transitions.yml`

The workflow checks out and verifies the exact pull-request head independently
on Ubuntu and Windows, installs the package, and executes:

`python scripts/gate030_auditable_state_transitions.py`

Final run IDs and exact-head results will be recorded after validation.

## Authority boundaries
- state-machine semantics: unchanged;
- history rewrite authority: not granted;
- automatic approval: prohibited;
- remote Git mutation authority: not granted;
- release authorization: `NOT_GRANTED`;
- fabrication authorization: `NOT_GRANTED`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

## Gate state
Implementation is pending exact-head deterministic validation and review.
