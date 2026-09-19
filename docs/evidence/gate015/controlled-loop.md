# Gate 015 — BuoyCalc Controlled Engineering Loop Evidence

## Scope

Gate 015 adds bounded isolated-worktree modification plus fixed
build/test/validation execution for BuoyCalc.

It does not authorize:
- calculation-core/physics changes;
- governance changes;
- commit/push/open PR/merge in BuoyCalc;
- RC packaging/publish;
- release-candidate branch mutation;
- tag/GitHub Release;
- physical validation.

Physical validation remains:
`PHYSICAL_NOT_EXECUTED`.

Release remains:
`NOT_AUTHORIZED_REQUIRES_EXPLICIT_MANUAL_WINDOWS_RC_SMOKE`.

## Accepted base

Engineering AI base:
Gate 014 squash merge
`0f7ec3c01829f9c193e5730ec5144eee77c00b52`.

BuoyCalc real baseline observed by Gate 014:
`main@0db1e7cc17e309fc1402fe58b265d2e95c2d4d39`.

## Controlled worktree contract

The primary BuoyCalc checkout must satisfy all of:
- branch `main`;
- clean Git-visible state;
- `HEAD == origin/main`;
- all Gate 014 frozen invariant markers PASS.

A controlled worktree:
- is adapter-created;
- uses fixed prefix `engineering-ai/buoycalc/`;
- starts from exact explicit base ref;
- never changes the primary checkout worktree.

Patch application additionally requires:
- explicit target allow-list;
- exact lowercase SHA-256 of current content;
- existing regular-file target;
- no path escape;
- no symlink target.

Gate 015 ordinary patch policy rejects:
- `GOVERNANCE`;
- `CALCULATION_CORE_CANDIDATE`.

These paths require separately approved architecture/physics work and are not
available through ordinary Gate 015 writes.

## Fixed validation profiles

Profile `buoycalc.dotnet_build` mirrors the accepted BuoyCalc .NET Build path:
- restore app;
- restore engineering regression package;
- Release build;
- report-builder / technical-report / selected-report boundary checks;
- v1 release-freeze and RC-packaging static checks;
- read-model and typed-user-report/PDF checks;
- RC smoke static regression scripts;
- repository-governance check;
- report-store and selected-shape consumer-map checks;
- engineering regression baseline verification.

Profile `buoycalc.selected_shape_consumer_scan`:
- fixed PowerShell `tools/scan-selected-shape-consumers.ps1`.

Profile `buoycalc.report_store_consumer_scan`:
- fixed PowerShell `tools/scan-report-store-consumers.ps1`.

Profile `buoycalc.validation_601`:
- restore PhysicalRejectionValidation package;
- Release build;
- run fixed physical-rejection validation matrix into
  `artifacts/validation-601-physical-rejection`.

Every command is a fixed `CommandSpec` executed with `shell=False`.
No publish/package/verify RC script, tag, release or generic shell profile exists.

## Structured validator evidence

For every executed step Gate 015 records:
- fixed step ID;
- exit code;
- timeout state;
- output truncation state;
- SHA-256 of bounded stdout;
- SHA-256 of bounded stderr;
- validation class `SOFTWARE_DETERMINISTIC`.

Model statements are not validator evidence.

Before and after the suite the loop captures:
- HEAD;
- tracked worktree diff;
- cached diff.

A validator changing tracked state blocks readiness even if its process exits 0.

Successful validation returns only:
`READY_FOR_HUMAN_APPROVAL`.

It never promotes:
- release authorization;
- physical validation;
- solver/physics maturity.

## Disposable generated-artifact cleanup

BuoyCalc does not expose a root .gitignore through the current repository
baseline. Build/test runs may therefore create untracked bin/obj/artifacts in a
disposable worktree.

Gate 015 adds a guarded cleanup path for adapter-owned disposable worktrees.
Forced removal is permitted only when:
- worktree HEAD still equals original base SHA;
- tracked worktree diff is empty;
- cached diff is empty.

This may discard generated untracked build artifacts in the disposable
worktree. It cannot discard tracked changes or unique commits.

The normal Gate 013 strict-clean cleanup remains unchanged.

## Policy

Autonomous:
- read_repository;
- run_validator;
- propose_patch.

Human approval required:
- write_worktree.

Forbidden:
- run_calculation as an unrestricted action;
- run_simulation;
- local_commit;
- push_remote;
- open_pr;
- merge_pr;
- architecture_change;
- physics_change;
- validator_weakening;
- fabrication_authorization;
- release_authorization;
- external_disclosure;
- destructive project action;
- scope expansion.

