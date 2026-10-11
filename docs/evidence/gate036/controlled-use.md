# Gate 036 — Real Connected-Project Controlled-Use Acceptance Evidence

## Scope

Gate 036 closes only the v1.0 criterion:

`successful controlled use on both PlataVM and BuoyCalc`.

It does not add a new project adapter, validator, model, tool authority, release
authority, fabrication authority or physical-validation authority.

Engineering AI base:
`d9ab48f50ef9e78c7fd7423cebadf39634c3de66`.

## Exact connected-project sources

PlataVM:
- repository: `Gonoboben/plataVM`;
- active Draft PR: `#100`;
- exact accepted Gate 036 source head:
  `840435615d0b3ebf5f1137f575cfd75b66501964`;
- project base main:
  `dcba77466d4800c0e7a336a2771684e066f845db`;
- active branch:
  `agent/pcb-e-aux-hardware-current-v1-9`.

BuoyCalc:
- repository: `Gonoboben/buoycalc-windows`;
- exact accepted Gate 036 source:
  `main@325aee5ee3a9f64413e416a1206fc4e296d9723f`;
- Draft PR #628 is explicitly outside the Gate 036 primary baseline.

## Existing authority reused unchanged

PlataVM:
- existing Gate 013 `PlataVMControlledEngineeringLoop`;
- fixed validators:
  - `platavm.repository_integrity`;
  - `platavm.semantic_gates`;
- adapter-owned local `engineering-ai/` worktree/branch only;
- no commit/push/open-PR/merge/fabrication/release API.

BuoyCalc:
- existing Gate 015 `BuoyCalcControlledEngineeringLoop`;
- fixed validation profiles:
  - `buoycalc.dotnet_build`;
  - `buoycalc.selected_shape_consumer_scan`;
  - `buoycalc.report_store_consumer_scan`;
  - `buoycalc.validation_601`;
- adapter-owned local `engineering-ai/buoycalc/` worktree/branch only;
- no commit/push/open-PR/merge/release/physics API.

## Gate 036 harness

`scripts/gate036_real_connected_project_controlled_use.py`

The real harness:
1. requires explicit `--approve-worktrees`;
2. verifies the exact approved source revision before worktree creation;
3. verifies the expected primary branch and origin/main relationship;
4. refuses PlataVM execution while an authoritative source conflict remains;
5. verifies BuoyCalc runtime prerequisites before controlled validation;
6. creates disposable adapter-owned worktrees;
7. executes only the existing fixed validators/profiles;
8. records bounded deterministic evidence;
9. cleans the disposable worktree/branch;
10. verifies the primary checkout is byte/Git-state identical before/after;
11. performs no connected-project remote mutation.

No project file patch is required merely to manufacture Gate evidence. Gate 036
tests the accepted controlled validation path against real project state rather
than introducing a fake engineering change.

## Deterministic acceptance evaluator

The harness contains a fail-closed evaluator. It rejects, at minimum:
- non-real/synthetic execution as final Gate evidence;
- wrong PlataVM PR head/base/active branch;
- PlataVM source conflicts;
- missing or failed PlataVM validators;
- failed cleanup or primary-repository drift;
- missing PlataVM package/fabrication/physical/series barriers;
- wrong or dirty BuoyCalc main;
- BuoyCalc runtime-prerequisite blockers;
- missing or failed fixed profiles;
- tracked-state mutation;
- cleanup failure;
- release-state promotion;
- missing project `NOT READY` marker;
- physical-validation promotion;
- any declared remote connected-project mutation attempt.

CI self-tests are explicitly synthetic contract tests and cannot satisfy real
Gate 036 acceptance.

## Remediation checkpoint

The first primary-workstation exercise exposed two bounded portability/cleanup
defects without changing either connected project's primary checkout:

