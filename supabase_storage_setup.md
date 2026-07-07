# Supabase Storage — настройка bucket для вложений (ARCH-change 2026-07)

Этот файл описывает ручные шаги в Supabase Dashboard, которые SQL-миграцией
не покрываются — создание Storage bucket и его политик доступа.

## Зачем это нужно

Cloudflare Worker теперь скачивает voice/photo/document-вложения сам (см.
`worker.js::downloadAndStoreAttachment`) и кладёт их в Supabase Storage,
вместо того чтобы HF скачивал их напрямую у Telegram — та же причина, что
и для `outbox` (см. `architecture_reality.md`): исходящие вызовы из
HF-контейнера к `workers.dev` подвержены `ConnectError`/`ConnectTimeout`,
а вызовы к Supabase — нет.

## Шаг 1 — создать bucket

В Supabase Dashboard: **Storage** → **New bucket**

- **Name:** `telegram-attachments`
- **Public bucket:** **выключено** (приватный) — файлы содержат личные
  сообщения пользователей, доступ должен идти только через service_role key
- Остальные настройки (file size limit, allowed MIME types) можно оставить
  по умолчанию, либо задать лимит размера файла (например, 25 MB, тот же
  лимит, что уже стоит для Whisper ASR в `speech_to_text.py`)

## Шаг 2 — политики доступа (RLS для Storage)

Поскольку и Worker (запись), и HF (чтение) используют **service_role key**,
а не anon-ключ, отдельные RLS-политики для этого bucket не обязательны —
service_role по умолчанию обходит RLS. Если позже понадобится ограничить
доступ даже для service_role (например, через отдельный ключ с урезанными
правами) — здесь нужно будет добавить политики в `storage.objects` для
bucket `telegram-attachments`, аналогично тому, как это делается для таблиц.

## Шаг 3 — структура путей внутри bucket

Worker кладёт файлы по схеме `{kind}/{file_id}.{ext}`, например:

```
telegram-attachments/
  voice/AgACAgIAAxkBAAIK...ogg
  photo/AgACAgIAAxkBAAIL...jpg
  document/AgACAgIAAxkBAAIM...pdf
```

Это соответствует полю `path` в `_attachment`, которое Worker записывает в
`pending_updates.payload._attachment.path` — HF читает файл по этому же
пути через `supabase.storage.from_(bucket).download(path)`.

## Шаг 4 — housekeeping (не обязательно сразу, но стоит иметь в виду)

Файлы в этом bucket не удаляются автоматически. Если объём вложений будет
расти, стоит настроить периодическую очистку (например, через Supabase
Scheduled Function или ручной скрипт) файлов старше N дней — по аналогии с
закомментированной секцией housekeeping в `outbox_schema.sql`.

## Проверка после настройки

1. Отправьте боту голосовое сообщение.
2. В Supabase Dashboard → Storage → `telegram-attachments` → `voice/` —
   должен появиться новый файл с именем `{file_id}.ogg` в течение нескольких
   секунд после отправки.
3. Если файл не появился — смотрите логи Worker'а (Cloudflare Observability)
   на предмет `downloadAndStoreAttachment attempt=... failed` — это укажет,
   на каком именно шаге (getFile / скачивание / загрузка в Storage)
   произошла ошибка.