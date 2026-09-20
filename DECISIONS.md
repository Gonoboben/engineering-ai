# DECISIONS.md

This file records accepted and proposed architectural decisions for the Engineering AI control plane. ADR-0001 through ADR-0012 were accepted with the Gate 001 architecture baseline; later ADRs retain an explicit pending/accepted Gate status.

---

## ADR-0001 — Repository-backed state is authoritative
Status: `ACCEPTED_GATE_001`

### Decision
Authoritative project state must be stored in repositories and explicit machine-readable state/evidence records. Chat history, model context and model memory are not authoritative sources of truth.

### Rationale
Model context is transient, incomplete and replaceable. Engineering work must be reproducible across chats, machines, models and time.

### Consequence
Every material project transition must be reconstructable without relying on conversational memory.

---

## ADR-0002 — Use a deterministic non-LLM Supervisor
Status: `ACCEPTED_GATE_001`

### Decision
Permissions, stop conditions, retries, state transitions, approval boundaries and audit are enforced by an ordinary program outside the LLM.

### Rationale
Policy enforcement cannot depend solely on prompt compliance or model self-discipline.

### Consequence
The Supervisor must be testable with stub/fake agents before any production model is connected.

---

## ADR-0003 — AI models are replaceable workers
Status: `ACCEPTED_GATE_001`

### Decision
Core architecture uses a stable model interface; no project state or governance semantics may depend on one vendor/model/runtime.

### Rationale
Local models will improve rapidly and different tasks may benefit from different capabilities.

### Consequence
Model-specific prompting/adapters live behind a narrow interface and can be replaced without redesigning state, tools or governance.

---

## ADR-0004 — Offline-first is a primary requirement
Status: `ACCEPTED_GATE_001`

### Decision
Core project continuation, local reasoning, repository access, deterministic tools, validation, memory and audit must function without internet access once required local dependencies/models are installed.

### Rationale
The system is intended to remain useful as a private local engineering environment and not depend on external service availability.

### Consequence
External/OpenAI/GitHub/web capabilities are optional extensions and their absence must degrade capability, not invalidate the control plane.

---

## ADR-0005 — Connected projects remain independent repositories
Status: `ACCEPTED_GATE_001`

### Decision
Engineering AI is a control plane. PlataVM, BuoyCalc and future projects remain separate repositories and are connected via project profiles/adapters.

### Rationale
Preserves project autonomy, existing Git history/governance, independent buildability and clean ownership boundaries.

### Consequence
Do not create a monorepo containing copies of connected projects.

---

## ADR-0006 — Deterministic validation outranks model claims
Status: `ACCEPTED_GATE_001`

### Decision
Compiler/tests/ERC/DRC/SPICE/FEM/calculation outputs and physical evidence are authoritative for their defined scopes. A model may explain or challenge assumptions, but cannot declare a failed check to have passed.

### Rationale
Language-model confidence is not engineering evidence.

### Consequence
Completion states must reference actual recorded validator/evidence results.

---

## ADR-0007 — Do not weaken validation to obtain PASS
Status: `ACCEPTED_GATE_001`

### Decision
The system must not suppress, disable or weaken validators/tests/CI/ERC/DRC solely to make work appear successful.

### Rationale
A green result obtained by reducing the test is not evidence that the engineering problem is solved.

### Consequence
Any proposal to change validation semantics is an explicit human-approval boundary and separate scoped decision.

---

## ADR-0008 — Simulation and physical validation are separate classes
Status: `ACCEPTED_GATE_001`

### Decision
Synthetic, simulated, calculated and software-test results must never be represented as physical test results.

### Rationale
Engineering traceability requires preserving the validation class of every result.

### Consequence
State/evidence schemas must carry physical-validation status explicitly.

---

## ADR-0009 — Evidence and provenance are first-class data
Status: `ACCEPTED_GATE_001`

