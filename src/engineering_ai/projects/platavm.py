"""Strict read-only adapter for the existing PlataVM engineering repository."""

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from engineering_ai.tools import (
    AllowListedProcessRunner,
    CommandSpec,
    GitReadOnlyAdapter,
    ReadOnlyFilesystemAdapter,
    ToolExecutionError,
    ToolResult,
)


REQUIRED_GOVERNANCE_FILES = (
    "AGENTS.md",
    "Docs/PROJECT_STATUS.md",
    "Docs/PROJECT_CONTROL.md",
    "Docs/PROJECT_MASTER.md",
    "Docs/ARCHITECTURE_BASELINE.md",
    "Docs/OPEN_QUESTIONS.md",
    "Docs/TRACEABILITY_V1_9.md",
    "Docs/CHRONOLOGY.md",
)

_KICAD_SUFFIXES = {
    ".kicad_pro",
    ".kicad_sch",
    ".kicad_pcb",
    ".kicad_sym",
    ".kicad_mod",
}
_SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
}


class CIState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    CANCELLED = "CANCELLED"
    IN_PROGRESS = "IN_PROGRESS"
    NOT_RUN = "NOT_RUN"
    UNKNOWN = "UNKNOWN"


class ValidatorState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    TIMEOUT = "TIMEOUT"


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
class PlataVMValidatorResult:
    profile_id: str
    state: ValidatorState
    result: ToolResult


@dataclass(frozen=True)
class PlataVMReadOnlySnapshot:
    repository_root: str
    governance_documents: tuple[GovernanceDocument, ...]
    latest_chronology: GovernanceDocument
    git: GitSnapshot
    kicad_assets: tuple[str, ...]
    conflicts: tuple[str, ...]


def classify_ci_conclusion(
    conclusion: str | None,
    *,
    status: str | None = None,
) -> CIState:
    """Preserve GitHub workflow state without collapsing CANCELLED into FAIL/PASS."""

    normalized_status = (status or "").strip().lower()
    normalized = (conclusion or "").strip().lower()

    if normalized_status in {"queued", "in_progress", "waiting", "requested", "pending"}:
        return CIState.IN_PROGRESS
    if normalized in {"success", "neutral"}:
        return CIState.PASS
    if normalized in {"failure", "timed_out", "action_required"}:
        return CIState.FAIL
    if normalized in {"cancelled", "stale"}:
        return CIState.CANCELLED
    if not normalized and normalized_status in {"", "not_run"}:
        return CIState.NOT_RUN
    return CIState.UNKNOWN


