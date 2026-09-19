# Gate 006 Local Role-Loop Smoke Evidence

## Scope

Narrow read-only runtime smoke for the controlled Planner / Executor / Reviewer loop.

Target runtime:
- model: `gpt-oss:20b`
- reasoning: `medium`
- context: `8192`
- max output: `2048`
- provider: loopback-only Ollama
- permitted action: `read_repository`
- physical validation: `PHYSICAL_NOT_EXECUTED`

## Attempt 1 — runtime contract mismatch found

Date: 2026-09-19

Repository head:
`30ade24c9128a0c44cd81a7e90f0740237d1711c`

Observed result:
`FAIL_RUNTIME_CONTRACT`

The Planner phase completed far enough to enter Executor. The local `gpt-oss:20b`
Executor returned an Ollama response whose structured `content` field was empty
while the response carried a tool proposal. Gate 006 incorrectly attempted to
parse the empty content as JSON and raised:

`SemanticValidationError: EXECUTOR returned invalid JSON`

This is not evidence of an engineering-domain failure and not a tool-policy
failure. Gate 005's accepted `tool-proposal` benchmark scores
`response.tool_calls` directly and does not require accompanying JSON content.

## Correction

Gate 006 Executor semantics were aligned with the accepted Gate 005 provider
contract:

- non-empty Executor `content` is still parsed and validated as structured JSON;
- an empty `content` is accepted only when at least one model tool proposal is
  present;
- the orchestration layer creates a deterministic neutral summary for that
  tool-only response;
- the proposal remains inert and still passes through the existing deterministic
  Supervisor before any tool can run;
- empty content with no tool proposal remains an error.

Regression coverage added for:
`content="" + ModelToolCall(read_repository, ...)`.

Corrected implementation head:
`00b17d498f90e3970352f6264584f8b1fdb60d53`

Validation on corrected head:
- deterministic suite: `47/47 PASS`
- generic CI: `PASS`
- strict exact-head CI: `PASS`

## Current acceptance state

A second local workstation smoke on the corrected/final documented head is still
required. Do not promote this Gate to accepted based only on CI.

Physical validation remains:
`PHYSICAL_NOT_EXECUTED`.


## Attempt 2 — Reviewer structured-output failure

Date: 2026-09-19

Repository head:
`7e20a4beaf617dfd118e4f7d1cb1c6ecc3e96942`

Observed result:
`FAIL_RUNTIME_CONTRACT`

The corrected Executor path advanced successfully through:
- Planner;
- Executor tool proposal;
- deterministic Supervisor evaluation;
- root-bounded read of `STATUS.md`;
- deterministic evidence collection.

The failure occurred only at Reviewer structured output. The local
`gpt-oss:20b / medium / 8192 / 2048` Reviewer response could not be parsed as
the required JSON object and raised:

`SemanticValidationError: REVIEWER returned invalid JSON`

This demonstrated a second orchestration robustness gap: malformed advisory model
output could escape the role loop as an uncaught Python exception.

### Correction

Gate 006 now treats structured role-output protocol failures as bounded,
non-authoritative failures:

- Planner and Reviewer structured responses receive at most one protocol-retry;
- the retry uses the same model and reasoning configuration and explicitly asks
  for exactly one JSON object matching the existing schema;
- schemas are not weakened;
- no alternate model is substituted;
- no model output can promote itself to PASS;
- retry exhaustion becomes deterministic terminal `FAIL`, not an uncaught
  traceback;
- malformed Executor structured output likewise becomes terminal `FAIL`;
- model audit summaries now record `done_reason`, response content length, and
  tool-call count for future diagnosis.

Corrected implementation head:
`0cb1756ebb8eb50ee4f45d883b42a0c14b1d2cca`

Validation on corrected head:
- deterministic suite: `50/50 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.

A further local workstation smoke is required. Physical validation remains
`PHYSICAL_NOT_EXECUTED`.


## Attempt 3 — successful end-to-end local runtime smoke

Date: 2026-09-19

Tested repository head:
`f3c434e630a10bbf016e28d6c873df4f79783c28`

Primary workstation/runtime:
- Windows 11 Pro;
- Ollama `0.34.1`, loopback-only;
- model `gpt-oss:20b`;
- reasoning `medium`;
- context `8192`;
- benchmark-equivalent max output `2048`.

Observed result:
`PASS`

User-captured machine output:

```json
{
  "state": "COMPLETE",
  "job_status": "PASS",
  "blocker": null,
  "revision_count": 0,
  "executed_actions": [
    "read_repository"
  ],
  "evidence_refs": [
    "sha256:STATUS.md:ac9f1cb5c40f9793a0342df00f7926b9b95af12e9f7e70b2f27b5710097b4b45"
  ],
  "review_decision": "ACCEPT",
  "model": "gpt-oss:20b",
  "reasoning": "medium",
  "context_tokens": 8192,
  "physical_validation": "PHYSICAL_NOT_EXECUTED"
}
```

Acceptance interpretation:
- Planner completed;
- Executor proposed only the bounded read action;
- deterministic Supervisor permitted the declared read;
- the smoke harness read exactly `STATUS.md`;
- deterministic SHA-256 evidence was produced;
- Reviewer returned `ACCEPT`;
- Supervisor-owned role loop reached `COMPLETE / PASS`;
- no repository write, Git mutation, unrestricted shell, project adapter, or
  additional authority was granted;
- this runtime smoke is advisory/control-plane validation only and does not
  constitute physical validation.

Physical validation remains:
`PHYSICAL_NOT_EXECUTED`.

The successful smoke satisfies the local runtime acceptance criterion for
Gate 006. Final acceptance still requires green CI on the final
documentation/evidence head and explicit human exact-SHA squash-merge approval.