## Deterministic implementation validation

Validated implementation head:
`b40baea3294474fafa26936e06b0fa5c7d69ea86`.

Result:
- deterministic tests: `143/143 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`;
- exact revision verification: `PASS`.

Regression coverage includes:
- clean aligned main prerequisite;
- branch prefix enforcement;
- non-core controlled patch/restore/cleanup;
- governance patch rejection;
- calculation-core/solver patch rejection;
- stale SHA rejection before mutation;
- explicit target allow-list;
- validator FAIL blocks readiness;
- validator tracked mutation blocks readiness;
- unknown validator profile rejection;
- fixed profiles exclude publish/package/release commands;
- disposable generated-untracked cleanup succeeds only with clean tracked state;
- disposable cleanup rejects tracked changes;
- no remote/release mutation API;
- policy schema and write-worktree human approval boundary;
- smoke missing-checkout structured state;
- smoke refuses worktree creation without explicit `--approve-worktree`.

## Remaining acceptance

1. stable-head generic and strict exact-head CI after evidence/status synchronization;
2. real primary-workstation smoke using explicit `--approve-worktree`;
3. prove full fixed suite PASS or preserve exact failure evidence;
4. prove primary BuoyCalc checkout unchanged;
5. prove disposable worktree/branch cleanup;
6. final acceptance-state exact-head CI and explicit human squash-merge approval.


## Real primary-workstation smoke attempt 1 — runtime prerequisite block

The first real Gate 015 smoke ran against:

`C:\workspace\repos\buoycalc-windows`

Observed primary repository:
- branch: `main`;
- HEAD: `0db1e7cc17e309fc1402fe58b265d2e95c2d4d39`;
- `origin/main`: same SHA;
- dirty: `false`;
- before/after status: `## main...origin/main`;
- repository_unchanged: `true`.

The disposable worktree was created and then safely removed after validation
startup failed because the local runtime could not resolve `dotnet`.

Observed result:
- state: `VALIDATION_EXECUTION_ERROR`;
- execution_error:
  `ToolExecutionError: allow-listed executable not found: dotnet`;
- worktree_removed: `true`;
- branch_removed: `true`;
- cleanup_state: `PASS_AFTER_EXECUTION_ERROR`;
- profiles: none executed;
- release_state: `NOT_AUTHORIZED`;
- physical_validation: `PHYSICAL_NOT_EXECUTED`;
- process exit: `1`.

Classification:
`INFRASTRUCTURE_PREREQUISITE_BLOCK`.

This is not a BuoyCalc engineering-validation failure. No build/test/validation
profile ran, and no BuoyCalc source, tracked state, release state, or physical
state changed.

### Corrective control change

Gate 015 now performs a deterministic runtime-prerequisite check before
worktree creation.

It resolves:
- `dotnet` from PATH, with a Windows fallback to
  `%ProgramFiles%\dotnet\dotnet.exe`;
- `pwsh` from PATH, with a Windows fallback to
  `%ProgramFiles%\PowerShell\7\pwsh.exe`.

It also runs fixed `dotnet --list-sdks` and requires at least one .NET 8 SDK.

If requirements are missing, the smoke returns:
`BLOCKED_RUNTIME_PREREQUISITE`
before creating a worktree.

Corrected runtime-preflight head:
`b6a490377f98cbe5d063e2a7460a977309507fe1`.

Validation:
- deterministic tests: `144/144 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.

A second real smoke is required.


## Real primary-workstation smoke attempt 2 — prerequisite preflight block

The corrected Gate 015 smoke reran on the real BuoyCalc checkout after runtime
preflight was added.

Observed primary repository:
- branch: `main`;
- HEAD: `0db1e7cc17e309fc1402fe58b265d2e95c2d4d39`;
- `origin/main`: same SHA;
- dirty: `false`;
- before/after status: `## main...origin/main`;
- repository_unchanged: `true`.

Preflight result:
- state: `BLOCKED_RUNTIME_PREREQUISITE`;
- dotnet_executable: `null`;
- pwsh_executable: `null`;
- dotnet_sdk8_available: `false`;
- dotnet_sdks: empty;
- blockers:
  - `dotnet executable not found`;
  - `pwsh executable not found`;
- process exit: `4`.

The corrected preflight blocked before worktree creation and before any
build/test/validation execution.

Release remained:
`NOT_AUTHORIZED`.

Physical validation remained:
`PHYSICAL_NOT_EXECUTED`.

