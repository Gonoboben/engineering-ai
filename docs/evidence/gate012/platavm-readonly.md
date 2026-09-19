# Gate 012 — PlataVM Read-Only Adapter Evidence

## Scope

Gate 012 connects the existing `Gonoboben/plataVM` project to Engineering AI in
strict read-only mode.

No PlataVM file, Git ref, PR state, CI run, architecture, validator, fabrication
state, physical state, population state, or release state is modified by this Gate.

Physical validation remains:
`PHYSICAL_NOT_EXECUTED`.

## PlataVM authority order resolved

Mandatory governance files are resolved in the exact order required by
`plataVM/AGENTS.md`:

1. `AGENTS.md`
2. `Docs/PROJECT_STATUS.md`
3. `Docs/PROJECT_CONTROL.md`
4. `Docs/PROJECT_MASTER.md`
5. `Docs/ARCHITECTURE_BASELINE.md`
6. `Docs/OPEN_QUESTIONS.md`
7. `Docs/TRACEABILITY_V1_9.md`
8. `Docs/CHRONOLOGY.md`
9. latest direct entry under `Docs/chronology/`

A missing mandatory file or empty chronology directory is a hard adapter error.

## Read-only implementation

Adapter:
`src/engineering_ai/projects/platavm.py`

Profile:
`profiles/platavm-readonly.json`

Policy:
`profiles/platavm-readonly-policy.json`

Autonomous Gate 012 actions:
- `read_repository`
- `run_validator`

Forbidden in the Gate 012 policy include:
- project patch/write;
- local commit;
- push;
- PR open/merge;
- architecture/physics changes;
- validator weakening;
- fabrication/release authorization;
- destructive action;
- scope expansion.

The adapter exposes no public write/delete/Git-mutation/generic-process API.

## Git snapshot semantics

The adapter records:
- checked-out branch;
- exact HEAD;
- `origin/main` SHA when available;
- porcelain status;
- dirty/clean state.

A safe read-only `GitReadOnlyAdapter.ref_sha()` operation was added to resolve
fixed safe Git refs without exposing a generic Git command surface.

## Governance conflict semantics

`Docs/PROJECT_STATUS.md` is compared against actual Git state.

Detected mismatch is returned as a conflict record. It is never silently
reconciled and does not cause the model to choose one source as authoritative
without surfacing the discrepancy.

At Gate 012 opening, GitHub evidence showed the PlataVM dynamic status document
was older than current repository activity:

- `Docs/PROJECT_STATUS.md` date: 2026-09-11;
- declared confirmed base main: `c9703c58486eb5efe6a1d1d3e1bbf37815cd2a65`;
- declared active branch: `agent/post-pr96-status-roadmap-v1-9`;
- PR #98 later merged to main at
  `dcba77466d4800c0e7a336a2771684e066f845db`;
- current open PR #100 branch:
  `agent/pcb-e-aux-hardware-current-v1-9`.

Therefore stale governance must be reported as source conflict, not silently
treated as current Git state.

## Current PlataVM PR #100 remote evidence

Observed at Gate 012 opening:

- PR: `#100`;
- state: `OPEN`;
- draft: `true`;
- base: `main@dcba77466d4800c0e7a336a2771684e066f845db`;
- head: `11e746cfea7f9200415cf817b6cde928b6a2651a`.

Post-push workflow evidence on that exact head:

- PlataVM repository integrity:
  run `35105701408`,
  job `104826210901`,
  status `completed`,
  conclusion `cancelled`;
- PlataVM KiCad 10 hierarchy:
  run `35105701440`,
  job `104826214812`,
  status `completed`,
  conclusion `cancelled`.

Gate 012 classification:
`CANCELLED / CANCELLED`.

This is explicitly non-PASS evidence. It is not classified as engineering FAIL
either; the exact-head validation remains incomplete.

No rerun was requested by Gate 012.

## Preserved PlataVM barriers

The adapter and Gate 012 preserve:

- `PACKAGE_SET_NOT_READY`;
- prototype fabrication `NOT_GRANTED`;
- physical `NOT_EXECUTED`;
- population `PROTOTYPE_BASIS_ONLY_NOT_RELEASED / UNDECIDED`;
- series production `NOT_GRANTED`.

No fabrication/readiness/physical conclusion is inferred from software or CI.

## KiCad inventory

The adapter scans only the root-bounded `Hardware/KiCad` subtree.

Recognized assets are bounded and include:
- `.kicad_pro`;
- `.kicad_sch`;
- `.kicad_pcb`;
- `.kicad_sym`;
- `.kicad_mod`;
- `.pretty` footprint directories.

Traversal has explicit count and depth limits.

## Fixed validator profiles

Only two Gate 012 validator profiles are exposed:

1. `platavm.repository_integrity`
   - Python
   - `Tools/repository_integrity.py --base-ref origin/main`

2. `platavm.semantic_gates`
   - Python
   - `Tools/run_all_gates.py`

Execution uses the accepted allow-listed process runner with `shell=False`.

Before/after Git HEAD and porcelain status are compared. If a validator changes
Git-visible repository state, Gate 012 raises an adapter error instead of
accepting the validator result.

## CI-state preservation

The adapter provides explicit CI states:

- `PASS`
- `FAIL`
- `CANCELLED`
- `IN_PROGRESS`
- `NOT_RUN`
- `UNKNOWN`

A cancelled GitHub workflow is never converted into PASS.

## Deterministic validation

Implementation head:
`53d54fe8a27fa88f0381590fcca4a80b43b276f3`

Result:
- deterministic tests: `108/108 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- exact revision verification: `PASS`.

The first CI attempt exposed a Gate 012 inventory implementation error: the
new adapter attempted to enumerate the repository root using the generic
filesystem adapter's deliberately strict relative-child boundary. The generic
security boundary was not weakened. Gate 012 was corrected to inventory only
the known `Hardware/KiCad` subtree.

## Remaining acceptance item

Local smoke on the actual primary-workstation checkout
`C:\workspace\repos\plataVM` is still `NOT_RUN`.

The smoke harness now reports `LOCAL_REPOSITORY_NOT_FOUND` as a structured state with exit code 2 instead of raising an unhandled Python traceback. After a local clone exists, the smoke must:
- capture the actual local branch/HEAD/origin-main;
- resolve mandatory governance and latest chronology;
- inventory KiCad assets;
- surface any governance/Git conflicts;
- run the two fixed read-only validators;
- verify that Git-visible state is unchanged.

No merge approval is admissible until that smoke evidence is recorded.
