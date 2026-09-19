# Engineering AI

Local-first autonomous/semi-autonomous engineering AI supervisor and agent platform.

## Purpose
Engineering AI is the control plane for safe long-running engineering work. It coordinates replaceable AI models with deterministic tools, project-specific policy, persistent state, evidence, validation, and audit.

The first real integration targets are existing engineering projects such as PlataVM and BuoyCalc. Those projects remain independent repositories; Engineering AI connects to them through controlled project profiles/adapters.

## Core design
- repository/project state is authoritative, not model/chat memory;
- offline-first operation;
- replaceable local/external model interfaces;
- deterministic non-LLM Supervisor for permissions and state transitions;
- deterministic engineering validators outrank model claims;
- explicit separation of simulation and physical validation;
- evidence/provenance and audit for material actions;
- validated single-agent reliability as the foundation for Supervisor-mediated multi-model specialization;
- models communicate through controlled task hand-offs rather than unrestricted peer-to-peer messaging.

## Current state
Gate 006 established the validated Planner / Executor / Reviewer control loop. Gate 007 is defining the supervised multi-model architecture that will qualify and route specialized local models without changing Supervisor authority. See:
- `AGENTS.md` — global governance and stop conditions;
- `ARCHITECTURE.md` — system architecture;
- `ROADMAP.md` — staged implementation plan;
- `STATUS.md` — current state;
- `DECISIONS.md` — architectural decisions;
- `CHRONOLOGY.md` — project chronology.

Current accepted local baseline: `gpt-oss:20b / medium / 8192` through loopback-only Ollama. Qwen3.5-9B and Qwen2.5-Coder-7B are planned qualification candidates, not yet accepted production roles. Connected engineering projects remain `NOT_CONNECTED` until their dedicated Gates.
