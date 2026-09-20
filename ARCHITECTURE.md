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

### 4.15 Persistent memory retrieval boundary

Gate 016 persistent memory is repository-independent shared engineering state,
but retrieval from that memory remains Supervisor/policy-controlled.

Gate 017 baseline retrieval:
- reads only typed memory records;
- requires an explicit project_id;
- defaults to latest revisions;
- excludes model/advisory memory by default;
- excludes proposed ADRs by default;
- preserves validation class, authority, provenance, source/evidence references,
  physical state and record integrity hash;
- uses deterministic bounded lexical ranking;
- produces a typed bounded context package;
- does not automatically inject that package into a model or Task Blackboard.

Retrieval relevance never promotes a record's evidence class. A highly relevant
ADVISORY record remains ADVISORY; a SOURCE record remains SOURCE; software test
evidence never becomes PHYSICAL.

Semantic/vector retrieval is an optional future backend, not an architectural
requirement. It requires benchmark evidence against simpler repository/search
methods before acceptance.

### 4.16 Knowledge lifecycle boundary

Gate 018 adds a deterministic lifecycle over Gate 016 memory without changing
or migrating accepted Gate 016 records.

Lifecycle state is stored in a separate append-only local SQLite ledger. Each
lifecycle revision binds exact immutable memory identities by:
- project_id;
- memory_id;
- record_id;
- revision;
- canonical content SHA-256;
- memory kind, authority and validation class.

The lifecycle states are:
`OBSERVATION -> EVIDENCE -> ACCEPTED -> INVALIDATED`.

An invalidated knowledge identity may later be re-qualified from current
evidence and accepted again. Re-qualification appends new lifecycle revisions;
it never erases or rewrites prior accepted/invalidated history.

Control rules:
- observation inputs must remain ADVISORY memory records;
- MODEL authority cannot own a lifecycle transition;
- evidence promotion accepts only current non-model evidence-qualified memory;
- CONTROL/ADR records are not evidence-qualified by the lifecycle and therefore
  cannot be used to bypass human architecture/policy decision authority;
- source and evidence revisions are bound exactly and checked against current
  Gate 016 memory revisions;
- dependency drift produces explicit STALE_SOURCE_REVISION or
  STALE_EVIDENCE_REVISION assessment;
- invalidation is append-only;
- no lifecycle transition infers PHYSICAL PASS/FAIL;
- lifecycle operations do not automatically inject context into models or the
  Task Blackboard.

An `ACCEPTED` lifecycle record means only that a non-control engineering claim
has current policy-qualified evidence. It does not authorize architecture,
physics, fabrication, release, destructive actions or any other action that
already requires human approval.

### 4.17 Persisted job queue boundary

Gate 019 persists bounded Supervisor job control state in a separate local
SQLite append-only event ledger. It does not execute tools or schedule work.

Each queue transition stores a complete schema-valid job snapshot plus:
- project/job identity;
- deterministic append sequence;
- queue event type;
- per-run timeout/deadline metadata;
- exact predecessor event;
- timestamp and canonical SHA-256 integrity hash.

Accepted queue transitions include:
- `ENQUEUED`;
- `RUN_STARTED`;
- `EXECUTION_RESULT`;
- `INTERRUPTED_RECOVERY`;
- `TIMEOUT_RECOVERY`.

Control rules:
- queueing never grants new action authority;
- immutable job scope, requested actions, validators and retry limit cannot
  change through a queue result;
- retries use the existing Supervisor job semantics and remain bounded;
- a retry returning to `QUEUED` re-enters deterministic FIFO order at the tail;
- `WAITING_FOR_APPROVAL` is persisted and is not claimable by the low-level
  queue API;
- resume from `WAITING_FOR_APPROVAL` is Supervisor-only and requires a fresh
  PolicyEngine check with explicit named human approval;
- a persisted `RUNNING` job found after process restart is recovered
  fail-closed to `BLOCKED`, never automatically retried or passed;
- an expired run deadline also recovers to `BLOCKED`;
- a result arriving after its persisted deadline cannot become queue `PASS`;
- terminal `PASS/FAIL/CANCELLED` jobs are not automatically requeued;
- project isolation and append-history integrity fail closed;
- the queue exposes no tool execution, scheduling, daemon, distributed-worker,
  or approval-granting surface.

Gate 019 is persistence and recovery only. Time-of-day scheduling, overnight
operation, unattended runner lifecycle and run summaries remain Gate 020.

### 4.18 Scheduled/unattended run boundary

Gate 020 adds persisted one-shot UTC schedules and bounded unattended sessions
on top of the accepted Gate 019 queue. A schedule is not a permission grant.

A schedule definition binds:
- schedule/project identity;
- explicit due_at timestamp with timezone;
- a bounded list of action names pre-authorized for this unattended session;
- max job claims;
- max session duration.

The current Supervisor/PolicyEngine is still evaluated for every queued job.
Gate 020 rules are:
- only actions that are currently `ALLOW` and also listed in the schedule's
  allowed_actions may invoke a supplied tool unattended;
