# ARCHITECTURE.md

## 1. Mission
Engineering AI is a local-first control plane for autonomous and semi-autonomous engineering work. It coordinates replaceable AI models with deterministic engineering tools while keeping project state, evidence, validation, governance, and audit outside model memory.

The initial target is reliable work on existing engineering repositories such as PlataVM and BuoyCalc. Vision, image generation, CAD-specialist workers, and multi-agent workflows are future extensions, not prerequisites for the core.

## 2. Architectural principles
1. **Repository-backed truth** — authoritative state is stored in repositories and explicit project-state records.
2. **Offline-first** — core engineering operation must continue without internet access.
3. **Replaceable models** — model providers/runtimes are adapters, not architectural dependencies.
4. **Deterministic validation** — compilers, tests, ERC/DRC, SPICE/FEM, calculation scripts and measured evidence outrank model claims.
5. **External policy enforcement** — an ordinary program, the Supervisor, controls permissions and stop conditions.
6. **Project isolation** — connected projects remain independent repositories with independent governance.
7. **Evidence before confidence** — conclusions are linked to sources, calculations, simulations, tests or measurements.
8. **Auditable autonomy** — material actions are reconstructable after the fact.
9. **Single-agent first** — reliability of one engineering agent is established before specialist/multi-agent expansion.
10. **Human authority at irreversible boundaries** — architecture, physics, fabrication, publishing, destructive actions and other policy boundaries remain human-controlled unless explicitly delegated.

## 3. System context

```text
User / External Supervisor
          |
          v
+-------------------------+
| Engineering Supervisor  |  <- deterministic control program
+------------+------------+
             |
   +---------+---------+-------------------+
   |                   |                   |
   v                   v                   v
Model Interface      Tool Bus          Project State
   |                   |                   |
   v                   v                   v
Local LLM(s)       KiCad/Python/etc.   policies/status
   |                   |                   |
   +---------+---------+-------------------+
             |
             v
     Evidence + Validation
             |
             v
        Audit / Git
```

Optional online services, including OpenAI, are external capabilities. They must not be required for basic project continuation.

## 4. Core components

### 4.1 Supervisor
The Supervisor is the control authority and is not an LLM.

Responsibilities:
- load active project profile and policy;
- load current project/Git state;
- create and track tasks/jobs;
- decide which tools/models are permitted for each step;
- enforce stop conditions and approval boundaries;
- bound retries and detect repeated failure loops;
- record tool/model calls and state transitions;
- prevent model output from directly becoming authoritative state without controlled write actions;
- require validation before marking work complete.

The Supervisor must be testable without any AI model connected.

### 4.2 Model Interface / Model Router
A stable interface abstracts model runtime/provider details.

Initial requirement: one primary local engineering model.

Future routing may select models by capability, e.g.:
- deep engineering/reasoning;
- code specialization;
- vision;
- CAD planning;
- image generation;
- independent review.

Routing must remain policy-controlled and observable.

### 4.3 Engineering Agent
The Engineering Agent uses the model interface to:
- understand tasks;
- inspect context;
- propose plans;
- call permitted tools through the Supervisor;
- analyze deterministic outputs;
- prepare changes;
- request review or human approval when required.

The agent does not own repository credentials, unrestricted shell access, or final policy decisions.

### 4.4 Reviewer
The Reviewer evaluates completed work against the original task and evidence.

In early versions, Planner/Executor/Reviewer may use the same model in separated contexts. Later, the Reviewer may use a second model.

Reviewer outcomes:
- `ACCEPT`;
- `REJECT`;
- `NEEDS_MORE_EVIDENCE`;
- `NEEDS_HUMAN_APPROVAL`.

### 4.5 Tool Bus
Tools are exposed through narrow typed adapters instead of unrestricted model-controlled execution where practical.

Planned tool families:
- Git/repository inspection and controlled writes;
- filesystem/document search;
- Python/NumPy/SciPy/SymPy;
- KiCad CLI, ERC and DRC;
- ngspice/SPICE;
- .NET/compiler/test runners;
- FreeCAD/CAD;
- FEM/other engineering solvers;
- reporting/export.

Tool results are captured as structured evidence.

### 4.6 Project Adapter
Each external engineering project supplies a profile describing:
- repository location/identity;
- authoritative governance files;
- architecture/version constraints;
- permitted tools;
- mandatory checks;
- stop conditions;
- status schema;
- project-specific terminology and validation semantics.

