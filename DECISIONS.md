# DECISIONS.md

This file records accepted/proposed architectural decisions for the Engineering AI control plane. Until Gate 001 is merged, these entries are `PROPOSED`.

---

## ADR-0001 — Repository-backed state is authoritative
Status: `PROPOSED`

### Decision
Authoritative project state must be stored in repositories and explicit machine-readable state/evidence records. Chat history, model context and model memory are not authoritative sources of truth.

### Rationale
Model context is transient, incomplete and replaceable. Engineering work must be reproducible across chats, machines, models and time.

### Consequence
Every material project transition must be reconstructable without relying on conversational memory.

---

## ADR-0002 — Use a deterministic non-LLM Supervisor
Status: `PROPOSED`

### Decision
Permissions, stop conditions, retries, state transitions, approval boundaries and audit are enforced by an ordinary program outside the LLM.

### Rationale
Policy enforcement cannot depend solely on prompt compliance or model self-discipline.

### Consequence
The Supervisor must be testable with stub/fake agents before any production model is connected.

---

## ADR-0003 — AI models are replaceable workers
Status: `PROPOSED`

### Decision
Core architecture uses a stable model interface; no project state or governance semantics may depend on one vendor/model/runtime.

### Rationale
Local models will improve rapidly and different tasks may benefit from different capabilities.

### Consequence
Model-specific prompting/adapters live behind a narrow interface and can be replaced without redesigning state, tools or governance.

---

## ADR-0004 — Offline-first is a primary requirement
Status: `PROPOSED`

### Decision
Core project continuation, local reasoning, repository access, deterministic tools, validation, memory and audit must function without internet access once required local dependencies/models are installed.

### Rationale
The system is intended to remain useful as a private local engineering environment and not depend on external service availability.

### Consequence
External/OpenAI/GitHub/web capabilities are optional extensions and their absence must degrade capability, not invalidate the control plane.

---

## ADR-0005 — Connected projects remain independent repositories
Status: `PROPOSED`

### Decision
Engineering AI is a control plane. PlataVM, BuoyCalc and future projects remain separate repositories and are connected via project profiles/adapters.

### Rationale
Preserves project autonomy, existing Git history/governance, independent buildability and clean ownership boundaries.

### Consequence
Do not create a monorepo containing copies of connected projects.

---

## ADR-0006 — Deterministic validation outranks model claims
Status: `PROPOSED`

### Decision
Compiler/tests/ERC/DRC/SPICE/FEM/calculation outputs and physical evidence are authoritative for their defined scopes. A model may explain or challenge assumptions, but cannot declare a failed check to have passed.

### Rationale
Language-model confidence is not engineering evidence.

### Consequence
Completion states must reference actual recorded validator/evidence results.

---

## ADR-0007 — Do not weaken validation to obtain PASS
Status: `PROPOSED`

### Decision
The system must not suppress, disable or weaken validators/tests/CI/ERC/DRC solely to make work appear successful.

### Rationale
A green result obtained by reducing the test is not evidence that the engineering problem is solved.

### Consequence
Any proposal to change validation semantics is an explicit human-approval boundary and separate scoped decision.

---

## ADR-0008 — Simulation and physical validation are separate classes
Status: `PROPOSED`

### Decision
Synthetic, simulated, calculated and software-test results must never be represented as physical test results.

### Rationale
Engineering traceability requires preserving the validation class of every result.

### Consequence
State/evidence schemas must carry physical-validation status explicitly.

---

## ADR-0009 — Evidence and provenance are first-class data
Status: `PROPOSED`

### Decision
Material engineering conclusions should be linked to sources, assumptions, calculations, simulation/test runs, revisions and validation class.

### Rationale
Long-running projects require the ability to answer not only what was decided, but why and on what evidence.

### Consequence
The implementation must support structured evidence references before advanced memory/RAG features are considered complete.

---

## ADR-0010 — Single-agent reliability precedes multi-agent specialization
Status: `PROPOSED`

### Decision
First establish one engineering agent operating through the Supervisor. Specialist code/electronics/vision/CAD/image/reviewer agents are later extensions.

### Rationale
Premature multi-agent systems increase coordination complexity and can amplify shared errors while obscuring accountability.

### Consequence
Multi-agent work remains out of scope until the core policy/tool/evidence loop is stable and benchmarked.

---

## ADR-0011 — Multi-agent workers are Supervisor-routed, not an unrestricted swarm
Status: `PROPOSED`

### Decision
When specialist workers are introduced, the Supervisor assigns bounded tasks and controls hand-offs. Agents do not form an unrestricted peer-to-peer decision network.

### Rationale
Engineering accountability requires explicit task ownership, evidence boundaries and deterministic stop conditions.

### Consequence
Consensus between models never substitutes for deterministic validation or human approval.

---

## ADR-0012 — Continual self-training is not part of the initial architecture
Status: `PROPOSED`

### Decision
Project learning is initially implemented through explicit memory, evidence, decisions and lessons rather than automatic modification of model weights during operation.

### Rationale
Online self-training risks reinforcing model errors and reducing reproducibility.

### Consequence
Fine-tuning/LoRA may be evaluated later using curated validated datasets as a separate controlled capability.
