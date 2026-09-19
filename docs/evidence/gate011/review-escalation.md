# Gate 011 — Independent Review and Disagreement Escalation Evidence

## Scope

Gate 011 implements evidence-first disagreement resolution and bounded
independent review on top of the accepted Gate 010 Blackboard.

Physical validation:
PHYSICAL_NOT_EXECUTED.

## Resolution order

1. Deterministic evidence is authoritative for its defined scope.
2. If deterministic evidence supports or contradicts the disputed claim,
   the disagreement is resolved without any model vote.
3. If evidence is inconclusive or unavailable, an independent bounded review
   may be requested.
4. The current accepted independent reviewer route is:
   BASELINE_REASONING -> gpt-oss:20b / medium.
5. Independent review is permitted only when the originating model identity is
   different from the reviewer model identity.
6. One bounded revision is permitted.
7. A second revision request or an inconclusive review becomes
   NEEDS_HUMAN_APPROVAL.

## Model/evidence semantics

Model review remains ADVISORY.

A review record:
- is not deterministic evidence;
- cannot override failed deterministic validation;
- cannot promote a model claim to deterministic evidence;
- cannot increase validation class merely because two models agree.

RESOLVED_AFTER_REVIEW is a workflow state only. It means the independent
review found no substantive conflict between the advisory statements; it does
not promote either statement to engineering evidence.

## Reviewer independence

Accepted reviewer evidence:
- Gate 005 gpt-oss:20b / medium baseline;
- Gate 006 gpt-oss Reviewer runtime validation.

Permitted:
- qwen3.5:9b-originated claim -> gpt-oss:20b independent review;
- qwen2.5-coder:7b-instruct-originated claim -> gpt-oss:20b independent review.

Not permitted:
- gpt-oss:20b-originated claim -> gpt-oss:20b "independent" review.

When the originating claim is from gpt-oss and deterministic evidence is
insufficient, the current accepted registry has no independent reviewer.
The deterministic result is NEEDS_HUMAN_APPROVAL.

No new reviewer model is qualified in Gate 011.

## Blackboard records

Gate 011 adds typed records:
- DISAGREEMENT;
- REVIEW_FINDING;
- REVISION_REQUEST;
- HUMAN_ESCALATION.

Authority:
- DISAGREEMENT / REVISION_REQUEST / HUMAN_ESCALATION are Supervisor control records;
- REVIEW_FINDING is model-authored ADVISORY;
- deterministic evidence remains the Gate 010 DETERMINISTIC_EVIDENCE record.

## Deterministic terminal/control states

- RESOLVED_BY_EVIDENCE
- REVIEW_REQUIRED
- RESOLVED_AFTER_REVIEW
- REVISION_REQUIRED
- NEEDS_HUMAN_APPROVAL

No majority/consensus score exists.

## Explicit non-goals

Not implemented:
- majority voting;
- confidence-weighted arbitration;
- a second newly qualified reviewer model;
- Electronics/PCB/KiCad/ERC/DRC/SPICE roles;
- vision/CAD/image roles;
- project adapters/write authority;
- external review bridge;
- persistent memory/RAG;
- unattended queue.

## Validation

Pending Gate 011 deterministic regression and exact-head CI.
