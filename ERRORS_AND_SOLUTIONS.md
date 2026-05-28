# Ошибки и решения

Этот файл фиксирует реальные ошибки при работе бота и решения, которые были внесены в проект.

## 2026-05-26: Docker не мог читать/обновлять cookies

Ошибка:

```text
[Errno 30] Read-only file system: '/data/cookies/cookies.txt'
```

Причина:

Папка cookies была примонтирована в контейнер как read-only:

```yaml
./data/cookies:/data/cookies:ro
```

`yt-dlp` может обновлять cookies-файл во время работы, поэтому запись в read-only volume падала.

Решение:

В `docker-compose.yml` volume изменен на writable:

```yaml
./data/cookies:/data/cookies
```

После изменения нужно пересоздать контейнер:

```bash
docker compose down
docker compose up -d --build
```

## 2026-05-26: Instagram-пост без видеоформатов

Ошибка:

```text
ERROR: [Instagram] ...: No video formats found!
```

Причина:

`yt-dlp` пытался скачать Instagram-пост как видео. Для фото и каруселей Instagram он иногда не находит видеоформаты, хотя в посте есть скачиваемые изображения.

Решение:

Добавлен fallback через `gallery-dl`. Если `yt-dlp` падает с `No video formats found`, бот пробует скачать ссылку через `gallery-dl`, используя тот же cookies-файл.

Также `yt-dlp` обновлен до `2026.3.17`, добавлена зависимость `gallery-dl==1.32.1`.

После изменения нужно пересобрать контейнер:

```bash
docker compose down
docker compose up -d --build
```

## 2026-05-26: X/Twitter tweet без видео

Ошибка:

```text
ERROR: [twitter] ...: No video could be found in this tweet
```

Причина:

`yt-dlp` искал видео в tweet, но tweet мог содержать фото, GIF-контент, карточку или другой тип вложения без видеоформатов для `yt-dlp`.

Решение:

Расширен fallback на `gallery-dl`: теперь он запускается не только при `No video formats found`, но и при `No video could be found`.

Если в tweet есть изображения или поддерживаемые вложения, `gallery-dl` должен скачать их. Если tweet вообще не содержит скачиваемого медиа, бот вернет ошибку о том, что fallback завершился без созданных файлов.

После изменения нужно пересобрать контейнер:

```bash
docker compose down
docker compose up -d --build
```

## 2026-05-26: Facebook-видео черное на ноутбуке, но нормальное на iPhone

Симптом:

Видео из Facebook Reels в Telegram на ноутбуке отображается черным прямоугольником, при этом видно, что таймер идет и воспроизведение началось. На iPhone то же видео отображается нормально.

Вероятная причина:

Скачанный MP4 может содержать видеодорожку, которую iPhone декодирует, а Telegram Desktop/macOS отображает некорректно. Частые причины: неподходящий codec/profile, pixel format не `yuv420p`, особенности контейнера MP4 или отсутствие `faststart` metadata.

Решение:

Перед отправкой видео бот теперь готовит Telegram-friendly копию через `ffmpeg`:

```text
H.264 video + yuv420p + AAC audio + MP4 faststart
```

Копия сохраняется рядом с исходником с суффиксом `.telegram.mp4` и отправляется в Telegram вместо оригинального видео. Если `ffmpeg` не сможет перекодировать файл, бот отправит оригинал как fallback.

После изменения нужно пересобрать контейнер:

```bash
docker compose down
docker compose up -d --build
```

## 2026-05-26: После добавления очистки контейнер падает с ModuleNotFoundError

Ошибка:

```text
ModuleNotFoundError: No module named 'cleanup'
from cleanup import cleanup_old_downloads, directory_size, format_bytes
File "/app/bot.py", line 14, in <module>
```

Причина:

В проект был добавлен новый файл `cleanup.py`, но `Dockerfile` копировал в образ только:

```dockerfile
COPY bot.py config.py downloader.py ./
```

Локально код работал, потому что `cleanup.py` был в папке проекта. В контейнере файла не было, поэтому импорт падал при старте.

Решение:

В `Dockerfile` добавлен `cleanup.py`:

```dockerfile
COPY bot.py config.py downloader.py cleanup.py ./
```

После изменения нужно пересобрать контейнер:

```bash
docker compose down
docker compose up -d --build
```

## 2026-05-28: Instagram Story вернула пустую metadata из yt-dlp

Ошибка:

```text
yt-dlp did not return download metadata.
```

Причина:

Для Instagram Stories `yt-dlp` может завершить обработку без нормального объекта metadata. Раньше бот считал это окончательной ошибкой и не пробовал второй downloader.

Решение:

Если `yt-dlp` не возвращает metadata, бот теперь запускает fallback через `gallery-dl`, используя тот же `cookies.txt`.

Для Stories особенно важно, чтобы cookies были свежими и аккаунт имел доступ к этой истории.

После изменения нужно пересобрать контейнер:

```bash
docker compose down
docker compose up -d --build
```
