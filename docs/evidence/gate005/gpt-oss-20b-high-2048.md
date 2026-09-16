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

## Machine-scored observations

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

This is not classified as an engineering calculation failure. The model exhausted the generation budget while repeatedly reasoning about output formatting/schema.

### `validation-semantics`
- result: `INCONCLUSIVE_TRUNCATED`
- elapsed: `83.14 s`
- reasoning recognized that no physical test had occurred but did not emit final schema-constrained content
- final content: empty
- done reason: `length`
- eval tokens: exactly `2048`
- deterministic scorer did not receive a complete answer

This is not classified as a validation-semantics failure because no complete final answer reached the scorer.

### `tool-proposal`
- result: `PASS`
- elapsed: `2.01 s`
- proposed tool: `read_repository`
- arguments: `{"path": "STATUS.md"}`
- done reason: `stop`
- eval tokens: `45`
- provider did not execute the tool; proposal remained advisory/inert

## Aggregate classification
- complete PASS cases: `2`
- completed deterministic FAIL cases: `0`
- inconclusive/truncated cases: `2`
- overall benchmark state: `INCONCLUSIVE`

The original harness version reported the truncated cases as ordinary failures. Gate 005 was corrected so `done_reason=length` is represented as `passed=null` / `INCONCLUSIVE`, with a distinct non-zero exit code.

## Workstation resource observation while model was loaded
- `ollama ps`: `57% CPU / 43% GPU`
- context: `8192`
- GPU: NVIDIA GeForce RTX 3060 Ti, `8192 MiB`
- measured GPU memory used: approximately `7401 MiB`
- measured total RAM: `31.9 GB`
- measured free RAM: `15.89 GB`

Resource conclusion: the candidate is operationally loadable on the primary workstation at the 8K baseline without exhausting system RAM. VRAM is substantially occupied, so larger candidates are expected to use a greater CPU/RAM fraction.

## Interpretation
The `high` reasoning setting is not accepted as the Gate 005 operating setting for `gpt-oss:20b` based on this run. Two simple structured-output tasks consumed the full 2048-token output budget without reaching final content.

Next diagnostic step: run the unchanged benchmark cases at `reasoning=medium`, context `8192`, max output `2048`. Do not change the questions or deterministic scoring criteria.
