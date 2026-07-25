"""Acquisition security controls — archive bombs, traversal, symlink escape."""
from __future__ import annotations

import os
import zipfile
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from .common import (
    EXECUTABLE_SUFFIXES,
    MAX_ARCHIVE_ENTRIES,
    MAX_COMPRESSION_RATIO,
    MAX_SINGLE_ENTRY_BYTES,
)


class AcquisitionSecurityError(ValueError):
    """Fail-closed acquisition / extraction security violation."""


def assert_allowlisted_url(url: str, allowlisted_urls: Sequence[str]) -> None:
    if url not in allowlisted_urls:
        raise AcquisitionSecurityError(
            f"arbitrary URL rejected (not in allowlist): {url!r}"
        )


def assert_https(url: str) -> None:
    if not url.startswith("https://"):
        raise AcquisitionSecurityError(f"non-HTTPS URL rejected: {url!r}")


def reject_path_traversal(member_name: str) -> None:
    normalized = member_name.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized:
        raise AcquisitionSecurityError(f"path traversal rejected: {member_name!r}")
    if ".." in Path(normalized).parts:
        raise AcquisitionSecurityError(f"path traversal rejected: {member_name!r}")


def reject_symlink_escape(path: Path, root: Path) -> None:
    resolved = path.resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise AcquisitionSecurityError(
            f"symlink/path escape rejected: {path} -> {resolved}"
        ) from exc


def reject_executable(path: Path) -> None:
    if path.suffix.lower() in EXECUTABLE_SUFFIXES:
        raise AcquisitionSecurityError(f"executable file rejected: {path.name}")
    # POSIX executable bit
    try:
        mode = path.stat().st_mode
    except OSError:
        return
    if mode & 0o111:
        raise AcquisitionSecurityError(f"executable permission rejected: {path}")


def inspect_zip_security(archive: Path) -> List[str]:
    """Inspect ZIP members before extraction. Returns warnings."""
    warnings: List[str] = []
    if not zipfile.is_zipfile(archive):
        raise AcquisitionSecurityError(f"not a ZIP archive: {archive}")
    with zipfile.ZipFile(archive, "r") as zf:
        infos = zf.infolist()
        if len(infos) > MAX_ARCHIVE_ENTRIES:
            raise AcquisitionSecurityError(
                f"archive bomb indicator: entry count {len(infos)} > {MAX_ARCHIVE_ENTRIES}"
            )
        total_uncompressed = 0
        total_compressed = 0
        for info in infos:
            reject_path_traversal(info.filename)
            # Symlink / absolute indicators in ZIP extras are rare; name checks above.
            if info.file_size > MAX_SINGLE_ENTRY_BYTES:
                raise AcquisitionSecurityError(
                    f"archive entry too large: {info.filename} ({info.file_size} bytes)"
                )
            total_uncompressed += max(0, info.file_size)
            total_compressed += max(1, info.compress_size)
            if info.filename.lower().endswith(tuple(EXECUTABLE_SUFFIXES)):
                raise AcquisitionSecurityError(
                    f"executable archive entry rejected: {info.filename}"
                )
        if total_compressed > 0:
            ratio = total_uncompressed / float(total_compressed)
            if ratio > MAX_COMPRESSION_RATIO and total_uncompressed > 50 * 1024 * 1024:
                raise AcquisitionSecurityError(
                    f"archive bomb indicator: compression ratio {ratio:.1f}"
                )
        if total_uncompressed == 0:
            warnings.append("archive_has_zero_uncompressed_size")
    return warnings


def safe_extract_zip(archive: Path, destination: Path) -> List[str]:
    """Extract ZIP into destination after security inspection."""
    warnings = inspect_zip_security(archive)
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "r") as zf:
        for info in zf.infolist():
            reject_path_traversal(info.filename)
            target = destination / info.filename
            # Ensure target stays under destination.
            reject_symlink_escape(target if not info.is_dir() else target, destination)
        zf.extractall(destination)
    # Post-extract walk: reject symlinks escaping and executables.
    for root, dirs, files in os.walk(destination):
        root_path = Path(root)
        for name in dirs + files:
            p = root_path / name
            if p.is_symlink():
                reject_symlink_escape(p, destination)
            if p.is_file():
                reject_executable(p)
                reject_symlink_escape(p, destination)
    return warnings


def bounded_redirects(history: Iterable[str], *, max_redirects: int) -> None:
    count = len(list(history))
    if count > max_redirects:
        raise AcquisitionSecurityError(
            f"redirect limit exceeded: {count} > {max_redirects}"
        )