### Decision
Material engineering conclusions should be linked to sources, assumptions, calculations, simulation/test runs, revisions and validation class.

### Rationale
Long-running projects require the ability to answer not only what was decided, but why and on what evidence.

### Consequence
The implementation must support structured evidence references before advanced memory/RAG features are considered complete.

---

## ADR-0010 — Single-agent reliability precedes multi-agent specialization
Status: `ACCEPTED_GATE_001`

### Decision
First establish one engineering agent operating through the Supervisor. Specialist code/electronics/vision/CAD/image/reviewer agents are later extensions.

### Rationale
Premature multi-agent systems increase coordination complexity and can amplify shared errors while obscuring accountability.

### Consequence
Multi-agent work remains out of scope until the core policy/tool/evidence loop is stable and benchmarked.

---

## ADR-0011 — Multi-agent workers are Supervisor-routed, not an unrestricted swarm
Status: `ACCEPTED_GATE_001`

### Decision
When specialist workers are introduced, the Supervisor assigns bounded tasks and controls hand-offs. Agents do not form an unrestricted peer-to-peer decision network.

### Rationale
Engineering accountability requires explicit task ownership, evidence boundaries and deterministic stop conditions.

### Consequence
Consensus between models never substitutes for deterministic validation or human approval.

---

## ADR-0012 — Continual self-training is not part of the initial architecture
Status: `ACCEPTED_GATE_001`

### Decision
Project learning is initially implemented through explicit memory, evidence, decisions and lessons rather than automatic modification of model weights during operation.

### Rationale
Online self-training risks reinforcing model errors and reducing reproducibility.

### Consequence
Fine-tuning/LoRA may be evaluated later using curated validated datasets as a separate controlled capability.


---

## ADR-0013 — Use Supervisor-mediated multi-model specialization
Status: `ACCEPTED_GATE_007`

### Decision
Engineering AI may use multiple specialized local models only as replaceable advisory workers behind the deterministic Supervisor.

Model-to-model work hand-offs are mediated by the Supervisor through typed bounded task records / a Task Blackboard. Workers do not form an unrestricted peer-to-peer swarm.

The Supervisor alone owns:
- task/role assignment;
- permissions and tool execution decisions;
- state transitions;
- retry/revision limits;
- approval boundaries;
- evidence promotion;
- final job state.

A deterministic Model Capability Registry records locally measured qualification evidence. A deterministic Model Router may select only roles/models that are accepted for the requested task class and resource envelope.

### Candidate baseline
Candidates to qualify after this architecture Gate:
- `Qwen3.5-9B` — general/Planner candidate and possible future multimodal worker;
- `Qwen2.5-Coder-7B` — code/repository specialist candidate;
- `gpt-oss:20b / medium` — accepted Gate 005 baseline and deep-reasoning/escalation candidate;
- `Huihui Qwen3 14B` — later independent critic/reviewer candidate;
- 27B-class models — deferred on the current workstation unless new evidence justifies them.

Candidate naming does not constitute production qualification.

### Rationale
The validated Gate 006 single-model Planner/Executor/Reviewer loop established the control boundary. Specialization can improve quality and speed without duplicating policy authority if all roles continue through the same Supervisor/evidence interfaces.

Direct peer-to-peer agent systems can amplify shared errors, hide provenance, and blur authority.

### Consequence
- model agreement or majority vote is never evidence;
- role assignment requires measured local qualification;
- deterministic validators and physical evidence continue to outrank every model;
- hand-offs and disagreements are auditable;
- a model cannot select a more privileged model/tool route for itself;
- later implementation must preserve the Gate 006 control loop semantics.

---

## ADR-0014 — External AI oversight uses a controlled bridge
Status: `ACCEPTED_GATE_007`

### Decision
ChatGPT/OpenAI or another external model may later act as an optional external reviewer/architect through a policy-controlled bridge, but it receives no direct authority over local policy, state, credentials, unrestricted shell, or project repositories.

