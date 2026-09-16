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
- single-agent reliability before multi-agent specialization.

## Current state
The project is in its architecture/governance bootstrap phase. See:
- `AGENTS.md` — global governance and stop conditions;
- `ARCHITECTURE.md` — system architecture;
- `ROADMAP.md` — staged implementation plan;
- `STATUS.md` — current state;
- `DECISIONS.md` — architectural decisions;
- `CHRONOLOGY.md` — project chronology.

No production local model/runtime or connected-project modification is part of Gate 001.
