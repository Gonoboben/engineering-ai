# Engineering AI

Local-first autonomous/semi-autonomous engineering AI supervisor and agent platform.

## Purpose
Engineering AI is the control plane for safe long-running engineering work. It
coordinates replaceable AI models with deterministic tools, project-specific
policy, persistent state, evidence, validation, and audit.

Existing engineering projects such as PlataVM and BuoyCalc remain independent
repositories. Engineering AI connects to them through controlled project
profiles/adapters rather than replacing their source of truth.

## Core design
- repository/project state is authoritative, not model/chat memory;
- offline-first operation;
- replaceable local/external model interfaces;
- deterministic non-LLM Supervisor for permissions and state transitions;
- deterministic engineering validators outrank model claims;
- explicit separation of simulation and physical validation;
- evidence/provenance and audit for material actions;
- validated single-agent reliability as the foundation for
  Supervisor-mediated multi-model specialization;
- models communicate through controlled task hand-offs rather than unrestricted
  peer-to-peer messaging.

## Current state
Phase 7 capability expansion is accepted through Gate 025. Phase 8 is validating
the stable-platform / v1.0 criteria one by one.

Gate 026 adds the canonical reproducible local installation path:
- Python 3.12.x;
- exact frozen runtime and install-tool dependencies;
- fresh virtual environment;
- non-editable wheel build/install;
- installed schema/package verification;
- `pip check`;
- deterministic regression from the installed package;
- Ubuntu and Windows CI acceptance.

Gate 026 does **not** by itself establish the separate offline-continuation
criterion.

Connected-project control paths are already implemented and accepted for
PlataVM and BuoyCalc under their dedicated Gates. Their repositories remain
authoritative for their own engineering content.

## Installation
See `INSTALL.md` for the Gate 026 canonical local-install procedure.

## Project control documents
- `AGENTS.md` — global governance and stop conditions;
- `ARCHITECTURE.md` — system architecture;
- `ROADMAP.md` — staged implementation plan;
- `STATUS.md` — current state;
- `DECISIONS.md` — architectural decisions;
- `CHRONOLOGY.md` — project chronology;
- `INSTALL.md` — reproducible local installation contract.

## Model/runtime notes
The accepted baseline remains local-first and Supervisor-controlled. Model and
runtime qualification are evidence-based and replaceable; a model name or
advertised capability alone does not grant a production route or authority.

Physical validation remains separate from software, calculation, synthetic and
CI validation.
