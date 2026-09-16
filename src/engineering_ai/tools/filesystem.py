"""Root-bounded read-only filesystem inspection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engineering_ai.tools.common import ToolAccessError, ToolExecutionError


@dataclass(frozen=True)
class FileEntry:
    relative_path: str
    is_dir: bool
    size: int


class ReadOnlyFilesystemAdapter:
    """Read-only filesystem access constrained to one configured root."""

    def __init__(self, root: str | Path, *, max_read_bytes: int = 1_048_576) -> None:
        if max_read_bytes <= 0:
            raise ValueError("max_read_bytes must be positive")
        self._root = Path(root).resolve(strict=True)
        if not self._root.is_dir():
            raise ValueError("filesystem root must be a directory")
        self._max_read_bytes = max_read_bytes

    @property
    def root(self) -> Path:
        return self._root

    def read_text(self, relative_path: str | Path, *, encoding: str = "utf-8") -> str:
        path = self._resolve_existing(relative_path)
        if not path.is_file():
            raise ToolExecutionError(f"not a regular file: {relative_path}")
        size = path.stat().st_size
        if size > self._max_read_bytes:
            raise ToolExecutionError(
                f"file exceeds max_read_bytes ({size} > {self._max_read_bytes})"
            )
        data = path.read_bytes()
        if len(data) > self._max_read_bytes:
            raise ToolExecutionError("file grew beyond max_read_bytes during read")
        return data.decode(encoding)

    def list_directory(self, relative_path: str | Path = ".") -> tuple[FileEntry, ...]:
        path = self._resolve_existing(relative_path)
        if not path.is_dir():
            raise ToolExecutionError(f"not a directory: {relative_path}")
        entries: list[FileEntry] = []
        for child in sorted(path.iterdir(), key=lambda item: item.name.casefold()):
            resolved = child.resolve(strict=True)
            self._assert_within_root(resolved)
            entries.append(
                FileEntry(
                    relative_path=resolved.relative_to(self._root).as_posix(),
                    is_dir=resolved.is_dir(),
                    size=0 if resolved.is_dir() else resolved.stat().st_size,
                )
            )
        return tuple(entries)

    def exists(self, relative_path: str | Path) -> bool:
        candidate = self._resolve_candidate(relative_path)
        if not candidate.exists():
            return False
        resolved = candidate.resolve(strict=True)
        self._assert_within_root(resolved)
        return True

    def _resolve_existing(self, relative_path: str | Path) -> Path:
        candidate = self._resolve_candidate(relative_path)
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as exc:
            raise ToolExecutionError(f"path does not exist: {relative_path}") from exc
        self._assert_within_root(resolved)
        return resolved

    def _resolve_candidate(self, relative_path: str | Path) -> Path:
        relative = Path(relative_path)
        if relative.is_absolute():
            raise ToolAccessError("absolute paths are not allowed")
        candidate = self._root / relative
        resolved_parent = candidate.parent.resolve(strict=False)
        self._assert_within_root(resolved_parent)
        return candidate

    def _assert_within_root(self, path: Path) -> None:
        try:
            path.relative_to(self._root)
        except ValueError as exc:
            raise ToolAccessError(f"path escapes configured root: {path}") from exc
