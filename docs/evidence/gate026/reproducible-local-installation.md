# Gate 026 — Reproducible local installation evidence

## Gate identity
- Issue: #51
- PR: #52
- Branch: `gate-026-reproducible-local-installation`
- Base: Gate 025 squash merge
  `171ff20125389d2d953576a0d3340c13dc1dc53f`
- Validated implementation head:
  `6c7bfbd9f8d07b96adeb3014b2071a4bc8a0793e`

## Objective
Close the first Phase 8 / v1.0 readiness criterion by defining and validating a
canonical local installation path that starts from a clean checkout, creates a
fresh Python environment, builds a non-editable wheel, installs exact dependency
versions, and runs the deterministic regression from the installed package.

Gate 026 does not claim offline continuation or offline dependency acquisition.

## Canonical contract

Python:
- `>=3.12,<3.13`

Frozen install toolchain:
- `packaging==26.3`
- `pip==26.2.1`
- `setuptools==84.0.0`
- `wheel==0.48.0`

Frozen runtime closure:
- `attrs==26.1.0`
- `jsonschema==4.26.0`
- `jsonschema-specifications==2025.9.1`
- `referencing==0.37.0`
- `rpds-py==2026.6.3`
- `typing-extensions==4.16.0`

Machine-readable locks:
- `requirements/toolchain.lock`
- `requirements/runtime.lock`

Canonical procedure:
- `scripts/bootstrap_reproducible.py`
- `INSTALL.md`

## What the bootstrap validates
For the exact checked-out revision, the bootstrap:
1. requires Python 3.12.x and a clean Git working tree;
2. creates a new virtual environment and refuses an existing target path;
3. installs the exact frozen install toolchain;
4. installs the exact frozen runtime dependency closure;
5. derives `SOURCE_DATE_EPOCH` from Git HEAD;
6. builds the project wheel twice without build isolation;
7. requires repeated wheel filename and SHA-256 equality;
8. installs the wheel non-editably with `--no-deps`;
9. runs `pip check`;
10. verifies all expected installed dependency/tool versions;
11. verifies `engineering_ai` imports from the installed environment, not
    `src/`;
12. verifies all 14 authoritative JSON Schema documents are installed with the
    wheel and are not being resolved from the source checkout;
13. runs the full deterministic unittest regression.

## Measured toolchain
Gate 026 first measured the upgraded install toolchain independently on both
GitHub-hosted platforms.

Ubuntu:
- Python `3.12.14`
- pip `26.2.1`
- setuptools `84.0.0`
- wheel `0.48.0`

Windows:
- Python `3.12.10`
- pip `26.2.1`
- setuptools `84.0.0`
- wheel `0.48.0`

The common contract therefore freezes Python at the 3.12 minor line rather than
an OS-specific patch release.

## Packaging defects exposed and corrected
The non-editable install path found issues that the earlier editable development
install did not expose:

1. JSON Schema files were repository data but were absent from the wheel.
   Gate 026 packages the authoritative `schemas/*.schema.json` set as wheel
   data and resolves installed schemas from the installed environment.

2. A failed `DecisionEvidenceMemory` constructor could leave an SQLite handle
   open if schema-version initialization failed. The constructor now closes the
   connection before re-raising.

3. Synthetic controlled-worktree tests assumed LF bytes. Windows Git worktrees
   may use CRLF, so exact-byte preconditions and rollback tests now hash and
   restore the actual prepared worktree bytes. Production exact-byte stale-patch
   protection was not weakened.

4. The allow-listed process runner timeout path used `Popen.kill()+wait()`.
   Windows could retain the timed-out process current-directory handle long
   enough to block deterministic temporary-directory cleanup. The runner now
   uses the standard-library `subprocess.run(..., timeout=...)` lifecycle,
   preserving the allow-list, `shell=False`, timeout and bounded-output
   boundaries while ensuring the child is fully reaped.

## Successful cross-platform acceptance

Implementation head:
`6c7bfbd9f8d07b96adeb3014b2071a4bc8a0793e`

Generic workflow:
- run `35535616430`
- state: `PASS`
- exact recorded head: `6c7bfbd9f8d07b96adeb3014b2071a4bc8a0793e`

Strict exact-head workflow:
- run `35535616425`
- state: `PASS`
- exact recorded head: `6c7bfbd9f8d07b96adeb3014b2071a4bc8a0793e`

Gate 026 install workflow:
- run `35535616417`
- Ubuntu job `106143992491`: `PASS`
- Windows job `106143992637`: `PASS`

Ubuntu installed-package acceptance:
- Python `3.12.14`
- `PASS_REPRODUCIBLE_INSTALLED_ENVIRONMENT`
- `PASS_REPRODUCIBLE_LOCAL_INSTALL`
- `pip check`: PASS
- installed schema count: 14
- schemas loaded from source repository: false
- deterministic regression: `306/306 PASS`
- repeated wheel SHA-256:
  `39f7487743ff430a31aee64beb3502a77b8cf59c436433cdc08b4bb525f6e567`

Windows installed-package acceptance:
- Python `3.12.10`
- `PASS_REPRODUCIBLE_INSTALLED_ENVIRONMENT`
- `PASS_REPRODUCIBLE_LOCAL_INSTALL`
- `pip check`: PASS
- installed schema count: 14
- schemas loaded from source repository: false
- deterministic regression: `306/306 PASS`
- repeated wheel SHA-256:
  `76149e3072ec45505f70b8e1f27df9683dd57e95797a8cf96e065db5ce55108a`

Each platform produced the same wheel SHA-256 on two consecutive builds for the
same checkout and frozen toolchain. Ubuntu and Windows wheel SHA-256 values are
not equal to each other. Gate 026 therefore claims deterministic repeated build
identity within each validated platform, not byte-identical cross-platform
wheel artifacts.

## Authority and scope boundaries
- architecture authority: unchanged;
- model/routing authority: unchanged;
- Supervisor permission authority: unchanged;
- validators/tests: not weakened;
- package publication: `NOT_RUN / OUT_OF_SCOPE`;
- offline dependency acquisition: `NOT_CLAIMED_GATE_026`;
- offline continuation of connected projects: `NOT_CLAIMED_GATE_026`;
- fabrication authorization: `NOT_GRANTED`;
- release authorization: `NOT_GRANTED`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

## Gate state
The implementation acceptance path is `IMPLEMENTED_VALIDATED` on Ubuntu and
Windows. Final Gate acceptance remains pending explicit human exact-SHA
squash-merge approval after the documentation/ready-state exact-head checks.
