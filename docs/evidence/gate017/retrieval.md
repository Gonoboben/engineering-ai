# Gate 017 — Retrieval Layer Evidence

## Scope

Gate 017 adds a policy-controlled retrieval layer over the accepted Gate 016
decision/evidence memory.

The initial backend is deterministic lexical retrieval.

Semantic/vector retrieval is not implemented unless a separately qualified
backend is benchmarked against simpler repository/search approaches and shown
to improve relevant engineering recall without hiding provenance.

Current semantic/vector state:
`DEFERRED_NOT_JUSTIFIED`.

## Accepted base

Engineering AI base:
Gate 016 squash merge
`a71c084078ae7c12361555eaed2f3d7c887d61d6`.

Gate 016 ADR:
`ADR-0015 — Use append-only local SQLite decision/evidence memory`
is accepted through Gate 016 merge.

## Retrieval contract

Implementation:
`src/engineering_ai/memory/retrieval.py`.

A RetrievalRequest requires:
- project_id;
- non-empty lexical query;
- bounded candidate limit 1..100;
- bounded result count;
- bounded context character budget.

Optional exact filters:
- memory kind;
- authority;
- validation class.

Default safety policy:
- latest revisions only;
- MODEL authority excluded;
- ADVISORY validation class excluded;
- PROPOSED ADRs excluded.

Explicit opt-in exists for:
- advisory memory;
- proposed ADRs;
- historical/superseded revisions.

Opt-in does not change labels or authority.

## Relevance semantics

Ranking is deterministic lexical relevance only.

Fields used:
- title;
- summary;
- structured content.

Scoring includes:
- exact phrase matches with field-specific weights;
- token matches with field-specific weights;
- all-query-token bonus.

Stable tie-break:
1. descending relevance score;
2. memory_id;
3. descending revision;
4. record_id.

Retrieval rank is not evidence strength.

## Context package

Each returned item preserves:
- record_id;
- memory_id;
- revision;
- kind;
- authority;
- validation class;
- ADR decision status;
- physical validation state;
- title/summary/content;
- provenance;
- evidence refs;
- source refs;
- canonical content SHA-256;
- relevance score/matched terms;
- current-vs-historical revision flag.

Individual records are never truncated to fit the context budget.
A whole record is omitted if it would exceed the remaining budget.

The package explicitly records:
- candidate count;
- relevant count;
- result-limit omissions;
- context-budget omissions;
- total serialized characters;
- advisory/proposed/history opt-in flags;
- semantic/vector backend status;
- `automatic_context_injection=false`.

## Trust boundaries

Default retrieval cannot silently expose model/advisory memory.

Proposed ADRs cannot appear in default context.

Historical superseded revisions cannot appear in default context.

Project_id is mandatory; cross-project memory cannot satisfy retrieval.

A memory integrity/hash failure propagates as a hard failure; corrupted memory
is not returned.

The retriever exposes no:
- append/update/delete;
- generic SQL;
- Blackboard write;
- evidence promotion;
- automatic context injection;
- semantic search;
- vector search.

## JSON Schema

`schemas/retrieval-context.schema.json`
fixes the typed context package contract.

It currently requires:
- `semantic_vector_backend=DEFERRED_NOT_JUSTIFIED`;
- `automatic_context_injection=false`.

## Deterministic benchmark

Benchmark implementation:
- `src/engineering_ai/memory/benchmark.py`;
- `scripts/gate017_retrieval_benchmark.py`.

Baseline:
Gate 016 exact-substring memory search under the same default safety filters.

Gate 017 candidate:
deterministic lexical ranked retrieval.

Metric:
recall@3 over fixed engineering-memory queries.

Fixture includes:
- non-contiguous/reordered append-only SQLite memory query;
- reordered Windows worktree cleanup query;
- selected-shape validation query with an intervening term;
- contiguous buoy-engineering source query where baseline should already work;
- advisory model-memory safety query;
- proposed-ADR safety query.

Acceptance benchmark requires:
- safety PASS;
- Gate 017 not worse on every relevant case;
- at least one improved relevant case;
- aggregate mean recall@3 greater than baseline.

No semantic/vector result may be inferred from this lexical benchmark.

## Proposed architecture decision

`ADR-0016 — Use deterministic provenance-preserving retrieval as the baseline`

Status:
`PROPOSED_GATE_017`.

It becomes accepted only after explicit human exact-SHA approval and Gate 017
squash merge.

## Physical validation

Retrieval never changes validation class.

Project physical validation remains whatever the source record states.

Gate 017 itself:
`PHYSICAL_NOT_EXECUTED`.

## Pending validation

- draft PR;
- deterministic regression;
- generic CI;
- strict exact-head CI;
- benchmark metrics;
- primary-workstation retrieval benchmark/smoke;
- final acceptance-state CI;
- final scope review;
- exact-SHA human squash-merge approval.
