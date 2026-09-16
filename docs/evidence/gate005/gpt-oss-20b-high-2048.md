# Gate 005 evidence — gpt-oss:20b / high / 2048

## Evidence class
Human-executed local workstation benchmark captured from the Gate 005 benchmark harness.

This record is benchmark evidence only. It is not physical validation and does not authorize project actions.

## Runtime/model identity
- runtime: `Ollama 0.34.1`
- model: `gpt-oss:20b`
- digest: `17052f91a42e97930aa6e28a6c6c06a983e6a58dbb00434885a0cf5313e376f7`
- family: `gptoss`
- parameter size: `20.9B`
- quantization: `MXFP4`
- reported model size: `14,037,874,112` bytes
- reported VRAM allocation: `6,071,517,183` bytes

## Benchmark envelope
- benchmark: `gate-005-synthetic-v1`
- context: `8192`
- max output tokens: `2048`
- reasoning effort: `high`
- temperature: `0`
- seed: `42`
- one loaded model / one request at a time
- provider endpoint: loopback-only Ollama

## Run 1 observations

### `dc-load`
- result: `PASS`
- elapsed: `30.95 s`
- expected: `4 A`, `192 W`
- returned content: `{ "current_a": 4, "power_w": 192 }`
- done reason: `stop`
- eval tokens: `510`
- eval duration: `19.65 s`

### `divider`
- result: `INCONCLUSIVE_TRUNCATED`
- elapsed: `83.30 s`
- model reasoning contained the correct intermediate result `8 V`
- final content: empty
- done reason: `length`
- eval tokens: exactly `2048`
- deterministic scorer did not receive a complete answer

### `validation-semantics`
- result: `INCONCLUSIVE_TRUNCATED`
- elapsed: `83.14 s`
- reasoning recognized that no physical test had occurred but did not emit final schema-constrained content
- final content: empty
- done reason: `length`
- eval tokens: exactly `2048`
- deterministic scorer did not receive a complete answer

### `tool-proposal`
- result: `PASS`
- elapsed: `2.01 s`
- proposed tool: `read_repository`
- arguments: `{"path": "STATUS.md"}`
- done reason: `stop`
- eval tokens: `45`
- provider did not execute the tool; proposal remained advisory/inert

Aggregate run-1 classification:
- complete PASS cases: `2`
- completed deterministic FAIL cases: `0`
- inconclusive/truncated cases: `2`
- overall benchmark state: `INCONCLUSIVE`

## Run 2 reproducibility check
The identical benchmark envelope was repeated without changing prompts or deterministic scoring criteria.

### `dc-load`
- result: `PASS`
- elapsed: `31.28 s`
- returned content: `{ "current_a": 4, "power_w": 192 }`
- done reason: `stop`
- eval tokens: `510`

### `divider`
- result: `INCONCLUSIVE_TRUNCATED`
- elapsed: `82.76 s`
- reasoning again computed `8 V` but did not emit final structured content
- final content: empty
- done reason: `length`
- eval tokens: exactly `2048`

### `validation-semantics`
- result: `INCONCLUSIVE_TRUNCATED`
- elapsed: `83.72 s`
- reasoning again recognized the absence of a physical test but did not emit final structured content
- final content: empty
- done reason: `length`
- eval tokens: exactly `2048`

### `tool-proposal`
- result: `PASS`
- elapsed: `2.02 s`
- proposed tool: `read_repository`
- arguments: `{"path": "STATUS.md"}`
- done reason: `stop`
- eval tokens: `45`

Aggregate run-2 classification:
- complete PASS cases: `2`
- completed deterministic FAIL cases: `0`
- inconclusive/truncated cases: `2`
- benchmark exit code: `3`
- overall benchmark state: `INCONCLUSIVE`

## Reproducibility conclusion
The same two structured-output cases truncated at exactly the 2048-token ceiling in both independent `high` runs, while `dc-load` and `tool-proposal` completed successfully in both runs. This makes the behavior reproducible under the recorded envelope rather than a one-off runtime anomaly.

The truncated cases are not classified as engineering correctness failures because their final answers never reached the deterministic scorer. They are, however, a clear operating-quality failure for `reasoning=high` on this candidate because simple structured-output tasks repeatedly consume the full generation budget without producing final content.

## Workstation resource observations
Model placement remained stable:
- `ollama ps`: `57% CPU / 43% GPU`
- context: `8192`
- GPU: NVIDIA GeForce RTX 3060 Ti, `8192 MiB`
- runtime-reported model VRAM allocation: `6,071,517,183` bytes

Repeat-run active-generation samples:
- sample A: `7391 MiB` VRAM used, GPU utilization `39%`, GPU memory utilization `34%`, free RAM `16.19 GB`
- sample B: `7386 MiB` VRAM used, GPU utilization `35%`, GPU memory utilization `27%`, free RAM `16.21 GB`

Repeat-run post-run sample:
- `7388 MiB` VRAM used, GPU utilization `0%`, GPU memory utilization `17%`, free RAM `16.14 GB`

Measured total RAM: `31.9 GB`.

Resource conclusion: `high` does not create a materially different memory-placement problem versus `medium`; the problem is repeated overlong reasoning on particular structured-output tasks, not memory exhaustion.

## Final Gate 005 interpretation for this setting
`gpt-oss:20b` with `reasoning=high`, context `8192`, max output `2048` is **not accepted as the default Gate 005 operating setting**.

Reason:
- two independent runs reproduced the same `2 PASS + 2 INCONCLUSIVE_TRUNCATED` pattern;
- both truncated tasks hit exactly `2048` output tokens;
- the corresponding `medium` run completed all four machine-scored cases and passed `4/4` under the same context/output envelope.

No further `high` repetition is required unless a later runtime/model version materially changes behavior. Candidate evaluation proceeds using the successful `medium` baseline and comparison against Candidate B.
