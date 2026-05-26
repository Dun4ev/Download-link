from __future__ import annotations

import logging
import re
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from config import Settings, load_settings
from downloader import DownloadResult, download_url


URL_RE = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)


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


async def send_result(update: Update, context: ContextTypes.DEFAULT_TYPE, result: DownloadResult) -> None:
    settings: Settings = context.application.bot_data["settings"]
    message = update.effective_message
    target_chat_id = settings.send_to_chat_id or update.effective_chat.id
    max_bytes = settings.telegram_max_upload_mb * 1024 * 1024

    if not result.files:
        await message.reply_text(f"Скачивание завершилось, но файл не найден на диске: {result.webpage_url}")
        return

    sent = 0
    skipped: list[Path] = []

    for file_path in result.files:
        if file_path.stat().st_size > max_bytes:
            skipped.append(file_path)
            continue

        with file_path.open("rb") as media:
            if settings.send_to_chat_id:
                await context.bot.send_document(
                    chat_id=target_chat_id,
                    document=media,
                    caption=result.title[:1024],
                )
            else:
                await message.reply_document(
                    document=media,
                    caption=result.title[:1024],
                )
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
