# Gate 005 Evidence — qwen3.6:27b-q4_K_M / medium / 2048

## Environment
- Runtime: Ollama `0.34.1`
- Model: `qwen3.6:27b-q4_K_M`
- Digest: `3a40c32f1450b8380412898385b0e00df5d6d2d801dd192ca1acb7e735cd050e`
- Family reported by Ollama: `qwen35`
- Parameters: `27.8B`
- Quantization: `Q4_K_M`
- Context: `8192`
- Max output tokens: `2048`
- Reasoning effort: `medium`

## Machine-scored result
- `dc-load`: PASS
- `divider`: PASS
- `validation-semantics`: INCONCLUSIVE_TRUNCATED (`done_reason=length`)
- `tool-proposal`: PASS
- Total complete PASS: `3/4`
- Deterministic FAIL: `0`
- Unscored/inconclusive: `1`
- Benchmark exit code: `3`

## Per-case timing / generation
- `dc-load`: 608.93 s (~10.15 min), eval_count 1448, done_reason `stop`, ~2.46 eval tok/s
- `divider`: 792.26 s (~13.20 min), eval_count 1939, done_reason `stop`, ~2.45 eval tok/s
- `validation-semantics`: 824.79 s (~13.75 min), eval_count 2048, done_reason `length`, ~2.49 eval tok/s
- `tool-proposal`: 36.44 s, eval_count 89, done_reason `stop`, ~2.55 eval tok/s
- Aggregate wall time across cases: ~2262.42 s (~37.71 min)

## Runtime resource evidence
Ollama-reported loaded model state during benchmark:
- Model size: `17,436,319,412` bytes (~17 GB)
- Processor split: `69% CPU / 31% GPU`
- Context: `8192`
- Runtime-reported model VRAM allocation: `5,354,133,912` bytes

Observed workstation samples during active benchmark:
- VRAM used: ~`7616–7632 MiB / 8192 MiB`
- GPU utilization samples: `3%`, `6%`, `7%`, `13%`
- CPU load samples: `42%`, `54%`, `56%`, `61%`
- Free system RAM during run: ~`12.79–13.43 GB`

Post-run sample:
- VRAM used: `7575 MiB / 8192 MiB`
- GPU utilization: `0%`
- GPU memory utilization: `17%`
- CPU load: `21%`
- Free system RAM: `13.74 GB`

## Interpretation
The candidate is stable in memory at the 8K baseline and does not show OOM or memory-thrashing behavior. However, the workload is CPU-heavy (`69% CPU / 31% GPU`) and generation speed is only about `2.45–2.55 tokens/s` on the primary workstation.

The benchmark therefore demonstrates that `qwen3.6:27b-q4_K_M` is operationally loadable but impractically slow for the primary interactive Engineering AI role on the current RTX 3060 Ti 8 GB / i7-11700K workstation. One structured validation case also exhausted the full 2048-token budget at `medium` reasoning without final content, so the benchmark is not a complete 4/4 PASS.

This is benchmark evidence, not physical validation. No project action authority is granted by this result.