- `NEEDS_HUMAN_APPROVAL` jobs may be claimed only to persist
  `WAITING_FOR_APPROVAL`; their tool is never called;
- denied/forbidden jobs may be claimed only to persist `BLOCKED`; their tool
  is never called;
- autonomous actions omitted from the schedule remain `QUEUED` and are not
  silently broadened into the unattended session;
- jobs with ambiguous multi-action scope are blocked without a tool call;
- missing or malformed unattended tool bindings fail closed;
- Gate 019 retry/timeout/deadline semantics remain authoritative;
- interrupted prior `RUNNING` queue jobs are recovered fail-closed before new
  unattended work;
- an interrupted scheduled session is terminally blocked on next invocation
  instead of being silently replayed;
- session max-jobs and max-duration budgets prevent unbounded overnight loops;
- summary counts are derived from persisted queue state for touched jobs and
  preserve deterministic evidence references;
- scheduled-run summaries always retain
  `physical_validation = PHYSICAL_NOT_EXECUTED` unless separate physical
  evidence exists outside this scheduler.

Schedule/session state is a separate append-only SQLite event ledger:
`SCHEDULED -> SESSION_STARTED -> SESSION_COMPLETED | SESSION_BLOCKED`,
or `SCHEDULED -> CANCELLED`.
Every event carries exact predecessor linkage and SHA-256 integrity.

Gate 020 provides a deterministic one-shot runner API/harness that can later be
invoked by a user-selected operating-system scheduler. It does not install or
configure Windows Task Scheduler/systemd/launchd, does not run a long-lived
daemon/service, and does not add remote/cloud or distributed execution.

### 4.19 External controlled advisory bridge

Gate 021 adds an optional provider-neutral external reasoning/review bridge. It
does not change local project authority and it is not a tool bridge.

Outbound disclosure is explicit:
- callers construct individual context items with project_id, context_id,
  source_ref, kind and exact text;
- context items cannot mix project identities;
- items marked as containing secrets are rejected;
- purpose, source_ref, kind, total context and output all have deterministic
  character bounds;
- there is no implicit repository/file/memory crawl or automatic context
  injection.

Before any provider call, the bridge evaluates the current
`external_disclosure` action through the deterministic Supervisor/PolicyEngine.
If current policy requires human approval, a named approver is required. A
missing approval produces `NEEDS_HUMAN_APPROVAL` and zero provider calls.
A denied disclosure produces `BLOCKED` and zero provider calls.

The provider-neutral call surface contains only:
- consultation identity;
- model identity;
- purpose;
- the exact explicitly supplied context tuples;
- max output size;
- timeout.

It carries no shell, filesystem, Git, job-queue, scheduler, local tool, approval
or MCP handle.

External consultation history is stored in a separate append-only SQLite
metadata ledger:
`REQUEST_RECORDED -> POLICY_BLOCKED | PROVIDER_FAILED | RESPONSE_ACCEPTED`.

The ledger stores request manifest metadata, source refs, character counts,
SHA-256 hashes, provider/model identity, policy approval metadata, response
hash/size and terminal status. It does not store the outbound context text or
purpose text. Provider exception text is not persisted because a remote runtime
may echo disclosed project data in an error string.

Accepted external output is always:
- authority = `ADVISORY`;
- evidence_eligible = `false`;
- physical_validation = `PHYSICAL_NOT_EXECUTED`.

An external review therefore cannot satisfy deterministic evidence, approve a
policy boundary, execute a local tool, mutate project truth, or establish
physical validation.

Gate 021 contains no concrete external network client or credentials. A real
OpenAI/ChatGPT/other provider adapter may be connected later under the same
bridge contract and explicit disclosure approval. The Engineering AI local core
remains fully functional when the bridge/provider is absent or unavailable.
Controlled MCP/tool exposure remains Gate 022.

### 4.20 Controlled registered tool exposure boundary

Gate 022 adds a transport-neutral registered-capability broker suitable for a
later MCP transport binding. The broker, not the transport/model, owns the
local capability map and policy path.

A capability definition is immutable and declares:
- capability_id and project_id;
- the existing project policy action it maps to;
- JSON Schema input/output contracts;
- side-effect class;
- timeout contract;
- request/response character budgets.

Gate 022 acceptance permits `READ_ONLY` capability metadata only. Initial real
bindings reuse previously accepted narrow adapters:
- `filesystem.read_text`, restricted to an explicit configured allow-list of
  relative paths in addition to the existing root-bounded filesystem adapter;
- `git.status`, using the existing fixed read-only Git adapter.

Every registered invocation must satisfy two independent policy checks:
1. `external_disclosure` must be currently ALLOW, because returning local tool
   output to an external/MCP transport is itself project-data disclosure;
2. the capability's mapped project action must also be currently ALLOW.

Where either boundary requires approval, a named approver is required.
Missing approval, policy denial, project mismatch, unregistered capability,
schema rejection or request-budget rejection produces zero local handler calls.