class PlataVMReadOnlyAdapter:
    """Read-only PlataVM inspection and fixed diagnostic execution.

    The adapter exposes no filesystem write/delete, Git mutation, push, PR, or
    generic process API.
    """

    VALIDATOR_REPOSITORY_INTEGRITY = "platavm.repository_integrity"
    VALIDATOR_SEMANTIC_GATES = "platavm.semantic_gates"

    def __init__(
        self,
        repository_root: str | Path,
        *,
        python_executable: str = sys.executable,
        git_executable: str = "git",
        max_read_bytes: int = 2_097_152,
        max_scan_entries: int = 5_000,
        max_scan_depth: int = 10,
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
        specs = {
            self.VALIDATOR_REPOSITORY_INTEGRITY: CommandSpec(
                command_id=self.VALIDATOR_REPOSITORY_INTEGRITY,
                executable=python_executable,
                fixed_args=(
                    "Tools/repository_integrity.py",
                    "--base-ref",
                    "origin/main",
                ),
                timeout_seconds=180.0,
                max_output_bytes=262_144,
            ),
            self.VALIDATOR_SEMANTIC_GATES: CommandSpec(
                command_id=self.VALIDATOR_SEMANTIC_GATES,
                executable=python_executable,
                fixed_args=("Tools/run_all_gates.py",),
                timeout_seconds=300.0,
                max_output_bytes=262_144,
            ),
        }
        self._runner = AllowListedProcessRunner(specs, root=self._root)

    @property
    def root(self) -> Path:
        return self._root

    @property
    def validator_profiles(self) -> tuple[str, ...]:
        return (
            self.VALIDATOR_REPOSITORY_INTEGRITY,
            self.VALIDATOR_SEMANTIC_GATES,
        )

    def governance_documents(self) -> tuple[GovernanceDocument, ...]:
        docs: list[GovernanceDocument] = []
        for path in REQUIRED_GOVERNANCE_FILES:
            if not self._filesystem.exists(path):
                raise ToolExecutionError(f"mandatory PlataVM governance file missing: {path}")
            docs.append(self._read_governance(path))
        return tuple(docs)

    def latest_chronology(self) -> GovernanceDocument:
        directory = "Docs/chronology"
        if not self._filesystem.exists(directory):
            raise ToolExecutionError("mandatory PlataVM chronology directory missing")

        entries = tuple(
            entry
            for entry in self._filesystem.list_directory(directory)
            if (
                not entry.is_dir
                and re.fullmatch(
                    r"\d{4}-\d{2}-\d{2}.*\.md",
                    Path(entry.relative_path).name,
                    flags=re.IGNORECASE,
                )
            )
        )
        if not entries:
            raise ToolExecutionError(
                "Docs/chronology contains no dated YYYY-MM-DD*.md entries"
            )

        latest = max(entries, key=lambda item: Path(item.relative_path).name.casefold())
        return self._read_governance(latest.relative_path)

    def git_snapshot(self) -> GitSnapshot:
        branch_result = self._git.current_branch()
        head_result = self._git.head_sha()
        status_result = self._git.status()
        if not branch_result.ok or not head_result.ok or not status_result.ok:
            raise ToolExecutionError("unable to capture PlataVM Git snapshot")

        origin_main = self._git.ref_sha("origin/main")
        origin_main_sha = origin_main.stdout.strip() if origin_main.ok else None

        status_lines = tuple(
            line for line in status_result.stdout.splitlines() if line.strip()
        )
        dirty = any(not line.startswith("## ") for line in status_lines)

        return GitSnapshot(
            branch=branch_result.stdout.strip(),
            head_sha=head_result.stdout.strip(),
            origin_main_sha=origin_main_sha,
            dirty=dirty,
            status_text=status_result.stdout,
        )

    def kicad_assets(self) -> tuple[str, ...]:
        kicad_root = "Hardware/KiCad"
        if not self._filesystem.exists(kicad_root):
            raise ToolExecutionError("mandatory PlataVM Hardware/KiCad tree missing")
        queue: list[tuple[str, int]] = [(kicad_root, 0)]
        assets: list[str] = []
        scanned = 0

        while queue:
            relative_dir, depth = queue.pop(0)
            if depth > self._max_scan_depth:
                raise ToolExecutionError("PlataVM KiCad scan exceeded max_scan_depth")

            for entry in self._filesystem.list_directory(relative_dir):
                scanned += 1
                if scanned > self._max_scan_entries:
                    raise ToolExecutionError("PlataVM KiCad scan exceeded max_scan_entries")

                path = Path(entry.relative_path)
                if entry.is_dir:
                    if path.name in _SKIP_DIR_NAMES:
                        continue
                    if path.name.endswith(".pretty"):
                        assets.append(entry.relative_path)
                    queue.append((entry.relative_path, depth + 1))
                    continue

                if path.suffix.lower() in _KICAD_SUFFIXES:
                    assets.append(entry.relative_path)

        return tuple(sorted(set(assets), key=str.casefold))

    def conflicts(
        self,
        *,
        governance_documents: tuple[GovernanceDocument, ...] | None = None,
        git: GitSnapshot | None = None,
    ) -> tuple[str, ...]:
        docs = governance_documents or self.governance_documents()
        git_snapshot = git or self.git_snapshot()
        status_doc = next(
            doc for doc in docs if doc.path == "Docs/PROJECT_STATUS.md"
        )

        conflicts: list[str] = []
        declared_main = self._status_table_value(
            status_doc.content,
            "Подтверждённый base main",
        )
        declared_branch = self._status_table_value(
            status_doc.content,
            "Активная ветка",
        )

        if declared_main and git_snapshot.origin_main_sha:
            if declared_main != git_snapshot.origin_main_sha:
                conflicts.append(
                    "PROJECT_STATUS declared main "
                    f"{declared_main} != origin/main {git_snapshot.origin_main_sha}"
                )
        elif declared_main and not git_snapshot.origin_main_sha:
            conflicts.append(
                "PROJECT_STATUS declares main but origin/main could not be resolved"
            )

        if (
            declared_branch
            and git_snapshot.branch
            and git_snapshot.branch != "main"
            and declared_branch != git_snapshot.branch
        ):
            conflicts.append(
                "PROJECT_STATUS active branch "
                f"{declared_branch} != checked-out branch {git_snapshot.branch}"
            )

        return tuple(conflicts)

    def snapshot(self) -> PlataVMReadOnlySnapshot:
        docs = self.governance_documents()
        git = self.git_snapshot()
        return PlataVMReadOnlySnapshot(
            repository_root=str(self._root),
            governance_documents=docs,
            latest_chronology=self.latest_chronology(),
            git=git,
            kicad_assets=self.kicad_assets(),
            conflicts=self.conflicts(governance_documents=docs, git=git),
        )

    def run_validator(self, profile_id: str) -> PlataVMValidatorResult:
        """Run one fixed read-only PlataVM diagnostic profile."""

        before = self.git_snapshot()
        result = self._runner.run(profile_id)
        after = self.git_snapshot()

        if before.head_sha != after.head_sha:
            raise ToolExecutionError(
                f"validator changed repository HEAD: {before.head_sha} -> {after.head_sha}"
            )
        if before.status_text != after.status_text:
            raise ToolExecutionError(
                "validator changed tracked/untracked Git-visible repository state"
            )

        state = (
            ValidatorState.TIMEOUT
            if result.timed_out
            else ValidatorState.PASS
            if result.ok
            else ValidatorState.FAIL
        )
        return PlataVMValidatorResult(
            profile_id=profile_id,
            state=state,
            result=result,
        )

    def _read_governance(self, relative_path: str) -> GovernanceDocument:
        content = self._filesystem.read_text(relative_path)
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return GovernanceDocument(
            path=relative_path,
            sha256=digest,
            content=content,
        )

    @staticmethod
    def _status_table_value(content: str, key: str) -> str | None:
        normalized_key = re.sub(r"[\x60*_]", "", key).strip().casefold()
        for line in content.splitlines():
            if not line.lstrip().startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 2:
                continue
            label = re.sub(r"[\x60*_]", "", cells[0]).strip().casefold()
            if label != normalized_key:
                continue
            value = cells[1].strip().strip(chr(96)).strip()
            return value or None
        return None
