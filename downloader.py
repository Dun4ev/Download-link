from __future__ import annotations

import asyncio
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yt_dlp
from yt_dlp.utils import DownloadError


GALLERY_DL_FALLBACK_ERRORS = (
    "No video formats found",
    "No video could be found",
)
YT_DLP_EMPTY_METADATA_ERROR = "yt-dlp did not return download metadata."


@dataclass(frozen=True)
class DownloadResult:
    title: str
    webpage_url: str
    files: tuple[Path, ...]


def _collect_files(info: dict[str, Any]) -> tuple[Path, ...]:
    requested = info.get("requested_downloads") or []
    files: list[Path] = []

    for item in requested:
        filepath = item.get("filepath") or item.get("_filename")
        if filepath:
            files.append(Path(filepath))

    if not files:
        filepath = info.get("filepath") or info.get("_filename")
        if filepath:
            files.append(Path(filepath))

    return tuple(path for path in files if path.exists())


def _download_sync(url: str, download_dir: Path, cookies_file: Path | None) -> DownloadResult:
    download_dir.mkdir(parents=True, exist_ok=True)
    target_dir = download_dir / "yt-dlp"

    options: dict[str, Any] = {
        "format": "bestvideo*+bestaudio/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "outtmpl": str(target_dir / "%(extractor)s" / "%(upload_date>%Y-%m-%d)s" / "%(title).180B-%(id)s.%(ext)s"),
        "restrictfilenames": True,
        "windowsfilenames": True,
        "quiet": True,
        "no_warnings": False,
    }

    if cookies_file and cookies_file.exists():
        options["cookiefile"] = str(cookies_file)

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            if not isinstance(info, dict):
                return _download_with_gallery_dl(url, download_dir, cookies_file, YT_DLP_EMPTY_METADATA_ERROR)
    except DownloadError as exc:
        error_text = str(exc)
        if not any(marker in error_text for marker in GALLERY_DL_FALLBACK_ERRORS):
            raise
        return _download_with_gallery_dl(url, download_dir, cookies_file, error_text)

    result = DownloadResult(
        title=str(info.get("title") or "download"),
        webpage_url=str(info.get("webpage_url") or url),
        files=_collect_files(info),
    )

    if result.files:
        return result

    return _download_with_gallery_dl(url, download_dir, cookies_file, "yt-dlp downloaded no files")


def _download_with_gallery_dl(
    url: str,
    download_dir: Path,
    cookies_file: Path | None,
    previous_error: str,
) -> DownloadResult:
    target_dir = download_dir / "gallery-dl"
    before = _snapshot_files(target_dir)

    command = [
        sys.executable,
        "-m",
        "gallery_dl",
        "--no-input",
        "--directory",
        str(target_dir),
        "--windows-filenames",
        url,
    ]

    if cookies_file and cookies_file.exists():
        command[3:3] = ["--cookies", str(cookies_file)]

    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"{previous_error}\ngallery-dl fallback failed: {details}")

    files = tuple(path for path in _snapshot_files(target_dir) - before if path.is_file())
    if not files:
        raise RuntimeError(f"{previous_error}\ngallery-dl fallback finished but did not create files.")

    return DownloadResult(title="download", webpage_url=url, files=files)


def _snapshot_files(directory: Path) -> set[Path]:
    if not directory.exists():
        return set()
    return {path for path in directory.rglob("*") if path.is_file()}


async def download_url(url: str, download_dir: Path, cookies_file: Path | None) -> DownloadResult:
    return await asyncio.to_thread(_download_sync, url, download_dir, cookies_file)
