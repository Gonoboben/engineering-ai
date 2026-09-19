# ARCHITECTURE.md

## 1. Mission
Engineering AI is a local-first control plane for autonomous and semi-autonomous engineering work. It coordinates replaceable AI models with deterministic engineering tools while keeping project state, evidence, validation, governance, and audit outside model memory.

The initial single-model core was established through Gate 006. The next architecture baseline adds Supervisor-mediated multi-model specialization while preserving the same deterministic authority, evidence, validation, project-isolation, and audit boundaries. Vision, image generation, CAD-specialist workers, and connected-project write authority remain later capabilities.

## 2. Architectural principles
1. **Repository-backed truth** — authoritative state is stored in repositories and explicit project-state records.
2. **Offline-first** — core engineering operation must continue without internet access.
3. **Replaceable models** — model providers/runtimes are adapters, not architectural dependencies.
4. **Deterministic validation** — compilers, tests, ERC/DRC, SPICE/FEM, calculation scripts and measured evidence outrank model claims.
5. **External policy enforcement** — an ordinary program, the Supervisor, controls permissions and stop conditions.
6. **Project isolation** — connected projects remain independent repositories with independent governance.
7. **Evidence before confidence** — conclusions are linked to sources, calculations, simulations, tests or measurements.
8. **Auditable autonomy** — material actions are reconstructable after the fact.
9. **Supervisor-mediated specialization** — the validated single-agent core is the foundation; specialist models are added only behind the same deterministic Supervisor, evidence, and policy interfaces.
10. **Human authority at irreversible boundaries** — architecture, physics, fabrication, publishing, destructive actions and other policy boundaries remain human-controlled unless explicitly delegated.

## 3. System context

```text
User / External controlled reviewer
              |
              v
+----------------------------------+
| Deterministic Engineering        |
| Supervisor                       |
| policy / state / approvals       |
+--------+-------------+-----------+
         |             |
         |             +----------------------+
         |                                    |
         v                                    v
  Model Capability Registry              Tool Bus
         |                            narrow typed tools
         v                                    |
  Deterministic Model Router                   v
    /        |         \                Deterministic
   /         |          \               tool outcomes
  v          v           v                     |
Planner   Code Worker  Deep Reasoner            |
 / General  / Reviewer   / Escalation           |
   \         |          /                       |
    \        |         /                        |
     +-------+--------+                          |
             |                                   |
             v                                   |
   Supervisor-controlled                        |
       Task Blackboard <-------------------------+
             |
             v
     Evidence + Validation
             |
             v
       Supervisor Review
             |
             v
      Project State / Audit
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

### 4.2 Model Interface / Model Capability Registry / Model Router
A stable interface abstracts model runtime/provider details. Gate 005 established the replaceable model interface and one accepted baseline model. Gate 007 defines the multi-model extension.

The **Model Capability Registry** records only measured/qualified capability metadata, including:
- model/runtime identity and version;
- qualification state;
- accepted role classes;
- structured-output and tool-proposal behavior;
- context/output limits;
- measured latency/throughput;
- measured RAM/VRAM/resource envelope;
- known failure modes and evidence references.

Public model cards and benchmark claims may nominate candidates but do not grant production roles.

The **Model Router** is deterministic and Supervisor-owned. It may route bounded tasks by accepted capability, resource availability, and policy. A model cannot assign itself a privileged role, select a broader tool surface, or bypass an approval boundary.

Candidate role classes include:
- general planning/task decomposition;
- code/repository work;
- deep engineering reasoning/escalation;
- independent review/critique;
- later vision/CAD/image specialization.

Routing decisions must be auditable and reproducible from the registry state and task classification.

### 4.3 Engineering Workers
Engineering workers are replaceable model-backed roles operating through the shared model interface.

A worker may:
- understand a bounded assigned task;
- inspect only supplied/authorized context;
- propose plans or actions;
- propose permitted tool calls through the Supervisor;
- analyze deterministic outputs;
- prepare advisory changes or review findings;
- request additional evidence or human approval.

A worker does not own repository credentials, unrestricted shell access, routing authority, accepted project state, evidence promotion, or final policy decisions.

Workers do not communicate peer-to-peer directly. Hand-offs are mediated by the Supervisor through typed task/blackboard records.

### 4.4 Reviewer
The Reviewer evaluates completed work against the original task and supplied deterministic evidence.

Gate 006 validated Planner/Executor/Reviewer separation with one model. In the multi-model architecture, the Reviewer may be a separately qualified model, but remains advisory.

Reviewer outcomes are bounded states such as:
- `ACCEPT`;
- `REVISE`;
- `REJECT`;
- `NEEDS_HUMAN_APPROVAL`.

Reviewer agreement, model confidence, or multi-model majority is never engineering evidence by itself. The Supervisor owns the terminal state and may require deterministic verification or human escalation.

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


### 4.12 Supervisor-controlled Task Blackboard
The Task Blackboard is the only shared inter-worker communication surface.

Typed records may include:
- task and role assignment;
- bounded plan;
- model claims;
- open questions;
- proposed actions/tool calls;
- deterministic evidence references;
- review findings;
- approval requests/results;
- terminal state.

Writing a model statement to the Blackboard does not promote it to evidence or accepted project truth. The Supervisor controls which records are visible to each worker and which state transitions they may influence.

### 4.13 Model disagreement and escalation
Model disagreement is resolved by evidence, not voting.

Preferred resolution order:
1. run a deterministic validator/tool/calculation when available;
2. obtain an independent bounded review from a qualified worker;
3. request bounded revision with explicit unresolved claims;
4. escalate to human approval/decision when evidence cannot resolve the conflict.

Multiple models repeating the same claim does not increase its validation class.

### 4.14 External Control Bridge
A future optional external bridge may allow ChatGPT/OpenAI or another external reviewer to submit bounded requests, inspect audit/evidence, or provide advisory review.

The bridge:
- is policy-controlled and auditable;
- sends only explicit approved outbound context;
- never receives unrestricted shell/filesystem authority;
- cannot mutate local policy/state directly;
- cannot bypass the deterministic Supervisor;
- is optional, so local Engineering AI remains functional offline.

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

## 8. Supervised multi-model architecture
Multi-model operation is an extension of the validated Gate 006 control loop, not a replacement for it.

Initial candidate assignments to be measured on the primary workstation:
- `Qwen3.5-9B` — candidate fast general worker / Planner and later multimodal worker;
- `Qwen2.5-Coder-7B` — candidate code/repository specialist;
- `gpt-oss:20b / medium` — already accepted Gate 005 baseline, candidate deep-reasoning/escalation worker;
- `Huihui Qwen3 14B` — measured secondary candidate for later independent critique/review;
- 27B-class candidates — deferred on the current workstation unless later evidence justifies them.

These are candidate roles, not accepted production routing. Each role requires local measured qualification before the registry marks it usable.

Workers do not form an unrestricted peer-to-peer swarm. The Supervisor classifies the task, chooses a qualified role/model, supplies bounded context, controls all hand-offs, evaluates tool proposals, and records evidence/audit.

Shared project truth remains external to every model. Model-to-model communication occurs only through Supervisor-controlled typed records.

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
- unrestricted peer-to-peer agent swarms;
- image generation or vision implementation.

These are selected only after the core control/validation loop is demonstrably stable.
