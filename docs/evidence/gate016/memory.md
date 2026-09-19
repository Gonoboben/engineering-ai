# Gate 016 — Decision/Evidence Memory Evidence

## Scope

Gate 016 implements local persistent engineering memory for:
- ADRs / engineering decisions;
- calculations;
- deterministic/software test results;
- failure lessons;
- source references.

The implementation uses SQLite from the Python standard library.

Gate 016 does not implement semantic/vector retrieval, RAG, automatic model
context injection, cloud memory or model-managed truth.

Physical validation remains:
`PHYSICAL_NOT_EXECUTED`
unless an individual memory record represents genuine physical evidence with
its own explicit provenance/evidence reference and PHYSICAL validation class.

## Accepted base

Engineering AI base:
Gate 015 squash merge
`496896ebb368618cbd9f3c6f26e31fae4acb8922`.

## Storage model

Implementation:
`src/engineering_ai/memory/store.py`.

Database schema version:
`1.0`.

SQLite tables:
- `memory_meta`;
- `memory_records`.

Historical records are append-only.

SQLite triggers reject:
- `UPDATE memory_records`;
- `DELETE FROM memory_records`.

The public memory adapter intentionally exposes no generic SQL, update or
delete API.

## Record identity and revision

Each record carries:
- unique `record_id`;
- project-scoped stable `memory_id`;
- positive revision;
- exact optional `supersedes_record_id`.

When a memory_id already exists, a new revision must reference the exact latest
record. Stale/forked supersession is rejected.

This preserves a single deterministic revision chain rather than silently
branching or rewriting history.

## Integrity

Every record stores SHA-256 over canonical JSON containing:
- schema version;
- record identity/project/memory/revision;
- kind/authority/validation class;
- title/summary/content;
- provenance/evidence/source refs;
- decision/physical state;
- supersession link;
- UTC timestamp.

Every record read recomputes and compares this hash.

Malformed JSON/enum state or a hash mismatch raises a deterministic integrity
error. Corrupted records are never silently returned.

## Memory kinds

- `ADR`;
- `CALCULATION`;
- `TEST_RESULT`;
- `FAILURE_LESSON`;
- `SOURCE_REFERENCE`.

## Authority classes

- `HUMAN`;
- `SUPERVISOR`;
- `MODEL`;
- `DETERMINISTIC_TOOL`;
- `IMPORTED_SOURCE`.

## Validation classes

- `CONTROL`;
- `ADVISORY`;
- `SOURCE`;
- `CALCULATION`;
- `SIMULATION`;
- `DETERMINISTIC_TEST`;
- `PHYSICAL`.

Trust boundaries:
- MODEL authority can only be ADVISORY;
- ACCEPTED ADR requires HUMAN authority and CONTROL class;
- SOURCE_REFERENCE requires SOURCE class and explicit source_refs;
- DETERMINISTIC_TEST requires evidence_refs and non-model authority;
- PHYSICAL requires HUMAN/DETERMINISTIC_TOOL authority, evidence_refs and
  explicit PHYSICAL_PASS/PHYSICAL_FAIL;
- non-PHYSICAL records cannot carry PHYSICAL_PASS/PHYSICAL_FAIL.

Thus software/calculation/model records cannot synthesize physical evidence.

## Search

Gate 016 search is deterministic and bounded.

Supported:
- project_id;
- exact record-kind filter;
- exact authority filter;
- exact validation-class filter;
- case-insensitive keyword matching over title/summary/content;
- latest-only or full history;
- result limit 1..100;
- bounded candidate scan.

Project_id is mandatory for get/latest/history/search so another project's
memory cannot satisfy the request.

No embedding/vector/semantic search exists in Gate 016.

## JSON Schema

`schemas/memory-record.schema.json`
mirrors the record and trust-boundary semantics.

## Proposed architecture decision

`ADR-0015 — Use append-only local SQLite decision/evidence memory`

Status:
`PROPOSED_GATE_016`.

It must not be considered accepted until Gate 016 receives explicit exact-SHA
human approval and is merged.

## Validation

Pending:
- deterministic regression;
- generic CI;
- strict exact-head CI;
- local persistent/reopen memory smoke.

## Remaining acceptance

1. open Gate 016 draft PR;
2. deterministic regression PASS;
3. generic + strict exact-head CI PASS;
4. local persistent/reopen smoke PASS;
5. final acceptance-state CI;
6. final scope review;
7. exact-SHA human squash-merge approval.
