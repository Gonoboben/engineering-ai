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

- installation: PASS
- local model ID: `6488c96fa5fa`
- exact local metadata: architecture `qwen35`; parameters `9.7B`; context length `262144`; embedding length `4096`; quantization `Q4_K_M`; capabilities `completion, vision, tools, thinking`; runtime requirement `0.17.1`; license `Apache-2.0`
- general suite: `4/4 PASS`, failed `0`, unscored `0`
- benchmark runtime: Ollama `0.34.2`
- settings: context `8192`, max output `2048`, reasoning `none`
- aggregate wall time: ~`31.446 s`
- cold first case: ~`29.394 s`, including ~`8.213 s` model load and ~`20.916 s` prompt evaluation
- warm case wall times: ~`0.849 s`, `0.586 s`, `0.617 s`
- eval throughput by case: ~`57.72`, `49.55`, `46.02`, `67.02 tok/s`
- structured JSON: `PASS`
- bounded Planner contract: `PASS`
- validation semantics: `PASS`
- inert tool proposal: `PASS`, exact `read_repository(path=STATUS.md)`
- done_reason: `stop` for all four cases
- truncation/timeouts/provider errors: `0`
- runtime placement: `100% GPU`
- model VRAM allocation reported by Ollama: `5,628,493,822 bytes` (~`5.37 GiB`)
- post-run total GPU memory used: `7487 MiB`; free `538 MiB`
- post-run free physical RAM: `22,517,204 KiB` (~`21.47 GiB`)
- resource evidence: `RECORDED`
- qualification: `QUALIFIED_GENERAL_PLANNER`
- note: speed is not treated as a direct apples-to-apples replacement comparison with Gate 005 gpt-oss because this Gate uses a different case matrix and Ollama runtime `0.34.2` versus historical `0.34.1`

## Candidate C — qwen2.5-coder:7b-instruct

- installation: PASS
- local model ID: `dae161e27b0e`
- exact local metadata: architecture `qwen2`; parameters `7.6B`; context length `32768`; embedding length `3584`; quantization `Q4_K_M`; capabilities `completion, tools, insert`; license `Apache-2.0`
- code suite: NOT_RUN
- resource evidence: NOT_RECORDED
- qualification: NOT_EVALUATED

## Runtime environment captured before benchmark

- repository head: `685f1ec046f0b42b8bd8d7c533dab7e5043cb6ce`
- `OLLAMA_CONTEXT_LENGTH=8192`
- `OLLAMA_HOST=127.0.0.1:11434`
- `OLLAMA_MAX_LOADED_MODELS=1`
- `OLLAMA_MODELS=C:\workspace\models\ollama`
- `OLLAMA_NO_CLOUD=1`
- `OLLAMA_NUM_PARALLEL=1`
- `ollama ps`: empty before benchmark, expected
- existing installed models retained: `gpt-oss:20b`, `huihui_ai/qwen3-abliterated:14b-v2-q4_K_M`
- Electronics/PCB/KiCad capability remains `NOT_RUN_OUT_OF_SCOPE_GATE_008`

## Accepted reference

- gpt-oss:20b / medium / context 8192 / max output 2048
- Gate 005 accepted baseline remains unchanged

## Final acceptance

- candidate results recorded: QWEN35_GENERAL_RECORDED; QWEN25_CODER_PENDING
- resource evidence recorded: PENDING
- qualification states recorded: PENDING
- final generic CI: PENDING
- final strict exact-head CI: PENDING
- exact-SHA human merge approval: PENDING
