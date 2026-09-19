# Gate 008 — Local Specialist Model Qualification Plan

## Purpose

Qualify the first two specialist-model candidates for the Gate 007 supervised multi-model architecture using measured evidence from the primary workstation.

This Gate does NOT qualify Electronics/PCB/KiCad capability.

## Accepted architecture baseline

Gate 007 squash merge: 3903672d44f6ac5119183eb58363847d42e25d9b

The deterministic Supervisor remains the sole authority for permissions, state transitions, tool execution decisions, approvals, evidence promotion, and final job state. Model output remains advisory.

## Primary workstation

- Windows 11 Pro
- Intel Core i7-11700K
- 31.9 GB RAM
- NVIDIA GeForce RTX 3060 Ti, 8192 MiB VRAM
- Ollama 0.34.1
- local endpoint: 127.0.0.1:11434
- model storage: C:\workspace\models\ollama

## Fixed candidates

### Candidate G — qwen3.5:9b

Official Ollama registry observation on 2026-09-19:
- package approximately 6.6 GB
- Q4_K_M
- native registry context 256K
- text + image
- tools/thinking family

Official upstream: Qwen/Qwen3.5-9B, Apache-2.0.

Gate 008 role under test: general worker / Planner-contract candidate. Vision is not tested in this Gate.

### Candidate C — qwen2.5-coder:7b-instruct

Official Ollama registry observation on 2026-09-19:
- package approximately 4.7 GB
- 7.62B parameters
- Q4_K_M
- native registry context 32K
- Apache-2.0

Gate 008 role under test: code/repository specialist candidate.

## Reference baseline

Accepted reference: gpt-oss:20b, reasoning medium, context 8192, max output 2048.

Gate 008 does not revoke or replace the accepted baseline merely because a new candidate runs faster or passes a subset of cases.

## Explicitly NOT tested

The following remain NOT_RUN_OUT_OF_SCOPE_GATE_008:
- Electronics/PCB capability
- KiCad
- schematic understanding
- ERC/DRC
- SPICE
- CAD
- vision qualification
- PlataVM/BuoyCalc project work

No Gate 008 result may be cited as evidence for those capabilities.

## Runtime comparison policy

- one model loaded at a time
- one request at a time
- loopback-only Ollama
- cloud disabled
- context 8192
- max output 2048
- temperature 0
- seed 42
- no proposed tool is executed by the benchmark

Reasoning mode is model-specific and must be recorded rather than falsely made identical across model families.

Initial runs:
- Qwen3.5-9B: structured-speed baseline with reasoning=none
- Qwen3.5-9B: optional native/default-thinking diagnostic later if needed
- Qwen2.5-Coder-7B-Instruct: reasoning argument omitted

Do not silently send medium to a model merely because the gpt-oss baseline uses medium.

## Installation

PowerShell commands:

    cd C:\workspace\repos\engineering-ai
    ollama pull qwen3.5:9b
    ollama pull qwen2.5-coder:7b-instruct
    ollama list
    ollama show qwen3.5:9b
    ollama show qwen2.5-coder:7b-instruct

Record the complete ollama show output before qualification. Do not substitute another size/tag/quantization without an explicit Gate decision.

## Environment check

    ollama --version
    ollama ps
    nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu --format=csv
    Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory

Keep the established baseline environment:
- OLLAMA_NUM_PARALLEL=1
- OLLAMA_MAX_LOADED_MODELS=1
- OLLAMA_CONTEXT_LENGTH=8192
- OLLAMA_NO_CLOUD=1

## Gate 008 benchmark v1

Script: scripts/gate008_model_qualification.py

### General / Planner suite

1. general-structured-math — deterministic arithmetic + strict JSON.
2. general-planner-contract — bounded plan with only declared read_repository.
3. general-validation-semantics — software PASS cannot become physical PASS.
4. general-tool-proposal — inert read_repository(path=STATUS.md) proposal.

Initial Qwen3.5 command:

    .\.venv\Scripts\python.exe scripts\gate008_model_qualification.py --model qwen3.5:9b --suite general --context 8192 --max-output 2048 --reasoning none --timeout 600

### Code / repository suite

1. code-clamp-repair — repair a bounded Python expression.
2. code-off-by-one-repair — repair a loop that drops the last item.
3. code-review-evidence — reject unsupported claim that tests passed.
4. code-tool-proposal — request repository evidence instead of fabricating state.

Initial Qwen2.5-Coder command:

    .\.venv\Scripts\python.exe scripts\gate008_model_qualification.py --model qwen2.5-coder:7b-instruct --suite code --context 8192 --max-output 2048 --timeout 600

## Result semantics

- PASS: complete response reached the deterministic scorer and met it
- FAIL: complete response reached the scorer and failed it
- INCONCLUSIVE: no complete scoreable response, including truncation or provider error

CLI exit codes: 0 all PASS; 2 one or more FAIL; 3 no FAIL but one or more INCONCLUSIVE.

A running model is not automatically a qualified model.

## Resource evidence

For each candidate record exact Ollama tag/metadata, local quantization, configured context/output/reasoning, wall time, prompt/eval metrics, processor placement, GPU memory, system RAM, and truncation/timeout behavior.

## Qualification states

Allowed final role states: QUALIFIED, QUALIFIED_WITH_LIMITATIONS, NOT_QUALIFIED.

Role qualification is separate for general/Planner and code/repository.

Electronics/PCB/KiCad remains NOT_RUN_OUT_OF_SCOPE_GATE_008.

## Acceptance

Gate 008 is not complete until both fixed candidates are installed and measured, deterministic regression remains PASS, resource evidence and qualification states are recorded, final generic and strict exact-head CI are PASS, and human exact-SHA squash-merge approval is given.

Physical validation remains PHYSICAL_NOT_EXECUTED.
