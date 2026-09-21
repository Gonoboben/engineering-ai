# Gate 028 — v1.0 policy and approval enforcement acceptance

## Gate identity
- Issue: #55
- PR: #56 (READY FOR REVIEW)
- Branch: `gate-028-policy-approval-enforcement`
- Base: accepted Gate 027 squash merge
  `39ab8ee30364cafaebe87d6d9b5ab17430f5031e`

## Objective
Close the Phase 8 / v1.0 criterion for tested policy/approval enforcement by
revalidating already-accepted deterministic authority boundaries as one
cross-platform acceptance package.

Gate 028 is an acceptance Gate. It does not redefine Supervisor policy
semantics and does not broaden any tool, Git, network, disclosure, release,
fabrication or project-physics authority.

## Acceptance basis

The Gate 028 smoke executes the existing deterministic test modules for:
- Supervisor policy and execution;
- controlled BuoyCalc project mutation;
- external controlled review;
- controlled registered tool exposure.

It also executes the accepted Gate 019, Gate 021 and Gate 022 smoke harnesses
and checks their approval-specific structured results.

The acceptance package proves the following existing properties together:
- `DENY` is fail-closed and protected actions do not execute;
- `NEEDS_HUMAN_APPROVAL` is distinct from `ALLOW`;
- approval-required actions execute zero protected calls before valid approval;
- asserted approval without a named human identity is non-authorizing;
- a valid named approval authorizes only the intended bounded action;
- persisted `WAITING_FOR_APPROVAL` survives reopen and is never auto-approved;
- external providers are not called before disclosure approval;
- controlled tool handlers are not called before required approval;
- forbidden/unregistered capabilities remain blocked;
- audit/ledger integrity checks remain part of the accepted modules.

## Cross-platform validation

Gate-specific workflow:
`.github/workflows/gate028-policy-approval.yml`

The workflow checks out and verifies the exact pull-request head independently
on Ubuntu and Windows, installs the package, and executes:

`python scripts/gate028_policy_approval_acceptance.py`

Validated implementation/ready checkpoint:
`5458c1bdd930d0d80671f42bc665807f12c8d215`

Validation:
- deterministic regression: `313/313 PASS`;
- generic workflow `35625528735`: `PASS`;
- strict exact-head workflow `35625528753`: `PASS`;
- Gate 028 policy/approval workflow `35625528680`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 027 offline workflow `35625528713`:
  Ubuntu `PASS`, Windows `PASS`;
- inherited Gate 026 install workflow `35625528728`:
  Ubuntu `PASS`, Windows `PASS`.

PR #56 was marked ready for review after this checkpoint passed.
A final source-of-truth synchronization head requires one last exact-head
validation set before explicit human squash-merge approval.

## Authority boundaries
- policy architecture: unchanged;
- remote Git mutation authority: not granted;
- external disclosure authority: unchanged and approval-gated;
- generic shell/filesystem write authority: not granted;
- release authorization: `NOT_GRANTED`;
- fabrication authorization: `NOT_GRANTED`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

## Gate state
Implementation is validated at the recorded checkpoint and PR #56 is ready for review. Final Gate acceptance remains pending one final exact-head validation set and explicit human exact-SHA squash-merge approval.
