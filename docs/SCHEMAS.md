# Machine-readable control-plane schemas

Gate 002 introduces six JSON Schema Draft 2020-12 records. They define control-plane data independently of any LLM runtime.

## Schemas

- `project-profile.schema.json` — project identity, repository location, authoritative files, policy reference and tool profiles.
- `project-policy.schema.json` — autonomous, approval-required and forbidden action classes plus validators, stop conditions and retry bound.
- `job.schema.json` — bounded engineering job/task scope, requested actions, validators, retry counters and lifecycle state.
- `project-state.schema.json` — explicit repository/Gate state, effective permissions, blockers, validation states and next admissible action.
- `evidence.schema.json` — engineering claim provenance and validation class, with a hard separation between simulation/calculation/test evidence and physical validation.
- `audit-event.schema.json` — reconstructable material events, before/after refs, evidence links and approval state; secret-bearing audit records are structurally rejected.

## Semantic validation

`engineering_ai.validation` adds deterministic checks that JSON Schema alone does not conveniently express:

- permission classes must be disjoint;
- architecture, physics, destructive, fabrication, release, disclosure, validator-weakening and scope-expansion boundaries may not become autonomous;
- those global boundaries must be approval-required or forbidden in project policy;
- job attempts may not exceed their retry limit.

## Validation command

From an activated project virtual environment:

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
```

The test suite validates schema syntax, positive fixtures, negative fixture rejection and package import. No LLM, network service, connected engineering project, KiCad, SPICE or CAD runtime is required.

## Validation semantics

Schema validity does not imply engineering correctness. It proves only that the record satisfies the declared structural and control-plane constraints.

In particular:

- model analysis remains advisory evidence;
- simulation/calculation/deterministic-test records cannot claim `PHYSICAL_PASS`;
- physical validation requires `physical_measurement` evidence;
- deterministic `PASS` is scoped to the named validator and recorded inputs/revision.