The adapter does not copy the project into this repository.

### 4.7 Project State
Project state is explicit and machine-readable. It records at minimum:
- project ID;
- active Gate/task;
- repository and branch/ref;
- exact HEAD when relevant;
- architecture baseline/version;
- allowed/forbidden action classes;
- pending checks;
- unresolved blockers/questions;
- current validation states;
- next admissible action.

Human-readable status documents may be generated from or cross-checked against this state.

### 4.8 Engineering Memory
Long-term memory is external to model weights and model context.

Memory classes include:
- decisions/ADRs;
- requirements;
- component/source references;
- calculations and assumptions;
- test/simulation results;
- failed approaches;
- lessons learned;
- terminology;
- chronology.

Initial implementation may use repository files and SQLite/search. Vector retrieval can be added later if justified by measured need.

### 4.9 Evidence Layer
Engineering conclusions should be represented as claims linked to evidence.

Conceptual record:
```text
claim
  -> source(s)
  -> assumptions
  -> calculation/simulation/test IDs
  -> revision/inputs
  -> validation class
  -> physical-validation state
```

No model confidence score is accepted as engineering evidence by itself.

### 4.10 Audit Log
Audit is append-oriented and reconstructable. Material events record actor/model, task, tool call, before/after refs, output summary, evidence and approval state.

A future implementation may use JSONL plus Git-linked artifacts. Secrets must not be written to audit logs.

### 4.11 Job Queue
The Supervisor will eventually support queued local work so the system can process permitted engineering tasks while unattended.

Jobs must have:
- bounded scope;
- permitted action classes;
- retry limits;
- required validators;
- stop/approval conditions;
- final status and evidence.

The queue must never convert an approval-required action into an automatic action merely because it is unattended.

## 5. Trust and execution boundaries

### Trusted for control
- Supervisor policy engine;
- committed governance/project policy;
- typed tool adapters;
- deterministic validators for their defined scope.

### Untrusted/advisory by default
- raw model output;
- model-generated shell commands before policy/tool validation;
- model self-reported confidence;
- third-party retrieved text until provenance is recorded.

### Secrets
Credentials, API keys and tokens remain outside prompts, repository history and audit artifacts. Tool adapters receive only the minimum credentials required for a permitted operation.

## 6. Execution lifecycle

```text
LOAD STATE
   -> OBSERVE
   -> PLAN
   -> POLICY CHECK
   -> ACT THROUGH TOOL
   -> CAPTURE EVIDENCE
   -> VALIDATE
   -> REVIEW
   -> RECORD STATE/AUDIT
   -> NEXT TASK OR STOP
```

A failed validation normally returns to diagnosis/rework within bounded retries. A policy boundary transitions to `NEEDS_HUMAN_APPROVAL` rather than being bypassed.

## 7. Project integration model

```text
engineering-ai (control plane)
    |
    +-- profile/policy --> PlataVM repository
    |
    +-- profile/policy --> BuoyCalc repository
    |
    +-- profile/policy --> future repositories
```

Each connected repository remains independently clonable, buildable, reviewable and usable without Engineering AI.

## 8. Multi-agent extension
Multi-agent operation is an extension of the same Supervisor, state, evidence and tool interfaces.

Potential future workers:
- engineering planner/reasoner;
- code worker;
- electronics/PCB worker;
- vision worker;
- CAD worker;
- image-generation worker;
- independent reviewer.

Workers do not form an unrestricted peer-to-peer swarm. The Supervisor assigns bounded tasks, records outputs, and controls hand-offs. Shared project truth remains external to every model.

## 9. External/OpenAI integration
An optional bridge may allow the local Supervisor to consult an external model for difficult reasoning/review or expose local tools through a controlled protocol such as MCP.

Requirements:
- local operation remains functional when the bridge is unavailable;
- project data sent externally is explicit and policy-controlled;
- all external consultations are auditable;
- an external model does not receive broader filesystem/tool authority merely because it has stronger reasoning capability.

## 10. Initial non-goals
The architecture baseline does not yet commit to:
- a specific local model;
- Ollama vs llama.cpp vs another runtime;
- a vector database;
- a GUI;
- autonomous publication/merging/release;
- self-modifying model weights or continual online fine-tuning;
- multi-agent orchestration;
- image generation or vision implementation.

These are selected only after the core control/validation loop is demonstrably stable.
