# Telegram media download bot

Бот принимает ссылки и скачивает публичные фото, видео и GIF через `yt-dlp`. Подходит для Instagram, X/Twitter, Facebook, YouTube, TikTok и других сервисов, которые поддерживает `yt-dlp`.

Для Instagram-фото, каруселей и X/Twitter-постов без видео бот использует fallback через `gallery-dl`, потому что `yt-dlp` иногда ищет только видеоформаты.

Важно: некоторые сайты требуют авторизацию, cookies, регулярно меняют защиту или запрещают скачивание в правилах сервиса. Бот не обходит DRM, платный доступ и приватные страницы. Используйте его только для контента, который вы имеете право скачивать.

## Установка на Synology через Docker Compose

Основной сценарий для NAS: файлы сохраняются в папку `data/downloads`, cookies лежат в `data/cookies/cookies.txt`, а бот отвечает скачанным фото, видео или GIF прямо в том же чате, куда вы отправили ссылку.

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
CLEANUP_DOWNLOADS_AFTER_DAYS=30
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

После запуска отправьте боту ссылку. Он скачает файл, сохранит его на NAS и ответит скачанным фото, видео или GIF в этом же чате без подписи. Видео перед отправкой подготавливается как совместимый MP4 для Telegram Desktop и мобильных клиентов. Если Telegram не примет формат как медиа, бот отправит его обычным файлом. Команда `/where` покажет текущую папку сохранения и целевой чат отправки.

Если задан `SEND_TO_CHAT_ID`, в канал отправляется только само фото, видео, GIF или файл без подписи. Сообщения статуса `Скачиваю...` и `Скачано...` остаются в чате, куда вы отправили ссылку, и в канал не уходят.

## Команды бота

- `/help` - показать справку по боту и командам.
- `/where` - показать папку downloads, ее размер, цель отправки и срок автоочистки.
- `/cleanup` - вручную удалить файлы старше `CLEANUP_DOWNLOADS_AFTER_DAYS`.

## Очистка downloads

По умолчанию бот удаляет файлы из `DOWNLOAD_DIR`, если они старше 30 дней:

```bash
CLEANUP_DOWNLOADS_AFTER_DAYS=30
```

Очистка запускается после успешного скачивания и отправки, а также вручную командой `/cleanup`.

Чтобы отключить автоочистку:

```bash
CLEANUP_DOWNLOADS_AFTER_DAYS=0
```

Папка cookies не очищается, потому что она находится отдельно: `data/cookies`.

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

### Экспорт cookies через Get cookies.txt LOCALLY

Удобный вариант для Chrome, Edge и Firefox - расширение **Get cookies.txt LOCALLY**:

- Chrome Web Store: <https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc>
- Firefox Add-ons: <https://addons.mozilla.org/en-US/firefox/addon/get-cookies-txt-locally/>

Порядок:

1. Установите расширение в браузер.
2. Откройте в этом же браузере нужные сайты:
   - <https://www.instagram.com>
   - <https://www.facebook.com>
   - <https://x.com>
3. Войдите в аккаунты, к которым у вас есть доступ.
4. Откройте расширение **Get cookies.txt LOCALLY**.
5. Выберите формат экспорта **Netscape**.
6. Если хотите один общий файл для Instagram/Facebook/X, выберите экспорт **all cookies** / **export all cookies**.
7. Сохраните файл как:

```bash
cookies.txt
```

8. Положите файл в папку проекта:

```bash
data/cookies/cookies.txt
```

Для Synology через File Station это означает: открыть папку проекта, зайти в `data/cookies` и заменить там `cookies.txt`.

Если экспортировать cookies отдельно по каждому сайту, не перезаписывайте общий файл последним сайтом. Иначе в `cookies.txt` останутся cookies только одного сервиса. Самый простой способ - залогиниться в Instagram/Facebook/X в одном браузере и экспортировать **all cookies** в один файл.

### Когда обновлять cookies

Обновляйте `data/cookies/cookies.txt`, если бот пишет ошибки вроде:

```text
login required
not authorized
sign in
cookies
```

Порядок обновления:

1. Откройте Instagram/Facebook/X в браузере.
2. Убедитесь, что вы залогинены.
3. Снова экспортируйте cookies в Netscape format.
4. Перезапишите файл:

```bash
data/cookies/cookies.txt
```

Если путь и имя файла не менялись, перезапуск контейнера обычно не нужен. Если хотите перезапустить вручную:

```bash
docker compose restart
```

### Безопасность cookies

`cookies.txt` нельзя отправлять другим людям, публиковать в GitHub или хранить в общей папке. По сути это временный доступ к вашей браузерной сессии.

Рекомендации:

- используйте отдельный браузерный профиль для бота;
- не используйте основной личный аккаунт, если можно завести отдельный;
- если cookies-файл случайно утек, выйдите из аккаунта на сайте, смените пароль при необходимости и экспортируйте новый файл.

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

## Журнал ошибок

Реальные ошибки и внесенные решения фиксируются в `ERRORS_AND_SOLUTIONS.md`.