- PlataVM's PCB-E auxiliary validator compared repository-relative manifest
  paths using the host-native separator. On Windows the same canonical path was
  rendered with backslashes and failed three exact string contracts. The
  owner-authorized PR #100 remediation changes only repository-relative path
  canonicalization to POSIX form and adds regression coverage. The remediated
  Draft PR #100 exact head is
  `840435615d0b3ebf5f1137f575cfd75b66501964`.
- BuoyCalc deterministic validation reached
  `READY_FOR_HUMAN_APPROVAL`, but disposable worktree cleanup encountered an
  already-deregistered Windows filesystem residue with `WinError 32`.
  Gate 036 therefore adds bounded retry/backoff for the already-verified
  adapter-owned disposable path plus transient/persistent-lock regressions.
  Persistent locking still fails closed with `ToolExecutionError`.

These remediations do not expand model/tool/project authority and do not change
PlataVM physics, engineering contracts, validator allowlists, release,
fabrication or physical states. Final Gate 036 acceptance still requires a new
real primary-workstation run against the exact revisions above.

## 2026-10-11 real Windows acceptance / cleanup evidence

The explicitly authorized primary-workstation Gate 036 exercise ran against
Engineering AI `b463eb0d7216c3ba9ae0241d1f261c4f731e3584`, PlataVM
`840435615d0b3ebf5f1137f575cfd75b66501964`, and BuoyCalc main
`325aee5ee3a9f64413e416a1206fc4e296d9723f`.

- PlataVM: both fixed validators PASS; worktree/branch cleanup PASS.
- BuoyCalc: all four fixed profiles / 23 steps PASS, tracked state unchanged.
- BuoyCalc cleanup: FAIL after Git had deregistered the disposable worktree;
  its directory remained with Windows `WinError 32` and the controlled branch
  remained at the exact base SHA. Overall Gate 036 exit code 1 / BLOCKED.
- The primary checkouts and Gate 035 worktree remained unchanged.
- A separately authorized manual recovery later verified the disposable
  directory was empty and not a reparse point, that Git had deregistered the
  worktree, and that its branch still equaled the expected base SHA. Only this
  empty directory and exact disposable branch were then removed successfully.
  Manual recovery does not retrospectively change the failed acceptance.

Root cause of the Windows handle retention is unproven: no holding handle was
found by Resource Monitor later. The existing synthetic transient/persistent
lock tests do not exercise a real Windows directory handle. The owner approved
bounded cleanup-attempt diagnostics and an isolated real Win32 handle regression
inside existing Draft PR #75. This adds no new tool permissions or validator
allowlists, and does not change release/fabrication/physical authority.

The remediation captures bounded diagnostic events from the Git remove and
filesystem fallback stages in the Gate 036 JSON evidence (including attempts,
latency, exit status, and OS error numbers). The Windows regression acquires a
real no-FILE_SHARE_DELETE directory handle in a separate process and verifies
fail-closed behavior while held and removability after release. It does not
establish the process responsible for the historical failure.

The new instrumentation and regression still require hosted CI review. No
second real Gate 036 execution, approval for release, or merge is authorized.

## Current state

`REAL_PRIMARY_WORKSTATION_REEXECUTION_REQUIRED_AFTER_CLEANUP_DIAGNOSTICS`.

No real Gate 036 PASS is claimed yet.

The next acceptance action is to run the Gate 036 harness on the primary
workstation with:
- PlataVM checkout clean on
  `agent/pcb-e-aux-hardware-current-v1-9@840435615d0b3ebf5f1137f575cfd75b66501964`;
- BuoyCalc checkout clean on
  `main@325aee5ee3a9f64413e416a1206fc4e296d9723f`;
- explicit human approval for disposable worktree creation.

PlataVM PR #100 GitHub CI remains separate evidence. Existing cancelled PR #100
workflow conclusions are not reinterpreted as PASS by Gate 036.

BuoyCalc project release status remains `NOT READY FOR v1.0`.

Release authorization remains `NOT_GRANTED`.
Fabrication authorization remains `NOT_GRANTED`.
Physical validation remains `PHYSICAL_NOT_EXECUTED`.
