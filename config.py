from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    download_dir: Path
    send_to_chat_id: str | None
    cookies_file: Path | None
    telegram_max_upload_mb: int


def load_settings() -> Settings:
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required. Copy .env.example to .env and set the bot token.")

    download_dir = Path(os.getenv("DOWNLOAD_DIR", "downloads")).expanduser()
    send_to_chat_id = os.getenv("SEND_TO_CHAT_ID", "").strip() or None

    cookies_value = os.getenv("YTDLP_COOKIES_FILE", "").strip()
    cookies_file = Path(cookies_value).expanduser() if cookies_value else None

    max_upload_mb = int(os.getenv("TELEGRAM_MAX_UPLOAD_MB", "50"))

    return Settings(
        telegram_bot_token=token,
        download_dir=download_dir,
        send_to_chat_id=send_to_chat_id,
        cookies_file=cookies_file,
        telegram_max_upload_mb=max_upload_mb,
    )
