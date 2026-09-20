from __future__ import annotations

import importlib.metadata
import json
import platform
import sys


def version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "NOT_INSTALLED"


def main() -> int:
    payload = {
        "gate": "026",
        "mode": "INSTALL_TOOLCHAIN_MEASUREMENT",
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "pip": version("pip"),
        "setuptools": version("setuptools"),
        "wheel": version("wheel"),
        "engineering_ai": version("engineering-ai"),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if sys.version_info[:2] != (3, 12):
        raise SystemExit("Gate 026 requires Python 3.12")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
