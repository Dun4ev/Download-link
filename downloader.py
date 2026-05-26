from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yt_dlp


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

    options: dict[str, Any] = {
        "format": "bestvideo*+bestaudio/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "outtmpl": str(download_dir / "%(extractor)s" / "%(upload_date>%Y-%m-%d)s" / "%(title).180B-%(id)s.%(ext)s"),
        "restrictfilenames": True,
        "windowsfilenames": True,
        "quiet": True,
        "no_warnings": False,
    }

    if cookies_file and cookies_file.exists():
        options["cookiefile"] = str(cookies_file)

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        if not isinstance(info, dict):
            raise RuntimeError("yt-dlp did not return download metadata.")

    return DownloadResult(
        title=str(info.get("title") or "download"),
        webpage_url=str(info.get("webpage_url") or url),
        files=_collect_files(info),
    )


async def download_url(url: str, download_dir: Path, cookies_file: Path | None) -> DownloadResult:
    return await asyncio.to_thread(_download_sync, url, download_dir, cookies_file)
