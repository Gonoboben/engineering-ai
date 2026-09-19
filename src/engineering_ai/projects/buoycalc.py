"""Strict read-only adapter for BuoyCalc Windows engineering boundaries."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from engineering_ai.tools import (
    GitReadOnlyAdapter,
    ReadOnlyFilesystemAdapter,
    ToolExecutionError,
)


REQUIRED_GOVERNANCE_FILES = (
    "AGENTS.md",
    "docs/OPTIMIZATION_PLAN.md",
    "RELEASE.md",
)

GOVERNANCE_REQUIRED_CHECKS = (
    ".NET Build",
    "Selected Shape Consumer Scan",
    "Report Store Consumer Scan",
)

RELEASE_REQUIRED_CHECKS = (
    ".NET Build",
    "Selected Shape Consumer Scan",
    "Report Store Consumer Scan",
    "BuoyCalc Validation 601 Main Gate",
    "BuoyCalc Windows Build: success",
)

RELEASE_STATE = "NOT_AUTHORIZED_REQUIRES_EXPLICIT_MANUAL_WINDOWS_RC_SMOKE"

_INVARIANT_MARKERS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "physics-domain-authority",
        "docs/OPTIMIZATION_PLAN.md",
        ("Engineering physics lives only in the calculation/solver domain.",),
    ),
    (
        "presentation-is-renderer-only",
        "docs/OPTIMIZATION_PLAN.md",
        ("UI, PDF, 2D and report layers render calculated data",),
    ),
    (
        "selected-xz-primary-geometry",
        "AGENTS.md",
        ("The only user-facing geometry with engineering meaning is the selected calculated X/Z shape.",),
    ),
    (
        "segmentation-020m",
        "RELEASE.md",
        ("segmentation = 0.20 m",),
    ),
    (
        "signed-feedback-budget-64",
        "RELEASE.md",
        ("signed feedback budget = 64",),
    ),
    (
        "signed-weightwater-semantics",
        "RELEASE.md",
        ("signed WeightWaterKgM semantics = unchanged",),
    ),
    (
        "exact-deterministic-fixed-point",
        "RELEASE.md",
        ("Accepted signed candidate = exact deterministic fixed point",),
    ),
    (
        "renderers-presentation-only",
        "RELEASE.md",
        ("renderers = presentation only",),
    ),
    (
        "3d-post-v1",
        "RELEASE.md",
        ("3D = post-v1",),
    ),
    (
        "release-needs-manual-smoke",
        "RELEASE.md",
        ("Запрещено создавать git tag `v1.0.0` или GitHub Release",),
    ),
)


class BuoyCalcCIState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    CANCELLED = "CANCELLED"
    PENDING = "PENDING"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class SourceBoundaryClass(str, Enum):
    GOVERNANCE = "GOVERNANCE"
    CALCULATION_CORE_CANDIDATE = "CALCULATION_CORE_CANDIDATE"
    READ_MODEL_CONSUMER = "READ_MODEL_CONSUMER"
    PRESENTATION_CONSUMER = "PRESENTATION_CONSUMER"
    VALIDATION_OR_TOOLING = "VALIDATION_OR_TOOLING"
    OTHER = "OTHER"


@dataclass(frozen=True)
class GovernanceDocument:
    path: str
    sha256: str
    content: str


@dataclass(frozen=True)
class GitSnapshot:
    branch: str
    head_sha: str
    origin_main_sha: str | None
    dirty: bool
    status_text: str


@dataclass(frozen=True)
class InvariantCheck:
    invariant_id: str
    source_path: str
    markers: tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class SourceInventoryEntry:
    path: str
    boundary_class: SourceBoundaryClass


@dataclass(frozen=True)
class BuoyCalcReadOnlySnapshot:
    repository_root: str
    governance_documents: tuple[GovernanceDocument, ...]
    git: GitSnapshot
    invariant_checks: tuple[InvariantCheck, ...]
    invariant_violations: tuple[str, ...]
    source_inventory: tuple[SourceInventoryEntry, ...]
    governance_required_checks: tuple[str, ...]
    release_required_checks: tuple[str, ...]
    release_state: str
    physical_validation: str


def classify_ci_state(
    conclusion: str | None,
    *,
    status: str | None = None,
    present: bool = True,
) -> BuoyCalcCIState:
    if not present:
        return BuoyCalcCIState.MISSING

    normalized_status = (status or "").strip().lower()
    normalized = (conclusion or "").strip().lower()

    if normalized_status in {
        "queued",
        "in_progress",
        "waiting",
        "requested",
        "pending",
    }:
        return BuoyCalcCIState.PENDING
    if normalized == "success":
        return BuoyCalcCIState.PASS
    if normalized in {"failure", "timed_out", "action_required"}:
        return BuoyCalcCIState.FAIL
    if normalized in {"cancelled", "stale"}:
        return BuoyCalcCIState.CANCELLED
    return BuoyCalcCIState.UNKNOWN


class BuoyCalcReadOnlyAdapter:
    """Inspect BuoyCalc boundaries without any project mutation authority."""

    def __init__(
        self,
        repository_root: str | Path,
        *,
        git_executable: str = "git",
        max_read_bytes: int = 2_097_152,
        max_scan_entries: int = 10_000,
        max_scan_depth: int = 12,
    ) -> None:
        if max_scan_entries <= 0:
            raise ValueError("max_scan_entries must be positive")
        if max_scan_depth <= 0:
            raise ValueError("max_scan_depth must be positive")

        self._root = Path(repository_root).resolve(strict=True)
        if not self._root.is_dir():
            raise ValueError("repository_root must be a directory")

        self._filesystem = ReadOnlyFilesystemAdapter(
            self._root,
            max_read_bytes=max_read_bytes,
        )
        self._git = GitReadOnlyAdapter(
            self._root,
            git_executable=git_executable,
        )
        self._max_scan_entries = max_scan_entries
        self._max_scan_depth = max_scan_depth

    @property
    def root(self) -> Path:
        return self._root

    def governance_documents(self) -> tuple[GovernanceDocument, ...]:
        docs: list[GovernanceDocument] = []
        for path in REQUIRED_GOVERNANCE_FILES:
            if not self._filesystem.exists(path):
                raise ToolExecutionError(
                    f"mandatory BuoyCalc governance file missing: {path}"
                )
            content = self._filesystem.read_text(path)
            docs.append(
                GovernanceDocument(
                    path=path,
                    sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    content=content,
                )
            )
        return tuple(docs)

    def git_snapshot(self) -> GitSnapshot:
        branch = self._git.current_branch()
        head = self._git.head_sha()
        status = self._git.status()
        if not branch.ok or not head.ok or not status.ok:
            raise ToolExecutionError("unable to capture BuoyCalc Git snapshot")

        origin_main = self._git.ref_sha("origin/main")
        origin_main_sha = origin_main.stdout.strip() if origin_main.ok else None
        lines = tuple(line for line in status.stdout.splitlines() if line.strip())
        dirty = any(not line.startswith("## ") for line in lines)

        return GitSnapshot(
            branch=branch.stdout.strip(),
            head_sha=head.stdout.strip(),
            origin_main_sha=origin_main_sha,
            dirty=dirty,
            status_text=status.stdout,
        )

    def invariant_checks(
        self,
        governance_documents: tuple[GovernanceDocument, ...] | None = None,
    ) -> tuple[InvariantCheck, ...]:
        docs = governance_documents or self.governance_documents()
        by_path = {doc.path: doc.content for doc in docs}
        checks: list[InvariantCheck] = []
        for invariant_id, source_path, markers in _INVARIANT_MARKERS:
            content = by_path[source_path]
            checks.append(
                InvariantCheck(
                    invariant_id=invariant_id,
                    source_path=source_path,
                    markers=markers,
                    passed=all(marker in content for marker in markers),
                )
            )
        return tuple(checks)

    def source_inventory(self) -> tuple[SourceInventoryEntry, ...]:
        tracked = self._git.tracked_files()
        if not tracked.ok:
            raise ToolExecutionError("unable to enumerate BuoyCalc tracked files")

        paths = tuple(
            line.strip()
            for line in tracked.stdout.splitlines()
            if line.strip()
        )
        if len(paths) > self._max_scan_entries:
            raise ToolExecutionError(
                "BuoyCalc source inventory exceeded max_scan_entries"
            )

        inventory = tuple(
            SourceInventoryEntry(
                path=path,
                boundary_class=self.classify_path(path),
            )
            for path in paths
            if self._interesting_file(path)
        )
        return tuple(sorted(inventory, key=lambda item: item.path.casefold()))

    @staticmethod
    def classify_path(relative_path: str) -> SourceBoundaryClass:
        normalized = relative_path.replace("\\", "/").casefold()
        name = Path(normalized).name

        if normalized in {
            "agents.md",
            "release.md",
            "docs/optimization_plan.md",
        }:
            return SourceBoundaryClass.GOVERNANCE

        if (
            "/views/" in f"/{normalized}"
            or "/presentation/" in f"/{normalized}"
            or "pdf" in name
            or "renderer" in name
            or "report" in name
            or "mainwindow" in name
        ):
            return SourceBoundaryClass.PRESENTATION_CONSUMER

        if (
            "/readmodels/" in f"/{normalized}"
            or "readmodel" in name
            or "selectedshapeprovider" in name
        ):
            return SourceBoundaryClass.READ_MODEL_CONSUMER

        if (
            normalized.startswith("tools/")
            or normalized.startswith("scripts/")
            or normalized.startswith(".github/")
            or "validation" in normalized
            or "test" in normalized
        ):
            return SourceBoundaryClass.VALIDATION_OR_TOOLING

        if (
            "/calculation/" in f"/{normalized}"
            or "/domain/" in f"/{normalized}"
            or "/services/" in f"/{normalized}"
            or "calculator" in name
            or "solver" in name
        ):
            return SourceBoundaryClass.CALCULATION_CORE_CANDIDATE

        return SourceBoundaryClass.OTHER

    def snapshot(self) -> BuoyCalcReadOnlySnapshot:
        docs = self.governance_documents()
        checks = self.invariant_checks(docs)
        violations = tuple(
            check.invariant_id for check in checks if not check.passed
        )
        return BuoyCalcReadOnlySnapshot(
            repository_root=str(self._root),
            governance_documents=docs,
            git=self.git_snapshot(),
            invariant_checks=checks,
            invariant_violations=violations,
            source_inventory=self.source_inventory(),
            governance_required_checks=GOVERNANCE_REQUIRED_CHECKS,
            release_required_checks=RELEASE_REQUIRED_CHECKS,
            release_state=RELEASE_STATE,
            physical_validation="PHYSICAL_NOT_EXECUTED",
        )

    @staticmethod
    def _interesting_file(relative_path: str) -> bool:
        suffix = Path(relative_path).suffix.casefold()
        return suffix in {
            ".cs",
            ".csproj",
            ".sln",
            ".slnx",
            ".ps1",
            ".yml",
            ".yaml",
            ".md",
            ".json",
        }
