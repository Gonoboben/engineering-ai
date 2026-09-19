# Gate 013 — PlataVM Controlled Engineering Loop Evidence

## Scope

Gate 013 adds controlled local branch/worktree writes for PlataVM on top of the
accepted Gate 012 strict read-only adapter.

It does not grant commit, push, pull-request, merge, fabrication, release,
architecture, physics, or validator-weakening authority.

Physical validation remains:
`PHYSICAL_NOT_EXECUTED`.

## Accepted control model

The controlled loop is:

1. read authoritative project state;
2. surface any governance/source conflict;
3. stop before write when an authoritative conflict exists;
4. otherwise create an isolated adapter-owned local Git worktree;
5. require an `engineering-ai/` branch prefix;
6. require an explicitly allow-listed target path;
7. require exact `expected_sha256` match against current file content;
8. apply one bounded existing-file replacement inside the isolated worktree;
9. capture the Git diff;
10. run the fixed PlataVM validators;
11. return `READY_FOR_HUMAN_APPROVAL` only when validators PASS.

A successful controlled write loop does not imply project PASS, release,
fabrication readiness, or physical validation.

## Project policy

Profile:
`profiles/platavm-controlled.json`

Policy:
`profiles/platavm-controlled-policy.json`

Autonomous:
- `read_repository`;
- `run_validator`;
- `propose_patch`.

Human approval required:
- `write_worktree`.

Forbidden:
- `local_commit`;
- `push_remote`;
- `open_pr`;
- `merge_pr`;
- `architecture_change`;
- `physics_change`;
- `validator_weakening`;
- fabrication/release authorization;
- destructive action;
- scope expansion;
- external disclosure.

The existing Supervisor/PolicyEngine is reused unchanged. Gate 013 does not
expand Supervisor authority.

## Controlled worktree adapter

Implementation:
`src/engineering_ai/tools/worktree.py`

Properties:
- primary repository must be clean before worktree creation;
- branch must match the fixed `engineering-ai/` prefix;
- worktree path is constrained under a configured parent;
- only adapter-created sessions may be written;
- replacement target must already exist;
- target must be explicitly allow-listed;
- absolute paths, parent escape and unsafe relative paths are rejected;
- symlink targets are rejected;
- proposed before-content is bound by exact lowercase SHA-256;
- stale SHA rejects before mutation;
- maximum replacement size is bounded;
- write uses a temporary file and atomic `os.replace`;
- post-write Git diff is captured;
- no generic Git or shell API is exposed.

Cleanup is allowed only for an adapter-created worktree that is clean and still
at its original base SHA. The adapter-created branch is deleted only when it
still points exactly to the original base SHA, proving no unique commit exists.

## PlataVM controlled wrapper

Implementation:
`src/engineering_ai/projects/platavm_controlled.py`

States:
- `BLOCKED_SOURCE_CONFLICT`;
- `WORKTREE_READY`;
- `PATCH_APPLIED`;
- `VALIDATION_FAILED`;
- `READY_FOR_HUMAN_APPROVAL`.

Before worktree creation the wrapper reuses the accepted Gate 012 read-only
snapshot and conflict detection.

When source conflicts exist, the result is
`BLOCKED_SOURCE_CONFLICT` and no worktree is created.

Validation reuses exactly:
- `platavm.repository_integrity`;
- `platavm.semantic_gates`.

Any validator failure prevents `READY_FOR_HUMAN_APPROVAL`.

## Real PlataVM constraint inherited from Gate 012

Current real PlataVM source state contains a governance conflict:

- `Docs/PROJECT_STATUS.md` declares confirmed main
  `c9703c58486eb5efe6a1d1d3e1bbf37815cd2a65`;
- local/remote main observed in Gate 012:
  `dcba77466d4800c0e7a336a2771684e066f845db`.

Engineering AI `AGENTS.md` requires authoritative-source conflict to stop
execution rather than silently reconcile it.

Therefore Gate 013 must not exercise a real PlataVM file write while this
conflict remains unresolved.

The write capability is validated on synthetic Git fixture repositories.
The real PlataVM local smoke is expected to prove deterministic
`BLOCKED_SOURCE_CONFLICT` before any worktree or file mutation.

## Deterministic regression

Implementation head:
`9574f44c37189205ba8577096ce08b9dd893642f`

Result:
- deterministic tests: `119/119 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- exact revision verification: `PASS`.

Validated synthetic-fixture boundaries:
- controlled patch/write/validate/restore/cleanup path PASS;
- primary checkout remains unchanged;
- worktree branch prefix enforcement PASS;
- dirty primary repository blocks creation;
- stale SHA rejects before mutation;
- disallowed target rejects;
- path escape rejects;
- validator failure blocks ready state;
- source conflict blocks before worktree creation;
- controlled adapter exposes no commit/push/open_pr/merge API;
- policy schema validates;
- `write_worktree` requires explicit human approval in PolicyEngine;
- commit/push/open_pr/merge actions are denied.

## Remaining acceptance item

Run `scripts/gate013_platavm_controlled_smoke.py` against the real local
`C:\workspace\repos\plataVM` checkout on a stable Gate 013 exact head.

Expected current result:
- `BLOCKED_SOURCE_CONFLICT`;
- at least one source conflict;
- `worktree_created=false`;
- repository HEAD/status unchanged;
- no remote mutation attempted;
- `PHYSICAL_NOT_EXECUTED`.

This real-project block is the correct Gate 013 behavior until PlataVM
authoritative governance is synchronized in a separately controlled PlataVM
Gate.


## Real PlataVM primary-workstation policy-block smoke

The Gate 013 real-project smoke completed on the primary Windows workstation.

Engineering AI Gate 013 head at smoke:
`a7f4fda9a487733711248d684d1107f5a0b59e76`.

Observed PlataVM repository:
- path: `C:\workspace\repos\plataVM`;
- before HEAD: `dcba77466d4800c0e7a336a2771684e066f845db`;
- before status: `## main...origin/main`;
- after HEAD: `dcba77466d4800c0e7a336a2771684e066f845db`;
- after status: `## main...origin/main`;
- repository_unchanged: `true`.

Detected source conflict:
`PROJECT_STATUS declared main c9703c58486eb5efe6a1d1d3e1bbf37815cd2a65 != origin/main dcba77466d4800c0e7a336a2771684e066f845db`.

Controlled-loop result:
- state: `BLOCKED_SOURCE_CONFLICT`;
- worktree_created: `false`;
- remote_mutation_attempted: `false`;
- physical_validation: `PHYSICAL_NOT_EXECUTED`;
- process exit: `0`.

This is the required Gate 013 safety result for the current real PlataVM state.
The authoritative source conflict stopped the controlled loop before any
worktree creation or file mutation.

No PlataVM file, branch, commit, PR, CI run, release/fabrication state, or
physical state was changed.

Final real-project smoke classification:
`PASS_POLICY_BLOCK_BEFORE_MUTATION`.
