from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CleanupResult:
    deleted_files: int
    deleted_dirs: int
    freed_bytes: int


def cleanup_old_downloads(download_dir: Path, max_age_days: int) -> CleanupResult:
    if max_age_days <= 0 or not download_dir.exists():
        return CleanupResult(deleted_files=0, deleted_dirs=0, freed_bytes=0)

    cutoff = time.time() - max_age_days * 24 * 60 * 60
    deleted_files = 0
    deleted_dirs = 0
    freed_bytes = 0

    for path in sorted(download_dir.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if path.is_file() and path.stat().st_mtime < cutoff:
            freed_bytes += path.stat().st_size
            path.unlink()
            deleted_files += 1
        elif path.is_dir():
            try:
                path.rmdir()
                deleted_dirs += 1
            except OSError:
                pass

    return CleanupResult(deleted_files=deleted_files, deleted_dirs=deleted_dirs, freed_bytes=freed_bytes)


def directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024

    return f"{size} B"
