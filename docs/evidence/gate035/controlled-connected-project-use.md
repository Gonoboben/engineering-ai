# Gate 035 — Controlled connected-project use acceptance

Date: 2026-10-05

State:
`OPENING_CONTRACT_IMPLEMENTED / HOSTED_CI_AND_REAL_PROJECT_PILOT_PENDING`

Issue:
`#70`

Branch:
`gate-035-controlled-connected-project-use`

Base:
`6db84082e45f3e00a555f5af79f66c1fc6b48ea6`

Draft PR:
`PENDING_DRAFT_CREATION`

## Purpose

Gate 035 closes the v1.0 criterion for successful controlled use on both real
connected projects, PlataVM and BuoyCalc.

The Gate does not require either product to be release-ready. It requires
Engineering AI to recover authoritative state, preserve project isolation,
apply project-specific policy and deterministic evidence correctly, and stop at
the correct authority boundary without false PASS.

The opening harness is a deterministic contract test only. It does not replace
the later real connected-project pilot.

## Accepted opening audit snapshot

### PlataVM

```text
main = dcba77466d4800c0e7a336a2771684e066f845db
Issue = #99
PR = #100 DRAFT
branch = agent/pcb-e-aux-hardware-current-v1-9
head = 11e746cfea7f9200415cf817b6cde928b6a2651a
```

The correction head has local deterministic evidence, but both current-head
GitHub native workflow runs terminated `CANCELLED` before validation steps.
That state is NON-PASS.

Required preserved barriers:

```text
PACKAGE_SET_NOT_READY
fabrication NOT_GRANTED
physical NOT_EXECUTED
population PROTOTYPE_BASIS_ONLY_NOT_RELEASED / UNDECIDED
series NOT_GRANTED
```

Local repository/semantic PASS may not imply native KiCad PASS or
Ready-for-Review/merge.

### BuoyCalc

```text
main = 325aee5ee3a9f64413e416a1206fc4e296d9723f
CURRENT RELEASE STATUS = NOT READY FOR v1.0
```

The exact main has the required current checks green. Issue #627 and Draft PR
#628 remain an independent remediation stream and are outside Gate 035 mutation
scope.

Owner process decision: BuoyCalc participation in Gate 035 is
`EXPERIMENTAL_VALIDATION_ONLY`. It is not an operational handoff to
Engineering AI. The owner intends to finish the BuoyCalc release through the
current owner/ChatGPT process and make any later handoff decision separately.

## Opening contract

The deterministic harness asserts:
- no hidden chat context is required by the declared acceptance contract;
- project IDs remain isolated;
- zero connected-project remote mutations;
- no connected-project primary-state mutation;
- no architecture, physics, validator, authority or core-runtime change;
- no automatic approval;
- PlataVM cancelled native evidence cannot become PASS or readiness;
- PlataVM release/fabrication/physical/population barriers remain unchanged;
- BuoyCalc release remains not ready and not authorized;
- BuoyCalc manual Windows RC smoke is not invented;
- BuoyCalc physics and PR #628 remain unchanged;
- BuoyCalc operational handoff remains unauthorized.

Opening deterministic pass marker:

`PASS_GATE035_OPENING_CONTRACT`

This marker is **not** the final Gate 035 acceptance marker.

## Real pilot still required

Final Gate 035 acceptance requires real local execution against the connected
project checkouts with exact repository identity captured at execution time.

Expected project-level dispositions for the audited starting point:

```text
PlataVM:
CONTROLLED_USE_PASS / PRODUCT_STATE_BLOCKED_NATIVE_EVIDENCE

BuoyCalc:
CONTROLLED_USE_PASS / PRODUCT_RELEASE_NOT_READY
```

Any changed connected-project head must be reconciled explicitly before the
real pilot; the opening harness must not silently treat a stale SHA as current.

## Authority

No new model/tool/Git/network authority is granted.

No connected-project commit, push, PR mutation, merge, release, fabrication,
production or physical-validation action is allowed by Gate 035 opening.

Core runtime under `src/engineering_ai/...` remains unchanged.

Ready for Review:
`NOT_AUTHORIZED`

Merge:
`NOT_AUTHORIZED`

Release:
`NOT_GRANTED`

Fabrication:
`NOT_GRANTED`

Physical validation:
`PHYSICAL_NOT_EXECUTED`
