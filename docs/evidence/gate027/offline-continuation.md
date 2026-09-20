# Gate 027 — Offline continuation boundary evidence

## Gate identity
- Issue: #53
- PR: #54
- Branch: `gate-027-offline-continuation-boundary`
- Base: Gate 026 squash merge
  `d1d93c7a3c17ffbd1c4bd7d7820ca75d8f9bcc4d`
- Validated implementation/architecture checkpoint:
  `323b2db90c1470634ea816a4a96eb1f9dcc47ed9`

## Objective
Close the Phase 8 offline-continuation criterion at the Engineering AI
control-plane boundary for connected PlataVM and BuoyCalc project adapters.

The Gate makes process network requirements explicit and fail-closed. It does
not emulate an operating-system firewall and does not claim that arbitrary
project-owned script internals have been formally proven incapable of opening a
network connection.

## Process execution contract

Every `CommandSpec` now requires an explicit
`NetworkRequirement` value:
- `LOCAL_ONLY`
- `NETWORK_CAPABLE`

There is no implicit default classification.

When `AllowListedProcessRunner(..., offline=True)` receives a
`NETWORK_CAPABLE` command it raises `ToolAccessError` before executable
resolution or subprocess creation.

`LOCAL_ONLY` commands preserve the existing:
- fixed allow-list;
- fixed argv;
- root-bounded cwd;
- `shell=False`;
- timeout;
- bounded stdout/stderr;
- structured process result.

## PlataVM offline continuation

The two existing fixed PlataVM validator commands are explicitly
`LOCAL_ONLY`:
- `platavm.repository_integrity`
- `platavm.semantic_gates`

`PlataVMReadOnlyAdapter` and
`PlataVMControlledEngineeringLoop` accept `offline=True` and propagate that
state to the process boundary.

Gate 027 synthetic connected-project smoke proves:
- local governance/KiCad snapshot succeeds;
- local Git refs are sufficient;
- both fixed validators PASS in offline mode;
- controlled local worktree creation/validation/cleanup succeeds;
- primary repository HEAD/status remain unchanged;
- no remote mutation API is introduced.

The smoke uses a local bare Git origin only. No external Git remote is used.

## BuoyCalc offline continuation

Gate 027 classifies exactly these package-acquisition steps as
`NETWORK_CAPABLE`:
- `buoycalc.restore_app`
- `buoycalc.restore_engineering_regression`
- `buoycalc.restore_validation_601`

All fixed PowerShell/static checks and .NET steps already carrying
`--no-restore` or `--no-build` are classified `LOCAL_ONLY`.

When BuoyCalc validation is requested in offline mode and reaches a
network-capable restore step:
- the process runner blocks before execution;
- no process exit code exists;
- step evidence records `blocked=true`;
- `block_reason=OFFLINE_NETWORK_REQUIRED`;
- validation state is `BLOCKED_RUNTIME_PREREQUISITE`;
- the block is never reinterpreted as PASS.

The Gate 027 smoke also proves:
- BuoyCalc read-only governance/invariant snapshot succeeds from local state;
- controlled local worktree creation succeeds;
- network-capable restore is blocked before execution;
- primary repository HEAD/status remain unchanged;
- selected-shape and report-store scan profiles are classified local-only.

Actual local-only validator PASS still requires the ordinary local runtime and
already-present dependency/build prerequisites. Gate 027 does not fabricate PASS
when those prerequisites are absent.

## Deterministic regression

Checkpoint:
`323b2db90c1470634ea816a4a96eb1f9dcc47ed9`

Generic workflow:
- run `35537733809`
- conclusion: `PASS`

Strict exact-head workflow:
- run `35537733812`
- conclusion: `PASS`

Deterministic regression:
- `312/312 PASS`

Gate 027 offline continuation workflow:
- run `35537733811`
- Ubuntu job `106149668069`: `PASS`
- Windows job `106149668156`: `PASS`
- state: `PASS_OFFLINE_CONTINUATION_BOUNDARY`
- recorded external-network exercise: false
- BuoyCalc blocked reason: `OFFLINE_NETWORK_REQUIRED`

Inherited Gate 026 reproducible-install workflow:
- run `35537733819`
- Ubuntu job `106149668242`: `PASS`
- Windows job `106149668175`: `PASS`
- installed-package regression: `312/312 PASS`
- schema count: 14
- schemas loaded from source checkout: false
- repeated wheel SHA-256 match: true on each platform.

## Evidence semantics and limitations

`external_network_exercised=false` means the deterministic Gate 027 smoke uses
only local resources and does not intentionally invoke an external-network
operation. It is not packet-capture evidence and is not an OS-level proof that
an arbitrary third-party/project-owned script can never open a socket.

Gate 027 therefore guarantees the control-plane boundary:
commands known to be network-capable are denied before process creation in
offline mode. It does not weaken or reinterpret project validators.

## Authority boundaries
- remote Git fetch/pull/push: not granted by Gate 027;
- external model/API calls: not granted;
- package download while offline: blocked for classified steps;
- architecture authority: unchanged;
- physics authority: unchanged;
- validator weakening: not permitted;
- release authorization: `NOT_GRANTED`;
- fabrication authorization: `NOT_GRANTED`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

## Gate state
Implementation is `IMPLEMENTED_VALIDATED` on Ubuntu and Windows.

Final Gate acceptance remains pending:
1. documentation/evidence exact-head validation;
2. PR ready-for-review transition;
3. ready-state source-of-truth synchronization;
4. final exact-head validation;
5. explicit human exact-SHA squash-merge approval.
