# Gate 009 — Model Capability Registry and Deterministic Router Evidence

## Scope

Gate 009 implements only the evidence-backed model capability registry and
deterministic Supervisor-owned routing boundary accepted by Gate 007.

Out of scope:
- Task Blackboard;
- model-to-model hand-offs;
- independent disagreement review;
- Electronics/PCB/KiCad/ERC/DRC/SPICE routing;
- vision/CAD/image routing;
- project adapters;
- external control bridge;
- new model qualification;
- model/provider/tool execution inside the Router.

Physical validation remains:
PHYSICAL_NOT_EXECUTED.

## Accepted evidence inputs

### gpt-oss:20b

Evidence:
- docs/evidence/gate005/model-selection.md
- docs/evidence/gate006/runtime-smoke.md

Accepted route class:
- BASELINE_REASONING

Configuration:
- provider: ollama
- reasoning: medium
- qualified context: 8192
- qualified max output: 2048
- native tool proposals: supported in accepted evidence

This route does not claim a new specialist qualification.

### qwen3.5:9b

Evidence:
- docs/evidence/gate008/qualification.md

Accepted Gate 008 state:
QUALIFIED_GENERAL_PLANNER

Accepted route class:
- GENERAL_PLANNING

Configuration:
- provider: ollama
- reasoning: none
- qualified context: 8192
- qualified max output: 2048
- native tool proposals: supported in Gate 008 qualification

### qwen2.5-coder:7b-instruct

Evidence:
- docs/evidence/gate008/qualification.md

Accepted Gate 008 state:
QUALIFIED_WITH_LIMITATIONS_CODE_REPOSITORY

Accepted route class:
- CODE_REPOSITORY

Configuration:
- provider: ollama
- qualified context: 8192
- qualified max output: 2048
- native tool proposals: NOT qualified

Hard limitation:
NO_NATIVE_TOOL_PROPOSALS_UNDER_CURRENT_OLLAMA_CONTRACT

## Deterministic routing table

| Task class | Requirements | Result |
| --- | --- | --- |
| GENERAL_PLANNING | context <= 8192, output <= 2048 | qwen3.5:9b |
| CODE_REPOSITORY | context <= 8192, output <= 2048, native tool proposal not required | qwen2.5-coder:7b-instruct |
| CODE_REPOSITORY | native tool proposal required | NO_ROUTE |
| BASELINE_REASONING | context <= 8192, output <= 2048 | gpt-oss:20b / medium |

No fallback is inferred across specialist task classes.

For example:
- CODE_REPOSITORY + native tool proposal required does NOT automatically route
  to qwen3.5 merely because qwen3.5 supports native tool proposals;
- GENERAL_PLANNING does NOT route to qwen2.5-coder;
- no Electronics/PCB/KiCad route exists.

## Authority boundary

The Router:
- receives an explicit typed task class;
- checks only recorded capability/requirement fields;
- returns ROUTE or NO_ROUTE;
- does not classify free text;
- does not invoke Ollama;
- does not call a model;
- does not call a tool;
- does not mutate Supervisor state;
- does not change policy;
- does not promote model claims to evidence.

Supervisor owns the routing boundary through route_model().

## Deterministic validation

Pending final Gate 009 CI evidence.
