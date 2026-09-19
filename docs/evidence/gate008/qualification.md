# Gate 008 — Local Model Qualification Evidence

## Fixed scope

- qwen3.5:9b — general / Planner candidate
- qwen2.5-coder:7b-instruct — code/repository candidate
- gpt-oss:20b / medium — accepted reference baseline
- Electronics/PCB/KiCad/ERC/DRC/SPICE: NOT_RUN_OUT_OF_SCOPE_GATE_008
- physical validation: PHYSICAL_NOT_EXECUTED

## Preparation validation

- deterministic suite: 54/54 PASS
- generic CI: PASS
- strict exact-head CI: PASS
- benchmark script: scripts/gate008_model_qualification.py
- procedure: docs/GATE008_MODEL_QUALIFICATION.md

## Candidate G — qwen3.5:9b

- installation: NOT_RUN
- exact local metadata: NOT_RECORDED
- general suite: NOT_RUN
- resource evidence: NOT_RECORDED
- qualification: NOT_EVALUATED

## Candidate C — qwen2.5-coder:7b-instruct

- installation: NOT_RUN
- exact local metadata: NOT_RECORDED
- code suite: NOT_RUN
- resource evidence: NOT_RECORDED
- qualification: NOT_EVALUATED

## Accepted reference

- gpt-oss:20b / medium / context 8192 / max output 2048
- Gate 005 accepted baseline remains unchanged

## Final acceptance

- candidate results recorded: PENDING
- resource evidence recorded: PENDING
- qualification states recorded: PENDING
- final generic CI: PENDING
- final strict exact-head CI: PENDING
- exact-SHA human merge approval: PENDING
