"""Deterministic PNG validation and root-bounded publication for Gate 025."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import tempfile
import zlib

from engineering_ai.tools.common import ToolAccessError, ToolExecutionError


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PNG_BYTES = 64 * 1024 * 1024
MAX_PNG_DIMENSION = 4096


class PngValidationError(ToolExecutionError):
    """Raised when generated PNG bytes violate the Gate 025 contract."""


@dataclass(frozen=True)
class PngInfo:
    width: int
    height: int
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class PublishedImageArtifact:
    relative_path: str
    width: int
    height: int
    size_bytes: int
    sha256: str
    media_type: str = "image/png"
    authority: str = "ADVISORY_CONCEPT_ONLY"
    evidence_eligible: bool = False
    engineering_drawing: bool = False
    physical_validation: str = "PHYSICAL_NOT_EXECUTED"


def validate_png(
    data: bytes,
    *,
    expected_width: int | None = None,
    expected_height: int | None = None,
    max_bytes: int = MAX_PNG_BYTES,
) -> PngInfo:
    if not isinstance(data, bytes):
        raise PngValidationError("PNG payload must be bytes")
    if len(data) <= len(PNG_SIGNATURE):
        raise PngValidationError("PNG payload is empty or truncated")
    if len(data) > max_bytes:
        raise PngValidationError("PNG payload exceeds configured size bound")
    if not data.startswith(PNG_SIGNATURE):
        raise PngValidationError("PNG signature mismatch")

    offset = len(PNG_SIGNATURE)
    chunk_index = 0
    width = height = None
    seen_idat = False
    seen_iend = False

    while offset < len(data):
        if len(data) - offset < 12:
            raise PngValidationError("PNG chunk header/trailer is truncated")
        length = int.from_bytes(data[offset : offset + 4], "big")
        chunk_type = data[offset + 4 : offset + 8]
        chunk_start = offset + 8
        chunk_end = chunk_start + length
        crc_end = chunk_end + 4
        if crc_end > len(data):
            raise PngValidationError("PNG chunk exceeds payload boundary")

        chunk_data = data[chunk_start:chunk_end]
        expected_crc = int.from_bytes(data[chunk_end:crc_end], "big")
        actual_crc = zlib.crc32(chunk_type)
        actual_crc = zlib.crc32(chunk_data, actual_crc) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise PngValidationError("PNG chunk CRC mismatch")

        if chunk_index == 0:
            if chunk_type != b"IHDR" or length != 13:
                raise PngValidationError("PNG first chunk must be 13-byte IHDR")
            width = int.from_bytes(chunk_data[0:4], "big")
            height = int.from_bytes(chunk_data[4:8], "big")
            bit_depth = chunk_data[8]
            color_type = chunk_data[9]
            compression = chunk_data[10]
            filter_method = chunk_data[11]
            interlace = chunk_data[12]
            if width <= 0 or height <= 0:
                raise PngValidationError("PNG dimensions must be positive")
            if width > MAX_PNG_DIMENSION or height > MAX_PNG_DIMENSION:
                raise PngValidationError("PNG dimensions exceed Gate 025 bound")
            valid_depths = {
                0: {1, 2, 4, 8, 16},
                2: {8, 16},
                3: {1, 2, 4, 8},
                4: {8, 16},
                6: {8, 16},
            }
            if color_type not in valid_depths or bit_depth not in valid_depths[color_type]:
                raise PngValidationError("PNG IHDR bit-depth/color-type combination is invalid")
            if compression != 0 or filter_method != 0 or interlace not in (0, 1):
                raise PngValidationError("PNG IHDR method fields are invalid")
        elif chunk_type == b"IHDR":
            raise PngValidationError("PNG contains duplicate IHDR")

        if chunk_type == b"IDAT":
            seen_idat = True
        if chunk_type == b"IEND":
            if length != 0:
                raise PngValidationError("PNG IEND must have zero length")
            seen_iend = True
            if crc_end != len(data):
                raise PngValidationError("PNG contains trailing bytes after IEND")
            break

        offset = crc_end
        chunk_index += 1

    if width is None or height is None or not seen_idat or not seen_iend:
        raise PngValidationError("PNG is missing required IHDR/IDAT/IEND structure")
    if expected_width is not None and width != expected_width:
        raise PngValidationError("PNG width does not match requested width")
    if expected_height is not None and height != expected_height:
        raise PngValidationError("PNG height does not match requested height")

    return PngInfo(
        width=width,
        height=height,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )


class PngArtifactPublisher:
    """Publish one validated PNG inside a configured root."""

    def __init__(self, root: str | Path, *, max_bytes: int = MAX_PNG_BYTES) -> None:
        self._root = Path(root).resolve(strict=True)
        if not self._root.is_dir():
            raise ValueError("image artifact root must be a directory")
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self._max_bytes = max_bytes

    def publish(
        self,
        *,
        data: bytes,
        relative_path: str,
        expected_width: int,
        expected_height: int,
    ) -> PublishedImageArtifact:
        info = validate_png(
            data,
            expected_width=expected_width,
            expected_height=expected_height,
            max_bytes=self._max_bytes,
        )
        target = self._resolve_target(relative_path)
        parent = target.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise PngValidationError("PNG target directory creation failed") from exc

        resolved_parent = parent.resolve(strict=True)
        try:
            resolved_parent.relative_to(self._root)
        except ValueError as exc:
            raise ToolAccessError("PNG target parent escapes configured root") from exc
        self._reject_symlink_components(resolved_parent)

        temp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=".engineering-ai-image-",
                suffix=".png",
                dir=resolved_parent,
                delete=False,
            ) as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
                temp_name = handle.name
            os.replace(temp_name, target)
            temp_name = None
        except OSError as exc:
            raise PngValidationError("PNG artifact publication failed") from exc
        finally:
            if temp_name is not None:
                try:
                    Path(temp_name).unlink(missing_ok=True)
                except OSError:
                    pass

        return PublishedImageArtifact(
            relative_path=relative_path.replace("\\", "/"),
            width=info.width,
            height=info.height,
            size_bytes=info.size_bytes,
            sha256=info.sha256,
        )

    def _resolve_target(self, relative_path: str) -> Path:
        value = relative_path.strip()
        if not value or len(value) > 512:
            raise ToolAccessError("PNG artifact path must contain 1..512 characters")
        relative = Path(value)
        if relative.is_absolute():
            raise ToolAccessError("absolute PNG artifact paths are not allowed")
        if relative.suffix.lower() != ".png":
            raise ToolAccessError("Gate 025 publishes PNG artifacts only")
        if any(part in ("", ".", "..") for part in relative.parts):
            raise ToolAccessError("PNG artifact path contains forbidden traversal component")

        candidate = self._root / relative
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(self._root)
        except ValueError as exc:
            raise ToolAccessError("PNG artifact path escapes configured root") from exc

        cursor = self._root
        for part in relative.parts:
            cursor = cursor / part
            if cursor.exists() and cursor.is_symlink():
                raise ToolAccessError("PNG artifact path traverses a symlink")
        return resolved

    def _reject_symlink_components(self, resolved_parent: Path) -> None:
        relative = resolved_parent.relative_to(self._root)
        cursor = self._root
        for part in relative.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise ToolAccessError("PNG artifact parent traverses a symlink")