External requests are submitted to the deterministic Supervisor as bounded requests. The Supervisor decides what context may leave the local system, what actions are admissible, and what evidence/state changes are permitted.

### Rationale
A stronger external model can provide useful architecture/review assistance while the local control plane remains private, offline-capable, reproducible, and safe.

### Consequence
- external consultation is optional and auditable;
- outbound context must be explicit and policy-controlled;
- the local system remains functional when the external bridge is unavailable;
- external model output remains advisory;
- external control cannot bypass human approval or deterministic validation.


---

## ADR-0015 — Use append-only local SQLite decision/evidence memory
Status: `ACCEPTED_GATE_016`

### Decision
Engineering AI decision/evidence memory uses a local append-only SQLite store
with immutable revisions, explicit provenance/evidence/source references,
canonical SHA-256 integrity hashes, project isolation, deterministic bounded
filter/keyword search and exact supersession links.

Memory records are typed as ADR, calculation, test result, failure lesson or
source reference.

Model-authored records remain `ADVISORY`. An accepted ADR requires human
authority. Deterministic/physical validation classes require explicit evidence
references and cannot be promoted from model claims. Physical PASS/FAIL remains
a distinct explicit class.

Gate 016 does not automatically inject memory into model context and does not
implement semantic/vector retrieval.

### Rationale
The control plane needs durable engineering context across jobs/chats without
making transient model context authoritative. SQLite is local, offline,
transactional and available in the Python standard library, which keeps the
first memory implementation simple and auditable.

Append-only revisions preserve historical reasoning and prevent later memory
updates from silently rewriting the evidence that supported an earlier
decision.

### Consequence
- historical memory records are not UPDATEd or DELETEd;
- correction occurs through exact supersession by a new revision;
- reading a record verifies its integrity hash;
- project-specific search cannot leak another project's memory;
- model output can be remembered as advisory but not promoted to truth;
- Gate 017 may later retrieve memory into bounded model context only through
  separate policy-controlled retrieval semantics;
- vector databases/embeddings remain deferred.


---

## ADR-0016 — Use deterministic provenance-preserving retrieval as the baseline
Status: `ACCEPTED_GATE_017`

### Decision
Engineering AI retrieval starts with a deterministic lexical layer over the
accepted Gate 016 decision/evidence memory.

Default retrieval:
- is project-scoped;
- uses latest revisions only;
- excludes MODEL/ADVISORY records;
- excludes PROPOSED ADRs;
- preserves authority, validation class, physical state, provenance,
  evidence/source references and integrity SHA-256;
- uses bounded candidate/result/context budgets;
- returns a typed context package only;
- performs no automatic Blackboard/model prompt injection.

Advisory memory, proposed ADRs and historical revisions may be retrieved only
through explicit opt-in and remain visibly labelled.

Semantic/vector retrieval is not accepted by default. It may be introduced only
after a separate local benchmark demonstrates materially better relevant
engineering recall than repository/search baselines while preserving provenance,
validation semantics and acceptable resource cost.

### Rationale
Gate 016 established durable memory, but retrieval is another trust boundary.
A memory record becoming relevant to a query must not silently increase its
authority or validation class.

A lexical baseline is offline, deterministic, dependency-free and directly
auditable. It also creates a measurable benchmark before adding embeddings or
a vector database.

### Consequence
- retrieval rank is relevance only, not evidence strength;
- retrieved metadata remains explicit in every context item;
- superseded/advisory/proposed records cannot silently enter default context;
- context is bounded without truncating individual records;
- memory integrity failures fail closed;
- no vector backend is added in Gate 017 unless separately benchmark-qualified;
- Gate 018 remains responsible for knowledge promotion/invalidation lifecycle.


---

## ADR-0017 — Use a separate append-only ledger for knowledge lifecycle
Status: `ACCEPTED_GATE_018`

