# Engineering AI local installation

## Canonical Gate 026 installation contract

The accepted local-install baseline is Python **3.12.x**. Gate 026 validates the
same installation procedure on Ubuntu and Windows.

The canonical environment freezes:

### Install toolchain
- `packaging==26.3`
- `pip==26.2.1`
- `setuptools==84.0.0`
- `wheel==0.48.0`

### Runtime dependency closure
- `attrs==26.1.0`
- `jsonschema==4.26.0`
- `jsonschema-specifications==2025.9.1`
- `referencing==0.37.0`
- `rpds-py==2026.6.3`
- `typing-extensions==4.16.0`

The exact machine-readable lists are:
- `requirements/toolchain.lock`
- `requirements/runtime.lock`

## Preconditions
- a clean Git checkout of the exact Engineering AI revision to install;
- Git available on PATH;
- Python 3.12.x available;
- network/package-index access for dependency acquisition in Gate 026.

Gate 026 does **not** claim offline dependency acquisition. Offline continuation
is a separate Phase 8 / v1.0 criterion.

## Windows

From PowerShell in the repository root:

```powershell
py -3.12 scripts/bootstrap_reproducible.py --venv .venv
.\.venv\Scripts\python.exe -m pip check
```

For the full deterministic acceptance regression:

```powershell
py -3.12 scripts/bootstrap_reproducible.py --venv .venv --run-tests
```

Use a new venv path for each bootstrap attempt. The script deliberately refuses
to overwrite an existing environment.

## Ubuntu / POSIX

From the repository root:

```bash
python3.12 scripts/bootstrap_reproducible.py --venv .venv
./.venv/bin/python -m pip check
```

For the full deterministic acceptance regression:

```bash
python3.12 scripts/bootstrap_reproducible.py --venv .venv --run-tests
```

## What the bootstrap proves

The bootstrap:
1. requires a clean exact Git revision;
2. creates a fresh virtual environment;
3. installs the frozen toolchain;
4. installs the exact runtime dependency closure;
5. builds the Engineering AI wheel twice with a Git-derived
   `SOURCE_DATE_EPOCH`;
6. requires both wheel filenames and SHA-256 hashes to match;
7. installs the wheel non-editably with `--no-deps`;
8. runs `pip check`;
9. verifies installed versions and confirms `engineering_ai` is imported from
   the installed environment, not from `src/`;
10. optionally runs the full deterministic unittest regression.

A Gate 026 PASS establishes reproducibility of this defined software install
path for the recorded source revision and dependency/toolchain versions. It does
not establish offline availability, model availability, connected-project
availability, engineering correctness of a project, or physical validation.
