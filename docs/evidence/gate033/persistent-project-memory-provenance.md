# Gate 033 — Persistent project memory with provenance acceptance

## Gate identity

- Issue: #66
- Branch: `gate-033-persistent-project-memory-provenance`
- Base: accepted Gate 032 squash merge
  `79fd557c645f9310c5729400cfe7ba5fcf61ffa0`
- Gate 032 final approved PR head:
  `a89a2c7fdb2e472dd422121695d8492a31387b80`
- State: `OPENING / NOT_ACCEPTED`

## Objective

Close the Phase 8 / v1.0 persistent-project-memory criterion by revalidating
the already accepted Gate 016 decision/evidence memory, Gate 017 retrieval
layer and Gate 018 knowledge lifecycle as one end-to-end provenance-preserving
project-memory acceptance package.

This Gate is acceptance hardening. It does not redesign or replace the accepted
memory architecture.

## Opening reconciliation

The accepted baseline already provides:

- append-only SQLite decision/evidence memory;
- persistent close/reopen behavior;
- project-scoped storage and lookup;
- exact record revision and canonical content SHA-256;
- explicit provenance, evidence refs and source refs;
- deterministic retrieval that preserves provenance and authority labels;
- latest/history semantics;
- exact lifecycle bindings to memory record identity, revision and SHA-256;
- explicit stale source/evidence revision detection;
- model-authored memory constrained to ADVISORY authority;
- human-only accepted ADR authority;
- software/deterministic evidence prohibited from synthesizing PHYSICAL PASS;
- automatic model/Blackboard context injection disabled.

The opening read-only reconciliation found no justified memory-architecture
redesign requirement. The remaining criterion is an integrated v1.0 acceptance
proof across persistence, retrieval, lifecycle provenance and project isolation.

## Acceptance package

Gate 033 must prove, as one integrated package:

1. persistent memory records survive close/reopen without identity or hash drift;
2. same memory IDs in different projects remain isolated;
3. cross-project storage/retrieval/lifecycle access fails closed;
4. retrieval after reopen preserves exact project, record, memory, revision,
   provenance, evidence/source refs and content SHA-256;
5. accepted lifecycle knowledge binds exact source/evidence revisions and hashes;
6. source/evidence revision drift produces an explicit stale assessment;
7. prior accepted/history records remain append-only and reconstructable;
8. MODEL/ADVISORY records cannot self-promote to accepted evidence;
9. automatic model/Blackboard context injection remains disabled;
10. physical-validation semantics remain unchanged;
11. full deterministic regression remains green;
12. Gate-specific acceptance passes on Ubuntu and Windows;
13. strict exact-head validation passes before ready-for-review transition.

## Explicitly out of scope

- memory architecture redesign or migration;
- semantic/vector retrieval;
- automatic memory promotion;
- automatic model/Blackboard injection;
- new model qualification;
- connected-project production work;
- project lifecycle registry implementation;
- machine-local path-resolution architecture;
- MCP transport implementation;
- new tool/Git/network authority;
- validator weakening;
- release/fabrication authorization;
- physical-validation claims.

## Authority state

- architecture change: `NOT_GRANTED`
- validator weakening: `PROHIBITED`
- release authorization: `NOT_GRANTED`
- fabrication authorization: `NOT_GRANTED`
- physical validation: `PHYSICAL_NOT_EXECUTED`

## Planned route after Gate 033

1. Gate 034 — documented model/tool failure recovery acceptance.
2. PlataVM handoff/readiness read-only audit.
3. Gate 035 — successful controlled use on PlataVM and BuoyCalc.
4. Gate 036 — practical model/runtime replaceability.
5. Final v1.0 cold-start/source-of-truth readiness audit.
