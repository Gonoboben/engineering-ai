# Gate 005 Evidence — gpt-oss:20b / medium / 2048

## Environment
- Runtime: Ollama `0.34.1`
- Model: `gpt-oss:20b`
- Digest: `17052f91a42e97930aa6e28a6c6c06a983e6a58dbb00434885a0cf5313e376f7`
- Family: `gptoss`
- Parameters: `20.9B`
- Quantization: `MXFP4`
- Context: `8192`
- Max output tokens: `2048`
- Reasoning effort: `medium`

## Machine-scored result
- `dc-load`: PASS
- `divider`: PASS
- `validation-semantics`: PASS
- `tool-proposal`: PASS
- Total: `4/4 PASS`
- Benchmark exit code: `0`

## Per-case timing / generation
- `dc-load`: 17.99 s, eval_count 200, done_reason `stop`
- `divider`: 9.85 s, eval_count 250, done_reason `stop`
- `validation-semantics`: 20.30 s, eval_count 508, done_reason `stop`
- `tool-proposal`: 1.74 s, eval_count 36, done_reason `stop`

## Runtime resource evidence
Post-run model state while kept loaded by Ollama:
- Model size: ~14 GB
- Processor split: `57% CPU / 43% GPU`
- Context: `8192`
- Runtime-reported model VRAM allocation: `6071517183` bytes
- NVIDIA RTX 3060 Ti VRAM used immediately after benchmark: `7397 MiB / 8192 MiB`
- GPU utilization immediately after benchmark: `12%`
- GPU memory utilization immediately after benchmark: `11%`
- Total system RAM: `31.9 GB`
- Free system RAM immediately after benchmark: `16.01 GB`

Important measurement note: utilization percentages above are post-run steady-state measurements, not active-generation load. The CPU/GPU split, allocated context, loaded model state, VRAM allocation, and post-run memory headroom remain valid evidence. Active-generation utilization should be sampled during the benchmark in a separate shell for later candidates.

## Interpretation
`gpt-oss:20b` at `medium` is a valid Gate 005 candidate: all four machine-scored cases completed and passed under the fixed 8K/2048 envelope. This is materially better structured-output behavior than the same model at `high`, where two cases were truncated at the output-token ceiling.

This file records local workstation evidence only. It does not by itself select the final Gate 005 model; Candidate B must be tested under the same benchmark envelope before selection.