### Decision
Engineering AI knowledge promotion/invalidation is represented in a separate
local append-only SQLite lifecycle ledger layered over the accepted Gate 016
decision/evidence memory.

The lifecycle ledger does not copy or rewrite Gate 016 record contents. Instead
each lifecycle record binds exact memory revisions by project_id, memory_id,
record_id, revision, content SHA-256, authority, kind and validation class.

Lifecycle stages are:
- `OBSERVATION`;
- `EVIDENCE`;
- `ACCEPTED`;
- `INVALIDATED`.

Model-authored observations remain ADVISORY and cannot own lifecycle
transitions. Evidence qualification requires current, non-model,
evidence-qualified memory records. CONTROL/ADR records are deliberately not
evidence-qualified through this lifecycle, preserving human authority over
accepted ADRs and existing architecture/policy boundaries.

A bound source/evidence revision becoming superseded is detected
deterministically. The claim is assessed as stale and may then be invalidated by
appending a new lifecycle revision. After invalidation, the same knowledge
identity may be re-qualified using current evidence and accepted again, also
through append-only revisions.

Lifecycle assessment never infers physical validation and performs no automatic
model/Blackboard context injection.

### Rationale
Gate 016 provides durable immutable evidence records and Gate 017 retrieves
them safely, but neither defines when a claim becomes accepted knowledge or how
that acceptance reacts when supporting sources change.

Keeping lifecycle state separate avoids a migration or semantic mutation of the
already accepted Gate 016 store. Exact revision/hash bindings make stale
knowledge mechanically detectable while preserving the full history of what
was known, accepted, invalidated and later re-qualified.

### Consequence
- Gate 016 memory UPDATE/DELETE semantics remain unchanged;
- knowledge history is append-only and integrity-hashed;
- source/evidence drift never silently leaves an old acceptance current;
- model confidence/majority never promotes knowledge;
- accepted non-control knowledge does not bypass architecture/physics/release
  approval boundaries;
- physical PASS/FAIL remains explicit physical evidence only;
- Gate 017 retrieval does not itself promote lifecycle state;
- Gate 019 queueing and Gate 023 vision integration remain separate future
  Gates.


---

## ADR-0018 — Persist job control state as an append-only local queue ledger
Status: `ACCEPTED_GATE_019`

### Decision
Engineering AI Gate 019 persists bounded job queue state in a local SQLite
append-only event ledger owned through the deterministic Supervisor boundary.

A queue event stores the complete validated job snapshot together with event
type, exact predecessor, timeout/deadline metadata, timestamp and canonical
SHA-256 integrity hash. Queue history is linear per project/job and immutable
job-definition fields cannot change across transitions.

The low-level queue does not execute tools, schedule work or grant approval.
Normal queued work may be claimed deterministically. An approval-waiting job
can resume only through a Supervisor method that re-evaluates current policy
with an explicit named human approver.

RUNNING work interrupted by process restart or exceeding its persisted run
deadline is recovered fail-closed to BLOCKED. It is never silently marked PASS
or automatically retried because the external action may have partially
executed.

### Rationale
Gate 003 already defines deterministic job states and bounded retries, but those
states were process-local. Gate 019 must survive restart without weakening
policy or guessing whether an interrupted external action completed.

An append-only event ledger preserves a reconstructable history and avoids a
mutable queue row silently rewriting prior state. Fail-closed interrupted-run
recovery is deliberately conservative because replaying an uncertain action can
duplicate side effects.

### Consequence
- job state and attempts survive process close/reopen;
- FIFO claim order is deterministic;
- bounded retry results can return to the queue tail;
- WAITING_FOR_APPROVAL persists without automatic claim;
- explicit approval still belongs to the existing Supervisor/PolicyEngine;
- timeout/interrupt recovery produces BLOCKED, not PASS;
- queue integrity and exact event supersession are verifiable;
- scheduling and overnight operation remain Gate 020;
- queue persistence does not imply physical validation or broaden project
  permissions.


