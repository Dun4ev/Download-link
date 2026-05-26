# Telegram media download bot

Бот принимает ссылки и скачивает публичные фото, видео и GIF через `yt-dlp`. Подходит для Instagram, X/Twitter, Facebook, YouTube, TikTok и других сервисов, которые поддерживает `yt-dlp`.

Важно: некоторые сайты требуют авторизацию, cookies, регулярно меняют защиту или запрещают скачивание в правилах сервиса. Бот не обходит DRM, платный доступ и приватные страницы. Используйте его только для контента, который вы имеете право скачивать.

## Установка на Synology через Docker Compose

Основной сценарий для NAS: файлы сохраняются в папку `data/downloads`, cookies лежат в `data/cookies/cookies.txt`, а бот отвечает скачанным файлом прямо в том же чате, куда вы отправили ссылку.

Подготовьте папки рядом с проектом:

```bash
mkdir -p data/downloads data/cookies
cp .env.example .env
```

Откройте `.env` и задайте:

```bash
TELEGRAM_BOT_TOKEN=токен_от_BotFather
SEND_TO_CHAT_ID=
DOWNLOAD_DIR=/data/downloads
YTDLP_COOKIES_FILE=/data/cookies/cookies.txt
TELEGRAM_MAX_UPLOAD_MB=50
```

Если хотите дополнительно или вместо ответа отправлять файл в канал, добавьте бота администратором канала и укажите:

```bash
SEND_TO_CHAT_ID=@your_channel_username
```

Если `SEND_TO_CHAT_ID` пустой, бот отвечает файлом прямо на ваше сообщение со ссылкой.

Соберите и запустите контейнер:

```bash
docker compose up -d --build
```

Посмотреть логи:

```bash
docker compose logs -f
```

Перезапустить бота:

```bash
docker compose restart
```

Обновить образ после изменений в проекте:

```bash
docker compose build --no-cache
docker compose up -d
```

После запуска отправьте боту ссылку. Он скачает файл, сохранит его на NAS и ответит скачанным файлом в этом же чате. Команда `/where` покажет текущую папку сохранения и целевой чат отправки.

## Cookies для Instagram/Facebook/X

Для сервисов, которые требуют вход, экспортируйте cookies из браузера в Netscape format и положите файл сюда:

```bash
data/cookies/cookies.txt
```

В контейнере этот файл доступен как:

```bash
/data/cookies/cookies.txt
```

Чтобы обновить cookies, просто перезапишите `data/cookies/cookies.txt` свежим файлом. Если путь не менялся, перезапуск контейнера обычно не нужен: `yt-dlp` читает cookies-файл при каждом скачивании.

Папка `data/cookies` монтируется в контейнер с правом записи. Это нужно потому, что `yt-dlp` может обновлять cookies-файл во время работы. Если примонтировать ее как read-only, скачивание может падать с ошибкой `Read-only file system: '/data/cookies/cookies.txt'`.

Если файла `data/cookies/cookies.txt` еще нет, бот будет скачивать без cookies. Это нормально для публичных ссылок, которым не нужна авторизация.

Не публикуйте этот файл и не добавляйте его в git. Cookies-файл фактически дает доступ к вашей браузерной сессии.

## Локальный запуск без Docker

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

Для локального запуска можно поменять в `.env`:

```bash
DOWNLOAD_DIR=downloads
YTDLP_COOKIES_FILE=/absolute/path/to/cookies.txt
```

## Ограничения

- `yt-dlp` не гарантирует скачивание с абсолютно любого сайта.
- Instagram/Facebook/X могут требовать cookies и иногда ломаться после изменений сайта.
- Большие файлы сохраняются локально, но не отправляются в Telegram, если больше `TELEGRAM_MAX_UPLOAD_MB`.
- По умолчанию плейлисты не скачиваются, чтобы случайно не забрать сотни файлов.