Classification:
`RUNTIME_PREREQUISITE_MISSING`.

Required local prerequisites before smoke attempt 3:
- Microsoft .NET 8 SDK;
- PowerShell 7 (`pwsh`).

No BuoyCalc engineering failure is recorded because no validation profile ran.


## Real primary-workstation smoke attempt 3 — validation PASS, cleanup recovery required

The third real Gate 015 smoke ran after .NET 8 SDK and PowerShell 7 were made
available locally.

Observed primary BuoyCalc repository:
- branch: `main`;
- HEAD: `0db1e7cc17e309fc1402fe58b265d2e95c2d4d39`;
- `origin/main`: same SHA;
- dirty: `false`;
- before/after status: `## main...origin/main`;
- repository_unchanged: `true`.

Validation result:
- state: `READY_FOR_HUMAN_APPROVAL`;
- all fixed profiles passed:
  - `buoycalc.dotnet_build`: PASS;
  - `buoycalc.selected_shape_consumer_scan`: PASS;
  - `buoycalc.report_store_consumer_scan`: PASS;
  - `buoycalc.validation_601`: PASS;
- all recorded steps returned exit code 0;
- no step timed out;
- no output was truncated;
- all evidence was classified `SOFTWARE_DETERMINISTIC`;
- `tracked_state_unchanged=true`;
- release state:
  `NOT_AUTHORIZED_REQUIRES_EXPLICIT_MANUAL_WINDOWS_RC_SMOKE`;
- physical validation:
  `PHYSICAL_NOT_EXECUTED`.

Cleanup result:
- worktree_removed: `false`;
- branch_removed: `false`;
- cleanup_state:
  `FAIL: ToolExecutionError: git disposable worktree remove failed: Permission denied`;
- process exit: `1`.

Disposable objects left for guarded recovery:
- branch:
  `engineering-ai/buoycalc/gate015-smoke-0db1e7cc17e3`;
- worktree:
  `C:\Users\wasd8\AppData\Local\Temp\engineering-ai-gate015-buoycalc-h_kcvqpw\gate015-0db1e7cc17e3`;
- base SHA:
  `0db1e7cc17e309fc1402fe58b265d2e95c2d4d39`.

Classification:
`PASS_SOFTWARE_VALIDATION_WITH_CLEANUP_INFRASTRUCTURE_BLOCK`.

This is not a BuoyCalc engineering validation failure. All controlled software
validators passed and tracked project state remained unchanged. Gate acceptance
remains blocked only until the stale disposable worktree/branch is safely
removed.

### Windows cleanup hardening

The disposable cleanup path now:
1. retries fixed `git worktree remove --force` three times;
2. if Windows still returns Permission denied, uses a guarded filesystem
   fallback only after proving HEAD==base and both tracked/cached diffs empty;
3. runs fixed `git worktree prune --expire now`;
4. deletes the controlled branch only when it still points exactly to base SHA.

A dedicated recovery harness was added for already-left Gate 015 disposable
worktrees. It verifies registered worktree identity, controlled branch prefix,
base SHA and clean tracked state before deletion.

Hardened cleanup head:
`87354398cd745856d8ff89798b5527e51477641c`.

Validation:
- deterministic tests: `145/145 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.


## Stale-worktree recovery attempt 1 — already deregistered

The first guarded recovery run returned:

`REFUSED: worktree is not registered by Git`.

Post-run primary repository evidence:
- `main@0db1e7cc17e309fc1402fe58b265d2e95c2d4d39`;
- status: `## main...origin/main`;
- `git worktree list` showed only:
  `C:/workspace/repos/buoycalc-windows 0db1e7c [main]`.

Interpretation:
Git had already removed the disposable worktree registration during the prior
cleanup attempt even though Windows filesystem deletion had failed.

Recovery harness was tightened to support this exact state:
- exact worktree identity must be
  `gate015-<base[:12]>`;
- exact branch identity must be
  `engineering-ai/buoycalc/gate015-smoke-<base[:12]>`;
- controlled branch must still point exactly to base SHA;
- primary repository snapshot must remain unchanged;
- registered-worktree cleanup remains fully guarded;
- if Git has already deregistered the exact smoke worktree, only residual
  filesystem cleanup plus controlled branch deletion is permitted.

Corrected recovery head:
`d8405894bfb9152256e28ca49678f27ed8a2471d`.

Validation:
- deterministic tests: `147/147 PASS`;
- generic CI: `PASS`;
- strict exact-head CI: `PASS`.

No full BuoyCalc validation rerun is required.