The registry is immutable after construction and public capability listing
returns only deep-immutable metadata/schema descriptors. Handler/adapter objects
are private to the local process. There is no dynamic import, eval/exec,
reflection-selected callable, generic shell/process command, filesystem-write,
Git mutation, approval-granting or public network-listener API in the Gate 022
bridge.

The capability handler receives a fixed timeout contract. Existing adapters
retain their own deterministic bounds; a handler-reported timeout, exception,
invalid result type, invalid output schema or oversized output fails closed.
Gate 022 does not create killable arbitrary-thread execution as a substitute for
adapter-native safety.

Each invocation is audited in a separate append-only SQLite metadata ledger:
`REQUEST_RECORDED -> POLICY_BLOCKED | TOOL_FAILED | RESULT_ACCEPTED`.

The ledger records project/invocation/capability identity, mapped action,
combined disclosure+action policy decisions, approval metadata, request/result
SHA-256 hashes, byte/character sizes, evidence refs and failure class. It does
not persist request arguments or result payloads, and exception text is not
persisted.

Gate 022 contains no concrete MCP server, stdio/SSE/HTTP listener or public
network endpoint. A future MCP transport can bind to `list_capabilities()`
and `invoke()`, but cannot obtain broader authority than the accepted broker.

Tool/software PASS never implies physical validation. Physical validation
remains `PHYSICAL_NOT_EXECUTED` unless independently established.

### 4.21 Provenance-preserving Vision worker boundary

Gate 023 adds a bounded local Vision-worker path for explicit
schematics/photos/screenshots/plots without changing the deterministic authority
model.

Visual inputs are caller-supplied transient records. Each image carries:
- an explicit project/source reference;
- an allow-listed media type (PNG, JPEG or WebP);
- a bounded byte payload;
- deterministic byte size and SHA-256 identity.

The provider transport receives image bytes inline only. It receives no local
path, URL, filesystem handle, camera handle, shell, Git or tool authority. The
loopback Ollama adapter serializes only the explicit bytes supplied by the
caller.

Vision analysis is a distinct deterministic routing class. A candidate may be
routed only if its measured capability record explicitly qualifies Vision input
support and carries qualification evidence. Gate 023 deliberately does not
self-qualify a production Vision model: until separate measured local evidence
is accepted, the default accepted registry returns `NO_ROUTE` for Vision.

A Vision result:
- cites only exact source references from the supplied image manifest;
- is schema-bounded;
- is always `ADVISORY`;
- is `evidence_eligible=false`;
- cannot directly become deterministic or physical evidence;
- is not automatically promoted to the Task Blackboard or knowledge lifecycle.

Provider tool calls are rejected on the Vision path. Unsupported media,
signature mismatch, input-budget overflow, missing qualification, provider
mismatch, malformed JSON/schema output or unknown source references fail closed.
Raw image bytes are not part of the returned observation record.

Vision/software/synthetic PASS never implies physical validation. Physical
validation remains `PHYSICAL_NOT_EXECUTED` unless independently established.

### 4.22 Controlled parametric CAD worker boundary

Gate 024 adds a bounded proposal-only CAD path without granting any new
autonomous write, fabrication, release, or physical-validation authority.

The CAD input is an immutable typed parametric design. The Gate 024 baseline is
deliberately narrow:
- units are millimetres;
- supported primitives are axis-aligned boxes and cylinders;
- placement is translation only;
- entity count, dimensions and coordinates are bounded;
- entity identifiers are unique and ASCII-safe;
- arbitrary sketches, constraints, rotations, booleans/CSG, assemblies and FEM
  are outside this Gate.

Before a CAD runtime is called, deterministic Python geometry derives:
- the canonical design SHA-256;
- each primitive's analytical volume;
- each primitive's axis-aligned bounding box;
- the assembly axis-aligned bounding box;
- the sum of primitive volumes, explicitly not boolean-union volume.

CAD generation/manipulation maps only to the already accepted Supervisor action
`propose_patch`. The CAD worker calls the existing Supervisor/PolicyEngine for
that action and makes zero CAD-backend calls when current policy denies it. Gate
024 does not introduce a `cad_write` permission or reinterpret fabrication or
release authority.

The concrete FreeCAD bridge is data-driven. It invokes a fixed repository-owned
helper through `FreeCADCmd` with `shell=False` and passes only canonical JSON
plus temporary artifact/report paths. Model-provided Python, macros, shell
commands, arbitrary executables, dynamic imports, `eval`, and `exec` are not
part of the interface.

The runtime writes a temporary FCStd candidate and a structured geometry report.
The control plane compares runtime entity identity, primitive kind, volume and
AABB against the deterministic expected geometry. A mismatch fails closed and
the requested target artifact is not published. Only after all checks pass is
the root-bounded FCStd proposal atomically moved to its target path.

A successful Gate 024 result establishes only that the generated proposal
matches the bounded parametric specification for the checked geometry. It does
not establish design intent, structural adequacy, manufacturability,
fabrication authorization, release authorization or physical validation.
Physical state therefore remains `PHYSICAL_NOT_EXECUTED`.

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
