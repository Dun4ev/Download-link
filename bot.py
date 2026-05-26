from __future__ import annotations

import asyncio
import logging
import re
import subprocess
from pathlib import Path

from telegram import Message, Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from config import Settings, load_settings
from downloader import DownloadResult, download_url


URL_RE = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}
ANIMATION_EXTENSIONS = {".gif"}
TELEGRAM_VIDEO_SUFFIX = ".telegram.mp4"


def extract_urls(text: str) -> list[str]:
    return [url.rstrip(").,;]") for url in URL_RE.findall(text)]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Пришлите ссылку на публичное фото, видео или GIF. Я скачаю файл и сохраню его в заданную папку."
    )


async def where(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    target = settings.send_to_chat_id or "чат с отправителем"
    await update.effective_message.reply_text(f"Папка: {settings.download_dir}\nОтправка: {target}")


def transcode_video_for_telegram(file_path: Path) -> Path:
    if file_path.suffix.lower() not in VIDEO_EXTENSIONS or file_path.name.endswith(TELEGRAM_VIDEO_SUFFIX):
        return file_path

    output_path = file_path.with_name(f"{file_path.stem}{TELEGRAM_VIDEO_SUFFIX}")
    if output_path.exists() and output_path.stat().st_size > 0 and output_path.stat().st_mtime >= file_path.stat().st_mtime:
        return output_path

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(file_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-level",
        "4.1",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
        logging.error("ffmpeg telegram transcode failed for %s: %s", file_path, completed.stderr.strip())
        return file_path

    return output_path


async def prepare_file_for_upload(file_path: Path) -> Path:
    if file_path.suffix.lower() in VIDEO_EXTENSIONS:
        return await asyncio.to_thread(transcode_video_for_telegram, file_path)
    return file_path


async def send_media_file(
    message: Message,
    context: ContextTypes.DEFAULT_TYPE,
    file_path: Path,
    caption: str,
    target_chat_id: str | int | None,
) -> None:
    suffix = file_path.suffix.lower()
    send_to_chat = target_chat_id is not None

    try:
        with file_path.open("rb") as media:
            if suffix in PHOTO_EXTENSIONS:
                if send_to_chat:
                    await context.bot.send_photo(chat_id=target_chat_id, photo=media, caption=caption)
                else:
                    await message.reply_photo(photo=media, caption=caption)
            elif suffix in VIDEO_EXTENSIONS:
                if send_to_chat:
                    await context.bot.send_video(chat_id=target_chat_id, video=media, caption=caption)
                else:
                    await message.reply_video(video=media, caption=caption)
            elif suffix in ANIMATION_EXTENSIONS:
                if send_to_chat:
                    await context.bot.send_animation(chat_id=target_chat_id, animation=media, caption=caption)
                else:
                    await message.reply_animation(animation=media, caption=caption)
            else:
                raise ValueError(f"Unsupported media preview extension: {suffix}")
    except (TelegramError, ValueError):
        logging.exception("Falling back to document upload for %s", file_path)
        with file_path.open("rb") as media:
            if send_to_chat:
                await context.bot.send_document(chat_id=target_chat_id, document=media, caption=caption)
            else:
                await message.reply_document(document=media, caption=caption)


async def send_result(update: Update, context: ContextTypes.DEFAULT_TYPE, result: DownloadResult) -> None:
    settings: Settings = context.application.bot_data["settings"]
    message = update.effective_message
    target_chat_id = settings.send_to_chat_id
    max_bytes = settings.telegram_max_upload_mb * 1024 * 1024

    if not result.files:
        await message.reply_text(f"Скачивание завершилось, но файл не найден на диске: {result.webpage_url}")
        return

    sent = 0
    skipped: list[Path] = []

    for file_path in result.files:
        upload_path = await prepare_file_for_upload(file_path)
        if upload_path.stat().st_size > max_bytes:
            skipped.append(upload_path)
            continue

        await send_media_file(message, context, upload_path, result.title[:1024], target_chat_id)
        sent += 1

    saved_list = "\n".join(str(path) for path in result.files)
    if skipped:
        skipped_list = "\n".join(str(path) for path in skipped)
        await message.reply_text(
            f"Сохранено на диск, но часть файлов больше лимита Telegram.\n\nФайлы:\n{saved_list}\n\nНе отправлено:\n{skipped_list}"
        )
    elif settings.send_to_chat_id:
        await message.reply_text(f"Готово. Файлов отправлено в целевой чат: {sent}\nСохранено:\n{saved_list}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    message = update.effective_message
    urls = extract_urls(message.text or message.caption or "")

    if not urls:
        await message.reply_text("Не вижу ссылки. Пришлите URL, начинающийся с http:// или https://.")
        return

    for url in urls:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        status = await message.reply_text(f"Скачиваю: {url}")

        try:
            result = await download_url(url, settings.download_dir, settings.cookies_file)
        except Exception as exc:
            logging.exception("Download failed for %s", url)
            await status.edit_text(
                "Не получилось скачать ссылку.\n"
                f"Причина: {exc}\n\n"
                "Для Instagram/Facebook/X часто нужны cookies из браузера и доступ к самому посту."
            )
            continue

        await status.edit_text(f"Скачано: {result.title}")
        await send_result(update, context, result)


def build_app(settings: Settings) -> Application:
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data["settings"] = settings
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("where", where))
    app.add_handler(MessageHandler(filters.TEXT | filters.CaptionRegex(URL_RE), handle_message))
    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    build_app(settings).run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
