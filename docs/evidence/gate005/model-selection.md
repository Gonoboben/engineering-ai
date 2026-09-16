# Gate 005 Model Selection Decision Evidence

## Decision scope
Select the initial local engineering model for the primary workstation using measured Gate 005 evidence. This selection is runtime/model configuration only; it does not alter Supervisor authority, policy, validators, or project architecture.

## Workstation
- Windows 11 Pro
- Intel Core i7-11700K
- 31.9 GB RAM
- NVIDIA GeForce RTX 3060 Ti, 8192 MiB VRAM
- Ollama 0.34.1
- benchmark context: 8192
- max output: 2048
- temperature: 0
- seed: 42

## Candidate A — gpt-oss:20b / medium
Measured result:
- 4/4 machine-scored cases PASS
- no deterministic failures
- all cases completed with `done_reason=stop`
- aggregate case wall time: ~49.9 s
- processor split: 57% CPU / 43% GPU
- active VRAM: ~7.38 GB
- free system RAM during run: ~16.3 GB
- structured output: PASS
- validation semantics: PASS
- inert tool proposal: PASS

Additional diagnostic:
- `reasoning=high` was tested twice and reproducibly caused two structured-output cases to exhaust the 2048-token budget.
- therefore `medium` is the accepted baseline reasoning level for this model; `high` is not the default.

## Candidate B — qwen3.6:27b-q4_K_M / medium
Measured result:
- 3/4 machine-scored cases PASS
- 0 deterministic failures
- 1 case INCONCLUSIVE_TRUNCATED at 2048 tokens
- aggregate case wall time: ~2262.42 s (~37.71 min)
- generation throughput: ~2.45–2.55 eval tokens/s
- processor split: 69% CPU / 31% GPU
- active VRAM: ~7.62 GB
- free system RAM during run: ~12.8–13.4 GB
- model is memory-stable and does not show OOM/thrashing
- one earlier run also exceeded the original 600 s per-case timeout before the benchmark harness was corrected to preserve timeout evidence

## Selection
Selected initial local engineering model:

`gpt-oss:20b`

Selected baseline reasoning level:

`medium`

Baseline runtime envelope:
- Ollama 0.34.1
- context 8192
- max output 2048 for benchmark-equivalent structured tasks
- one loaded model / one request at a time
- loopback-only runtime

## Rationale
Candidate A is selected because it is the only candidate that completed all four deterministic Gate 005 cases successfully under the measured workstation envelope. It also provides materially better interactive throughput on the current hardware while maintaining adequate memory headroom.

Candidate B is not rejected as incapable: it produced three correct completed answers and remained memory-stable. It is not selected for the primary interactive role because the measured CPU-heavy inference path is operationally too slow on the current workstation and one structured-output case still exhausted the generation budget.

The deferred 35B stretch candidate is not justified on the current workstation after the 27B measurement, because the 27B candidate already shifts more model weight to CPU and is impractically slow for the primary role.

## Authority / safety
This selection does not promote model output above deterministic evidence. The model remains advisory. The Supervisor continues to own policy, permissions, state transitions, approvals, and tool execution decisions.

Physical validation remains `PHYSICAL_NOT_EXECUTED`.
