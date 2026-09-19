# Gate 010 — Task Blackboard and Supervised Handoffs Evidence

## Scope

Gate 010 implements the runtime Task Blackboard and Supervisor-mediated handoff
records accepted in Gate 007, consuming the deterministic routing accepted in
Gate 009.

Physical validation:
PHYSICAL_NOT_EXECUTED.

## Authority model

- Blackboard is the only shared inter-worker communication surface.
- Workers receive read-only BlackboardView objects.
- Control records and handoffs are Supervisor-created.
- Model claims and model tool proposals are ADVISORY only.
- A model-authored record cannot be promoted to deterministic evidence.
- Deterministic evidence requires deterministic-tool authority and explicit
  evidence references.
- Blackboard writes do not execute tools.
- Handoff creation does not invoke a model.
- Direct worker-to-worker writes are not supported.

## Context resolution precedence

1. CONTEXT_READY
   - required deterministic context is already recorded.

2. DETERMINISTIC_ACQUISITION
   - required context is explicit but missing;
   - no model route is needed to decide what to fetch.

3. TOOL_PLANNER
   - required context is not explicit;
   - deterministic router selects GENERAL_PLANNING;
   - accepted route is qwen3.5:9b;
   - native tool proposal capability is required.

4. DEEP_ESCALATION
   - acquisition/tool choice is explicitly marked ambiguous;
   - deterministic router selects BASELINE_REASONING;
   - accepted route is gpt-oss:20b / medium.

Qwen2.5-Coder does not perform native tool planning.

## Handoff visibility

A handoff carries an explicit tuple of visible Blackboard record IDs.

Required context is considered supplied only when deterministic evidence
providing those context keys is included in that visible set.

Evidence that exists elsewhere on the Blackboard but is not visible to the
handoff does not satisfy the target worker's context requirement.

Records from another task cannot satisfy the requirement.

## Coder handoff contract

CODE_REPOSITORY -> qwen2.5-coder:7b-instruct only when:
- the Gate 009 route matches;
- native model tool proposal is not required;
- every required context key is backed by deterministic evidence;
- those evidence records are explicitly visible to the handoff.

Otherwise the handoff is not created.

## Gate 010 non-goals

Not implemented:
- independent disagreement review;
- majority voting;
- persistent long-term memory/RAG;
- unattended queue;
- Electronics/PCB/KiCad/Vision roles;
- project adapters;
- project write authority;
- external bridge;
- new model qualification.

## Deterministic validation

Pending Gate 010 regression and exact-head CI.
