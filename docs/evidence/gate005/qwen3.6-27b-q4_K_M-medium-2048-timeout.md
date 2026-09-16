# Gate 005 evidence — qwen3.6:27b-q4_K_M / medium / 2048 — timeout diagnostic

## Evidence class
Human-executed local workstation benchmark attempt captured from the Gate 005 benchmark harness before provider-timeout preservation was implemented.

This is operational benchmark evidence only. It is not a domain failure, physical validation, or model-selection decision.

## Runtime/model identity observed
- runtime: Ollama `0.34.1`
- model: `qwen3.6:27b-q4_K_M`
- Ollama model ID prefix: `3a40c32f1450`
- reported model size: `17 GB`
- context: `8192`
- processor split while loaded: `69% CPU / 31% GPU`
- reasoning effort requested by the benchmark: `medium`
- max output tokens: `2048`
- per-request timeout used by the failed attempt: `600 s`

## Benchmark outcome
The benchmark process terminated with a provider timeout before it could serialize its JSON evidence package:

- Python exception: `ModelProviderUnavailable: Ollama request failed: timed out`
- process exit code: `1`
- no benchmark JSON file was produced by this attempt
- the exact case that exceeded the timeout cannot be recovered from the aborted run, so no case-level PASS/FAIL claim is made
- aggregate state: `INCONCLUSIVE_TIMEOUT`

The timeout is not classified as an engineering-answer failure. It demonstrates that at least one request did not complete within the 600-second per-request envelope on this workstation.

## Resource samples while the model was loaded
All samples reported context `8192` and processor split `69% CPU / 31% GPU`.

### Sample 1
- NVIDIA VRAM used: `7635 MiB / 8192 MiB`
- GPU utilization: `3%`
- GPU memory utilization: `1%`
- total RAM: `31.9 GB`
- free RAM: `12.79 GB`

### Sample 2
- NVIDIA VRAM used: `7634 MiB / 8192 MiB`
- GPU utilization: `15%`
- GPU memory utilization: `2%`
- free RAM: `12.93 GB`

### Sample 3
- NVIDIA VRAM used: `7634 MiB / 8192 MiB`
- GPU utilization: `11%`
- GPU memory utilization: `2%`
- free RAM: `13.14 GB`

### Sample 4
- NVIDIA VRAM used: `7611 MiB / 8192 MiB`
- GPU utilization: `20%`
- GPU memory utilization: `22%`
- free RAM: `13.43 GB`

### Post-run / idle sample
- NVIDIA VRAM used: `7604 MiB / 8192 MiB`
- GPU utilization: `0%`
- GPU memory utilization: `17%`
- free RAM: `13.74 GB`

## Resource interpretation
The model is loadable at the fixed 8K context on the primary workstation without exhausting system RAM or VRAM. Compared with `gpt-oss:20b`, more weights are CPU-resident (`69% CPU / 31% GPU` versus `57% CPU / 43% GPU` for the measured GPT-OSS baseline), and system RAM headroom is lower.

The observed timeout therefore cannot be attributed to an observed out-of-memory condition. The evidence is consistent with a substantially slower CPU-heavy inference path, but exact token throughput is unavailable because the request did not complete.

## Harness correction triggered by this attempt
Gate 005 was updated so provider errors/timeouts are serialized as `passed=null`, `done_reason=provider_error`, with the error recorded in `score_note`, rather than aborting the entire benchmark process before JSON evidence is emitted.

## Next diagnostic
Repeat the unchanged 8K / 2048 / medium benchmark with the corrected harness and a larger explicit per-request timeout. Do not change the questions or deterministic scoring criteria for the comparison run.