---

## ADR-0019 — Use persisted one-shot schedules with Supervisor re-authorization
Status: `ACCEPTED_GATE_020`

### Decision
Gate 020 scheduled/unattended work is represented by explicit persisted one-shot
UTC schedules plus append-only session history. A schedule records only a
bounded unattended allow-list and execution budgets; it never grants project
authority.

Before every queued job is executed, the current deterministic
Supervisor/PolicyEngine is evaluated again. Tool execution is possible only
when both conditions are true:
1. current policy returns `ALLOW`;
2. the action is present in the schedule's `allowed_actions`.

Approval-required work transitions to persisted `WAITING_FOR_APPROVAL`
without a tool call. Denied/forbidden work transitions to `BLOCKED` without a
tool call. Autonomous actions not listed by the schedule remain `QUEUED`.

Each session has explicit max-job and max-duration limits. Interrupted prior
queue jobs are recovered using Gate 019 fail-closed semantics before new work.
An interrupted scheduled session is blocked on reopen and is never silently
replayed.

Session summaries record deterministic final counts for touched jobs, evidence
references, recovery information and `PHYSICAL_NOT_EXECUTED`.

### Rationale
Gate 019 makes job state durable but intentionally provides no scheduler.
Unattended/overnight operation requires due-time selection and run budgeting
without turning elapsed time or schedule membership into authorization.

Rechecking policy at execution time prevents stale schedules from bypassing a
later tightened project policy. One-shot append-only sessions avoid ambiguous
automatic replay after process failure and keep audit history reconstructable.

### Consequence
- due schedules survive process restart;
- not-due schedules do not execute;
- schedule membership cannot elevate approval-required or forbidden actions;
- explicit current policy remains authoritative;
- unattended sessions are bounded by job count and duration;
- summaries are deterministic and evidence-linked;
- OS scheduler/service installation remains external/out of scope;
- no long-lived daemon, remote queue, distributed workers or automatic approval
  is introduced;
- scheduled software PASS never implies physical validation.


---

## ADR-0020 — External review uses explicit disclosure manifests and remains advisory
Status: `PROPOSED_GATE_021`

### Decision
Gate 021 implements external reasoning/review as an optional provider-neutral
consultation bridge controlled by the existing deterministic Supervisor.

No provider call occurs until current policy evaluates `external_disclosure`.
Where policy requires human approval, a named approver is mandatory.

Outbound context is caller-explicit and project-scoped. Every disclosed item has
a source reference, kind, exact content SHA-256 and character count. Cross-project
mixing and items explicitly marked as containing secrets are rejected.
Purpose/context/output/timeout dimensions are bounded.

The external provider receives no local tool, shell, filesystem, Git, queue,
scheduler, approval or MCP authority.

External responses are returned only as `ADVISORY`,
`evidence_eligible=false`, with no physical-validation inference.

A separate append-only SQLite ledger records metadata and hashes for each
consultation, but deliberately does not persist outbound context or purpose
text. Provider exception strings are not persisted.

### Rationale
External reasoning can be useful for difficult independent review, but sending
project data outside the workstation is itself a controlled disclosure event.
Treating an external model as stronger authority would violate the accepted
local-first Supervisor architecture.

Explicit manifests make the disclosed payload reviewable and bounded. Current
policy re-evaluation prevents a stale consultation request from bypassing later
permission changes. Metadata-only audit retains accountability without creating
a second copy of disclosed project content.

### Consequence
- local operation remains independent of any external service;
- missing approval yields zero provider calls;
- external disclosure is attributable to an explicit named approver when
  required by policy;
- only explicitly selected context is sent;
- request/response hashes and provider identity remain auditable;
- malformed, oversized or failed provider responses fail closed;
- external text is advisory and cannot become deterministic/physical evidence
  by itself;
- no credentials or concrete network client are required for Gate 021;
- external local-tool exposure remains separately gated by Gate 022.
