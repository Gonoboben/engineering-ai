# Gate 005 — Local Model Benchmark Plan

## Purpose
Select the first local engineering model from measured workstation evidence rather than public benchmark claims alone.

The selected model is advisory. It never owns permissions, project state, or tool execution authority.

## Workstation envelope
- Windows 11 Pro build `10.0.22000` (tracked platform risk)
- Intel Core i7-11700K
- 31.9 GB RAM
- NVIDIA GeForce RTX 3060 Ti, 8192 MiB VRAM
- Python 3.12.10

## Initial runtime
Gate 005 uses Ollama as the first runtime implementation behind the replaceable `ModelProvider` interface.

Reasons:
- native Windows support;
- local API on loopback;
- NVIDIA GPU acceleration;
- structured outputs/JSON schema;
- tool/function-call transport;
- usage metrics (`prompt_eval_count`, `eval_count`, durations);
- OpenAI-compatible API exists for future adapters;
- runtime resource observations are available through `ollama ps` / `/api/ps`.

Ollama is not an architecture dependency. A later provider may use llama.cpp or another local runtime without changing Supervisor semantics.

## Network boundary
Gate 005 provider accepts only:
- `localhost`
- `127.0.0.1`
- `::1`

No LAN/public runtime endpoint is admissible in this Gate.

## Initial candidates
Registry observations captured 2026-09-16:

### Candidate A — `gpt-oss:20b`
- Ollama package size: approximately 14 GB
- 20.9B parameters, MXFP4 in current Ollama registry
- 128K advertised model context
- tools/thinking support
- current Ollama documentation identifies it as a strong general-purpose local model

### Candidate B — `qwen3.6:27b`
- Ollama package size: approximately 18 GB
- Q4_K_M current registry build
- 256K advertised model context
- text/image, tools, thinking category
- recent Qwen3.6 family prioritizes agentic coding and iterative development

### Stretch candidate — `qwen3.6:35b`
- Ollama package size: approximately 23 GB
- Q4_K_M current registry build
- 256K advertised model context
- not downloaded initially because 23 GB weights leave limited system-RAM headroom on a 32 GB Windows host once runtime/context/OS memory are included

The stretch candidate is tested only if the first two measurements show sufficient memory margin and a reason to expect a material quality gain.

## Context policy for first benchmark
Use `8192` tokens for the first comparison.

Reason:
- the workstation has 8 GiB VRAM and 32 GB system RAM;
- Ollama documents increasing memory use with context length;
- the purpose of the first Gate 005 run is provider/model selection, not maximum-context validation.

Longer context is a separate measured step after a stable candidate is selected.

## Runtime settings for the first comparison
- one loaded model at a time;
- one request at a time;
- temperature `0` for machine-scored cases;
- seed `42` where supported;
- context `8192`;
- output cap `512` tokens per synthetic case;
- model kept loaded only during a benchmark sequence;
- no cloud model usage;
- no Ollama web-search tool;
- no model-proposed tool is executed by the benchmark harness.

## Synthetic benchmark v1
The command is:

```powershell
python scripts/benchmark_local_model.py --model <model> [--reasoning high]
```

Machine-scored cases:
1. `dc-load` — 48 V / 12 ohm: expected 4 A and 192 W in schema-constrained JSON.
2. `divider` — unloaded 24 V divider, 10 kOhm / 5 kOhm: expected 8 V.
3. `validation-semantics` — simulation+CI PASS with no physical test must yield `PHYSICAL_NOT_EXECUTED`.
4. `tool-proposal` — unknown repository state must produce an inert `read_repository(path=STATUS.md)` proposal instead of fabricated file contents.

A model must pass all four machine-scored cases before it can be considered for primary use.

## Measurements recorded per case
- provider/runtime version;
- exact model name;
- configured context and generation settings (benchmark envelope);
- wall-clock elapsed time;
- prompt token count/duration when available;
- output token count/duration when available;
- derived output tokens/s when available;
- runtime `/api/ps` snapshot including model size, VRAM allocation, quantization and allocated context where reported;
- raw final content;
- separate thinking field where the runtime/model exposes it;
- proposed tool calls;
- machine score and explanation.

## Selection policy
Quality outranks speed, but a model is inadmissible if it causes unstable memory pressure, repeated runtime failure, invalid structured output, or unreliable tool-call transport.

The initial primary model is selected using the local evidence package. Public benchmark claims are background only.

## Source references used for runtime/candidate discovery
- https://ollama.com/download/windows
- https://docs.ollama.com/api/chat
- https://docs.ollama.com/capabilities/structured-outputs
- https://docs.ollama.com/api/openai-compatibility
- https://docs.ollama.com/context-length
- https://docs.ollama.com/faq
- https://ollama.com/library/gpt-oss
- https://ollama.com/library/qwen3.6

These URLs are discovery references, not proof of local performance. Local benchmark evidence remains authoritative for Gate 005 selection.
