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

Gate 026 is accepted and establishes the canonical reproducible local
installation path on Ubuntu and Windows.

Gate 027 is implementation-validated and pending human acceptance. It makes the
offline-first boundary explicit for connected projects:
- every allow-listed process command declares `LOCAL_ONLY` or
  `NETWORK_CAPABLE`;
- offline mode blocks `NETWORK_CAPABLE` commands before process execution;
- PlataVM local read-only/controlled validator paths continue offline;
- BuoyCalc local repository/worktree paths continue offline;
- BuoyCalc package-acquisition `dotnet restore` steps fail closed with explicit
  `OFFLINE_NETWORK_REQUIRED` evidence rather than silently using the network.

Gate 027 does not claim OS-level firewall enforcement or formal network-freedom
of arbitrary project-owned script internals. A blocked network-dependent
validator is never reinterpreted as PASS.

Connected-project repositories remain authoritative for their own engineering
content.

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
