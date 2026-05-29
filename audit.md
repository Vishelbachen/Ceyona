# CEYONA — ARCHITECTURE AUDIT
**Дата:** май 2026 (обновлён май 2026)
**Проверено:** architecture.md v8.4, models.md v7.3, economic.md v5.2 + весь runtime код
**Статус:** 13.1, 13.5, 13.6, 17.3 закрыты. Открыто: 3 UX/качество + 1 архитектурный gap.

Обозначения: ✅ Закрыто | ⚠️ Открыто | 🔴 Критично | 🟡 Средний | 🟢 Низкий

---

## ⚡ АБСОЛЮТНЫЙ ПРИОРИТЕТ — КАЧЕСТВО ОТВЕТОВ

**Пользователь видит только ответ бота. Не pipeline, не архитектуру — только ответ.**
Целевой уровень: **Claude / ChatGPT** — разговорный, тёплый, умный, без роботизации.

**Правило:** любое архитектурное изменение оценивается по одному критерию — стал ли ответ лучше или хуже. Если хуже — откат, даже если изменение «архитектурно правильное».

**Не делай костылей, заглушек и временных решений.** Продакшн серьёзный. Каждое решение должно быть правильным и масштабируемым — с первого раза.

### Файлы, которые определяют КАК бот отвечает

| Файл | Что решает |
|------|-----------|
| `cognition/intent_engine.py` | System prompts для каждого intent — голос и стиль |
| `transport/telegram/vision_handler.py` | Обработка изображений |
| `transport/telegram/update_handler.py` | Общий flow ответа, история |
| `llm/prompt_engine.py` | Сборка промпта перед LLM |
| `core/execution/orchestrator.py` | intent → путь → ответ |
| `agents/compound_agent.py` | Синтез ответов для data-driven интентов |
| `cognition/response_synthesizer.py` | Финальная обработка перед отправкой |

### Признаки проблемы с ответами

- Начинается с «Изображение представляет собой» / «The image shows» → vision fast-path сломан
- Содержит `Constraints:`, `Candidates:`, `Ограничения:` → CoT артефакты (§13.3)
- Пустой или обрывается → timeout или 413
- Тон сухой на простых вопросах → CONVERSATION system prompt
- На альбом (несколько фото) — отвечает по одному → media_group не агрегируется (§13.6)

### Задеплоены (май 2026)
- `vision_handler.py` — экстрактор переписан: идентифицирует нарисованных персонажей, описывает реальных людей без именования, не начинает с мета-фраз
- `vision_handler.py` — маршрутизация: «не знаю» → pipeline, не raw output
- `vision_handler.py` — добавлен `handle_vision_group()`: батч-обработка нескольких изображений одним Groq вызовом (§13.6)
- `intent_engine.py` — QUESTION prompt: убрана роботизация, тёплый голос
- `intent_engine.py` — SEARCH prompt очищен: убран micro-orchestrator («HOW TO ANSWER», «End with 1-2 useful links», «list 2-3 briefly and let the user confirm»). Оставлены: grounding rules, no-hallucinate, if nothing matches — say so
- `intent_engine.py` — восстановлены `classify()` и `_llm_pre_classify()` (были утеряны при §13.5 рефакторинге)
- `update_handler.py` — история: сохраняется caption, не vision dump (фикс 413)
- `update_handler.py` — photo-блок: одиночное фото → старый путь; альбом (`media_group_id`) → агрегатор (§13.6)
- `intent_engine.py` — LLM pre-classifier вместо hardcoded signal tuples (все 75 языков)
- `intent_engine.py` — history context для follow-up сообщений (§13.4 частично)
- `prompt_engine.py` — переписан: lang → system prompt → truth block → format. Контекст в user turn
- `reasoning_engine.py` — QUESTION на GENERAL/HEAVY: mode=DIRECT, CoT убран

---

## ✅ 13.6 — ЗАКРЫТ (май 2026) — Media group aggregator

### Проблема
Telegram отправляет каждое фото из альбома как отдельный update с одинаковым `media_group_id`. Бот отвечал на каждое фото по отдельности — несколько раз подряд на один альбом.

### Решение

**Новый модуль `transport/telegram/media_group_aggregator.py`:**
- Redis-backed aggregator. Состояние целиком в Redis → работает при горизонтальном масштабировании (N инстанций)
- Debounce через TTL keyspace events: каждое новое фото сбрасывает TTL (1 сек). Когда TTL истекает → flush
- Lua-скрипты для атомарности: RPUSH + EXPIRE в одной операции; SETNX lock при flush (flush-once гарантия)
- Дедупликация по `message_id` через Redis SET (защита от Telegram duplicate updates)
- Немедленный flush при достижении 10 фото (лимит Telegram на альбом)
- `scoped_group_id = "{user_id}:{media_group_id}"` — изоляция между пользователями

**`transport/telegram/message_router.py`:**
- Добавлены `extract_media_group_id(update) -> str | None`
- Добавлен `extract_message_id(update) -> int`

**`transport/telegram/vision_handler.py`:**
- Добавлен `handle_vision_group(file_ids, caption, lang) -> VisionResult`
- Параллельный download всех изображений через `asyncio.gather()`
- Один Groq вызов с несколькими `image_url` в user_content
- Тот же `VisionResult` контракт что у `handle_vision()` — orchestrator не меняется
- Fallback: если group содержит одно фото → делегирует в `handle_vision()`

**`transport/telegram/update_handler.py`:**
- Добавлен параметр `app_state` (получает `request.app.state` из webhook)
- Photo-блок разветвляется: `media_group_id` присутствует → `aggregator.add(scoped_group_id, item)` → early return с пустым результатом (webhook не шлёт ответ). Одиночное фото → без изменений
- Агрегатор берётся из `app_state.media_group_aggregator`

**`app/bootstrap.py`:**
- `MediaGroupAggregator` стартует в `bootstrap()`, останавливается в `shutdown()`
- `state["media_group_aggregator"]` — доступен через app.state

**`app/main.py`:**
- `lifespan`: aggregator wired в `app.state`
- `_on_group_ready` callback переопределяется в lifespan — имеет доступ к `_send_message`, chat_id парсится из `scoped_group_id` prefix

**Redis keys per group:**
```
media_group:{uid}:{gid}       LIST    — serialised MediaGroupItem JSON
media_group:{uid}:{gid}:ttl   STRING  — debounce sentinel (EXPIRE)
media_group:{uid}:{gid}:lock  STRING  — flush-once guard (SETNX)
media_group:{uid}:{gid}:seen  SET     — deduplicated message_ids
```

**Требование к Redis конфигу:** `notify-keyspace-events Ex` (выставляется автоматически в `aggregator.start()`)


bash

python3 << 'EOF'
addition = """
---

## ✅ 13.6.1 — ЗАКРЫТ (май 2026) — Media group: баги агрегатора и изоляция контекста

### Контекст

§13.6 закрыл базовую проблему (бот отвечал на каждое фото альбома по отдельности).
После деплоя выявлены три новых бага в реализации — диагностика совместно с ChatGPT.

### Симптомы в продакшне

- Описывал 2 фото из 8 — остальные "не загрузились"
- Вторая партия из 10 фото смешивалась с первой
- Бот "возвращался к незавершённой задаче" — отвечал в контексте предыдущего альбома
- lang захардкожен как `"ru"` независимо от языка пользователя

### Диагностика (совместно с ChatGPT, май 2026)

ChatGPT выявил три корневые причины:

**1. Флашит слишком рано** — debounce запускается до того как все фото доставлены.
Telegram отправляет альбом не атомарно: `photo1 (media_group_id=123)` ... `photo10 (media_group_id=123)` — каждое отдельным update. Бот начинал обработку до получения всех фото.

**2. Нет reset после flush** — следующая партия смешивается с предыдущей.
`_LUA_FLUSH` приобретал `lock_key` через SETNX, но не удалял его — оставлял с `EXPIRE 30`.
Вторая партия в течение 30 секунд: `SETNX lock_key` → 0 → flush пропускался → группа терялась.

**3. "Возвращается к старым фото"** — история содержит предыдущие vision-ответы.
`_on_group_ready` → `handle_message` → загружает `conversation_history` для `user_id`.
История содержит ответы по предыдущему альбому → модель думает что продолжает.

**Что ChatGPT уточнил к плану:**
- Lock надо удалять атомарно внутри того же Lua скрипта (не держать после flush).
- Не обходить `handle_message` через прямой вызов `run()` — это сломает middleware, метрики, rate limiting. Правильно: добавить `input_type` в `OrchestratorRequest` и внутри `update_handler` при `input_type == "image_group"` пропустить загрузку истории.
- lang: брать из item с caption, затем из первого item, затем "ru" — не из первого item вслепую.

### Изменения (май 2026) ✅

**`transport/telegram/media_group_aggregator.py`** — два фикса:

*Фикс 1 — `_LUA_FLUSH`: атомарное удаление lock.*
Убран `EXPIRE lock_key 30`. Lock теперь удаляется в том же `DEL` что list_key, ttl_key, seen_key.
Атомарность сохранена: SETNX по-прежнему гарантирует что только один воркер входит в flush.
После DEL — clean slate: вторая партия стартует немедленно без ожидания.

```lua
-- было:
redis.call("EXPIRE", lock_key, 30)
local items = redis.call("LRANGE", list_key, 0, -1)
redis.call("DEL", list_key, ttl_key, seen_key)  -- lock_key НЕ удалялся

-- стало:
local items = redis.call("LRANGE", list_key, 0, -1)
redis.call("DEL", list_key, lock_key, ttl_key, seen_key)  -- все ключи атомарно
```

*Фикс 2 — `MediaGroupItem.lang`.*
Добавлено поле `lang: str = "ru"`. Сериализуется в JSON при `add()`, десериализуется при `_flush()`.

**`core/execution/orchestrator.py`** — `OrchestratorRequest` получил поле:
```python
input_type: str = "text"  # значения: "text", "image_group", "voice", "image"
```
Дефолт "text" → все существующие call-sites не затронуты.

**`transport/telegram/update_handler.py`** — два изменения:

*Сигнатура `handle_message`*: добавлен параметр `input_type: str = "text"`.

*Skip history load для `image_group`*:
```python
if supabase is not None and input_type != "image_group":
    # image_group: каждый альбом — самостоятельная задача.
    # Загрузка истории смешивает партии.
    ...get_history(...)
```
История по-прежнему **пишется** после ответа — следующий текстовый запрос получит корректный контекст.

`MediaGroupItem` получает `lang=lang` при создании в album-path.

`OrchestratorRequest` получает `input_type=input_type`.

**`app/main.py` — `_on_group_ready`** — три изменения:

*Lang резолюция* (убран TODO/хардкод `"ru"`):
```python
item_with_caption = next((i for i in items if i.caption), None)
lang = (
    item_with_caption.lang
    if item_with_caption
    else (items[0].lang if items else "ru")
)
```

*`handle_vision_group`*: теперь получает `lang=lang`.

*`handle_message`*: теперь получает `lang=lang` и `input_type="image_group"`.

### Архитектурный принцип

Каждый альбом = изолированная задача. История не загружается при обработке, но пишется после — пользователь может продолжить диалог текстом с корректным контекстом.
`input_type` в `OrchestratorRequest` — расширяемый механизм: в будущем аналогично можно изолировать другие типы входных данных без изменения pipeline.
"""

with open("/tmp/Ceyona-main/audit.md", "r") as f:
    content = f.read()

# Update header
content = content.replace(
    "**Статус:** 13.1, 13.5, 13.6, 17.3 закрыты. Открыто: 3 UX/качество + 1 архитектурный gap.",
    "**Статус:** 13.1, 13.5, 13.6, 13.6.1, 17.3 закрыты. Открыто: 3 UX/качество + 1 архитектурный gap."
)

# Update summary table
old_row = "| 17.3 | ✅ | Шаблонные ответы / отсутствие вариативности | prompt_engine, analysis, correction, synthesizer, vision_handler |"
new_row = """| 17.3 | ✅ | Шаблонные ответы / отсутствие вариативности | prompt_engine, analysis, correction, synthesizer, vision_handler |
| 13.6.1 | ✅ | Media group: lock bug, смешение партий, lang хардкод | media_group_aggregator, orchestrator, update_handler, main |"""
content = content.replace(old_row, new_row)

---

## ⚡ КРИТИЧЕСКОЕ АРХИТЕКТУРНОЕ ОТКРЫТИЕ — compound (май 2026)

### Диагноз

`groq/compound` и `groq/compound-mini` — **не tool-calling модели**. Это автономные агентные системы Groq со встроенными инструментами (web search, code execution). Кастомные tool schemas не поддерживаются — API возвращает `400 invalid_request_error: 'tool calling' is not supported with this model`.

Предыдущая архитектура (`compound_agent.py` передавал `_TOOL_SCHEMAS` + `tool_choice="auto"`) была архитектурно несовместима с природой этих моделей.

**Диагностика** подтверждена через `GET /debug` (добавлен в `main.py` май 2026):
- `groq_llm` ✅ — plain complete() работает
- `compound_mini` ❌ — 400 на tool_choice
- `compound_deep` ❌ — 400 на tool_choice
- `search`, `weather`, `maps`, `embedding` ✅ — все внешние сервисы работают

**Важно:** `/providers` проверяет только **наличие ключей**, не реальную доступность сервисов. Для диагностики использовать `/debug`.

### Принятое решение

**compound = синтезатор, не агент.**

Внешний retrieval (Tavily / SerpAPI / SearXNG / OpenWeatherMap / Mapbox) выполняется оркестратором до вызова compound. Compound получает готовый контекст в messages и синтезирует ответ через `groq_client.complete()` без tools.

**Почему это единственное правильное решение:**
- Сохраняет `source_credibility.py` фильтрацию (architecture §20)
- Сохраняет TruthMode.STRICT grounding invariant (architecture §10)
- Сохраняет ownership retrieval pipeline (architecture §3)
- Устраняет 400 ошибки
- compound как синтезатор поверх контролируемого контекста — это его правильная роль в governed системе

**Что НЕ делать:**
- ❌ Давать compound автономный поиск — теряем контроль источников, ломаем source_credibility и TruthMode.STRICT
- ❌ Адаптировать tool_choice параметры — compound не tool-calling модель по природе
- ❌ Делать fallback внутри одного агента

### Изменения (май 2026) ✅

**`agents/compound_agent.py`** — полная переработка:
- Удалено: `_TOOL_SCHEMAS`, `complete_with_tools`, tool loop, `_execute_tool`, `_build_tool_result_messages`
- Удалены импорты: `json`, `ToolCallResponse`, `external.maps`, `external.search`, `external.weather`
- Один вызов `groq_client.complete()`. Сигнатуры `run_fast()` / `run_deep()` не изменились — coordinator не трогается

**`core/execution/orchestrator.py`** — три изменения:
- `_NO_SEARCH_INTENTS` — только self-contained интенты: `creative, conversation, emotional, code, math`
- `_AGENTIC_TOOL_MAP` — каждый data-driven intent маппится на свой `web_tools` инструмент, контекст собирается до EPK
- STRICT gate — убрано `_is_agentic` исключение: если retrieval упал → gate срабатывает → нет галлюцинаций

**`app/main.py`** — добавлен `GET /debug`: реальные live-вызовы каждого сервиса с точным текстом ошибки.

**Не тронуто:** `groq_client.py` (complete_with_tools остаётся для будущего), `multi_agent_coordinator.py` (вызывает run_fast/run_deep — они корректны).

---

## ОТКРЫТЫЕ ПРОБЛЕМЫ

### ✅ 13.1 — ЗАКРЫТ (май 2026)
Все tool intents → «сервис недоступен». Причина: `tool_choice="auto"` не поддерживается compound моделями. Решение: архитектурная переработка compound как синтезатора (см. выше).

---

### 🟡 13.3 — CoT артефакты в финальном ответе (остаточные случаи)

**Симптом:** ответы содержат `Constraints / Candidates / Verification table`.

**Причина:** `_strip_cot_artifacts()` не покрывает vision → MATH/ANALYSIS classification.

**Статус:** основной infinite loop закрыт (17.1). Остаток — редкие случаи через vision-input.

---

### 🟡 13.4 — Classifier теряет контекст на follow-up сообщениях

**Симптом:** «Вот, нашла» / «Туговатый поиск» → CONVERSATION вместо правильного intent.

**Причина:** `_llm_pre_classify` получает только `text[:500]` без истории. Частично закрыт: history context добавлен для коротких сообщений (≤8 слов).

**Осталось:** asyncio stress tests (см. CI_README).

---

### ✅ 13.5 — ЗАКРЫТ (май 2026)

**Симптом:** описательный запрос («аниме про внучку якудзы с охранником») → поиск по сырому тексту → нерелевантные результаты.

**Причина:** `web_tools._search()` передавал user message в search provider as-is без реврайта.

**Решение (финальная архитектура):**

**`cognition/intent_engine.py`:**
- Добавлена функция `_understand_query(text) -> str`: семантический классификатор **KNOWN_ENTITY vs DESCRIPTIVE_SEARCH**. Один prompt к llama-3.1-8b-instant (FAST tier, max_tokens=30, temperature=0.0) — LLM определяет, знает ли пользователь точное название. KNOWN_ENTITY → запрос as-is. DESCRIPTIVE_SEARCH → краткий английский keyword query (3-8 слов) по уникальным признакам: роль, отношения, жанр, год, сеттинг. Никаких hardcoded списков слов — работает на всех 75 языках.
- `_understand_query()` вызывается в `classify()` **до** `_build_result()` — только для SEARCH intent (все три пути: pre_label route/accommodation/search, embedding path).
- `_build_result()` остаётся чистым структурным билдером: принимает готовый `query`, упаковывает в `IntentResult`. Никакой логики, никакого `if SEARCH` внутри.
- Удалён keyword fallback (`_WEATHER_KW`, `_SEARCH_KW`) — дублировал LLM pre-classifier и ломался на языках вне списка.
- SEARCH prompt очищен: убран micro-orchestrator («HOW TO ANSWER», «End with 1-2 useful links», «list 2-3 briefly and let the user confirm»). Оставлены 3 правила grounding: use ONLY ## CONTEXT, do not hallucinate, if nothing matches — say so honestly.
- Удалена ложная инструкция «3 search rounds» (compound — синтезатор, повторный вызов search невозможен).
- Восстановлены `async def classify(...)` и `async def _llm_pre_classify(...)` — заголовки функций были утеряны при §13.5 рефакторинге (merge артефакт). Тест CI #111 подтверждает.

**`external/web_tools.py`:**
- `_rewrite_search_query()` удалена — rewrite перенесён на правильный уровень (intent classification, не retrieval execution).
- `_search()` получает уже готовый query из `tool_params["query"]` — никакой трансформации в web_tools.

**`tests/test_orchestrator_web_search.py`:**
- `test_tool_intents_excluded` — переписан: проверяет `_AGENTIC_TOOL_MAP`, а не `_NO_SEARCH_INTENTS` (weather теперь agentic tool, не self-contained)
- `test_get_route_in_compound_tools` — переписан: проверяет `maps_route` в `_AGENTIC_TOOL_MAP` (compound больше не владеет tools)
- `test_compound_tools_complete` — переписан: проверяет полноту `_AGENTIC_TOOL_MAP` (инвариант перенесён с compound на orchestrator)

**Архитектурное соответствие:**
- Query understanding живёт в classify() — единственное правильное место (§2.1, §2.5).
- `_build_result` — pure structural builder, без логики и LLM-зависимостей.
- Новых модулей не создано. llama-3.1-8b-instant — паттерн существующий в кодовой базе (`_extract_poi_parts_via_llm`, `_extract_route_endpoints_via_llm`).

---

### ✅ 13.6 — ЗАКРЫТ (май 2026)
Бот отвечал на каждое фото альбома по отдельности. Решение: Redis-backed MediaGroupAggregator (см. выше).

---

### 🟡 17.2 — TruthMode как flag вместо verification layer

**Проблема:** TruthMode меняет стиль промпта, но не проверяет факты. LLM может галлюцинировать уверенно.

**Правильное решение:** одна функция `truth_check(answer, retrieval_context) -> float` в `execution_policy_kernel.py`. Retrieval = кандидаты, LLM = генератор, truth_check = судья.

**Что НЕ делать:** не создавать `truth/verifier.py` и другие новые модули — это замена файлов, не решение.

**Статус:** спроектировано. Реализация после стабилизации ответов.

---

## 🟡 ОТКРЫТАЯ ПРОБЛЕМА — Vision pipeline: QA/validation mode на альбомах (май 2026)

### Симптом
Альбом без caption → бот отвечает в режиме "проверки ограничений": таблицы, "ОК", пронумерованные пункты. Одиночное фото без caption → иногда SEARCH/ANALYSIS ответ вместо описания.

### Корневая причина (верифицирована)
**Граница между vision pipeline и intent engine нарушена.**

Vision output (`extracted`) попадал в `classify()` — это фундаментальная архитектурная ошибка. Classifier получал LLM-generated текст (описание изображений: "1. кружка, 2. пейзаж, 3. собака") и интерпретировал его как user intent → ANALYSIS/INSTRUCTION → QA-режим.

Цепочка: `extracted → classify() → ANALYSIS → pipeline LLM → таблицы/OK/проверка ограничений`

### Принятая итерация (май 2026)
**Файл:** `transport/telegram/vision_handler.py`

Три независимых изменения:

**1. Classifier работает только на caption — никогда на extracted:**
```python
# ДО (неправильно):
classify_input = f"{caption}\n\n{extracted}"  # LLM output в classifier
# ПОСЛЕ:
if caption.strip():
    intent_result = await classify(caption.strip(), lang=lang)
```

**2. Убран QA-триггер из `_GROUP_EXTRACTION_SYSTEM`:**
- Удалена строка `"If the images form a task (exam, problem set, instructions) — solve it."` из `_GROUP_SYNTHESIS_SYSTEM` — это был главный переключатель в validation mode
- Добавлен блок `ABSOLUTE RULES`: никогда не решать, не валидировать, не писать OK/fixed/satisfied

**3. Семантический контракт для фото без caption:**
```python
# Нет caption → фото без вопроса → описать напрямую
intent_result = IntentResult(intent=Intent.CONVERSATION, confidence=1.0)
needs_pipeline = _has_uncertainty  # False если extractor уверен
# needs_pipeline=False → extracted отдаётся пользователю напрямую, минуя pipeline и classifier
```
Это не хардкод — это семантическая истина: фото без вопроса не имеет классифицируемого user intent. `needs_pipeline=False` → `update_handler` отдаёт `vision_result.text` напрямую без orchestrator.

**4. Verbosity управляется кодом:**
```python
verbosity_rule = "1-2 sentences per image" if image_count >= 5 else "2-3 sentences per image"
system_prompt = _GROUP_SYNTHESIS_SYSTEM_TEMPLATE.format(image_count=..., verbosity_rule=...)
```
Детализация не интерпретируется моделью — передаётся как факт.

### Статус после деплоя
⚠️ **Частично улучшено, не закрыто полностью.**

Наблюдение (3:52): альбом с mixed content (Google search screenshot, кружка, биология, собака, обувь) → бот ответил `"Этномир\nSublimagia\nПроверьте Booking.com/2GIS/Google Maps для актуальных цен."` — это SEARCH intent, не описание.

**Диагноз последнего симптома:** `needs_pipeline=True` срабатывает когда `_has_uncertainty=True` (extractor вернул что-то неоднозначное) → extracted идёт в pipeline → там classifier всё ещё видит текст с названиями сайтов ("Этномир", "Sublimagia") → SEARCH intent → web search ответ.

Проблема в том что `_has_uncertainty` проверяет uncertainty signals в extracted, но не защищает от случая когда extracted содержит бренды/URL/названия — они тригерят SEARCH даже через `vision_intent=CONVERSATION` если `needs_pipeline=True`.

### Следующая итерация (НЕ реализована, требует обсуждения)

**Предложение ChatGPT (правильное архитектурно, но scope больше):**
Добавить `is_vision: bool` флаг в `OrchestratorRequest`. В orchestrator: если `is_vision=True` → пропустить intent classification полностью, использовать vision-specific path. Это жёсткое разделение потоков:
```
USER TEXT → intent_engine → orchestrator routing
VISION    → vision_handler → description LLM → ответ напрямую
```
Требует изменений: `OrchestratorRequest`, `orchestrator.py`, `update_handler.py`. Правильно для долгосрочного масштабирования.

**Почему не сделано сейчас:** scope и лимиты. Это следующая итерация.

### Что НЕ делать при следующей итерации
- ❌ Не добавлять больше `ABSOLUTE RULES` в промпты — это фильтрация симптомов
- ❌ Не форсировать intent через `IntentResult` для edge cases (таблица → CONVERSATION и т.д.) — система начнёт обрастать исключениями
- ❌ Не пытаться фильтровать extracted постфактум regex — правильно разделить источники данных
- ✅ `is_vision` флаг в OrchestratorRequest — единственное правильное долгосрочное решение

---

### 🟢 13.7 — Грузинский: i18n fallback некорректен

**Симптом:** вопрос на грузинском → «уточните вопрос» вместо «технический сбой».

**Файл:** `i18n/strings.py`, ключ `search_unavailable`, lang `ka`.

---

## ИСТОРИЯ РЕШЕНИЙ

### Нондетерминизм и классификация
- `_classify_complexity()` переписан: code detection только по fenced blocks, JSON требует key:value, threshold 800 chars
- `_build_messages()` принимает реальный tier — FAST/HEAVY получают разные instruction_prefix

### Governance
- Safety Gate: observability-only (non-blocking) — false-positive rate на русском/арабском/коротком тексте неприемлем
- `analysis.py` подключён: update_handler → analyse() → OrchestratorRequest.analysis_report → intent_engine.classify()
- `decision_matrix.py` читает пороги из policy_registry.RUNTIME

### Orchestration
- Web search routing перенесена из transport в orchestrator.run()
- forced_intent / _already_grounded coupling устранён → vision_intent: IntentResult | None
- Billing cascade исправлен: используется actual_tier из CoordinationResult

### Retrieval
- pgvector similarity_search() bug исправлен
- rerank_tokens считает реальные символы (1 token ≈ 4 chars)
- source_credibility.score_documents() активирован; source_url добавлен в MemoryRecord
- Retrieval при redis is None: деградирует без кэша с WARNING, не пропускается

### Billing
- UsageEntry заполняется полностью: intent, audio_seconds, tts_characters, tool_calls
- Speech billing columns через migrate_usage_log.sql; PGRST204 fallback до миграции

### Observability
- GET /metrics в main.py — in-memory JSON snapshot
- tracing.py переписан: structured JSON spans, trace_id через contextvars
- request_id = "{update_id}:{user_id}" — сквозная корреляция

### CI / Tests
- Test suite: EPK, safety gate, analysis, usage meter, intent hints, web search routing
- Coverage: 41% → ≥60%
- fly.toml: 8gb / performance-cpu-1x (healthcheck timeout fix)

### Search
- Three-tier fallback: Tavily → SerpAPI → SearXNG (self-hosted)

### Healthcheck
- asyncio.wait_for() 3s для Redis и Supabase; параллельные проверки через asyncio.gather
- asyncio.to_thread для sync Supabase call

### Conversation history
- Tier-зависимые бюджеты: FAST=1800, GENERAL=3500 tokens (было: 1200 для всех)
- SQL fetch limit: 20 → 40 turns

### CoT infinite loop (17.1)
- reasoning_engine.py: QUESTION на GENERAL/HEAVY → mode=DIRECT
- response_synthesizer._strip_cot_artifacts(): Mode A (pure CoT loop), Mode B (partial stripping)

### Balance guards
- Web search и vision fast-path пропускаются при user_balance ≤ 0

### Media group (13.6)
- Новый модуль: `transport/telegram/media_group_aggregator.py` — Redis debounce, Lua atomicity, flush-once SETNX
- `message_router.py`: `extract_media_group_id()`, `extract_message_id()`
- `vision_handler.py`: `handle_vision_group()` — батч vision, параллельный download
- `update_handler.py`: `app_state` param, media_group routing
- `bootstrap.py` / `main.py`: aggregator lifecycle + callback wiring

---

## СВОДНАЯ ТАБЛИЦА ОТКРЫТЫХ ПУНКТОВ

| # | Приоритет | Описание | Файлы |
|---|---|---|---|
| 13.3 | 🟡 | CoT артефакты (остаточные случаи) | response_synthesizer, vision_handler |
| 13.4 | 🟡 | Classifier теряет контекст на follow-up | intent_engine._llm_pre_classify |
| 17.2 | 🟡 | TruthMode как flag, не verification layer | execution_policy_kernel |
| 17.3 | ✅ | Шаблонные ответы / отсутствие вариативности | prompt_engine, analysis, correction, synthesizer, vision_handler |
| 13.7 | 🟢 | Грузинский i18n fallback некорректен | i18n/strings.py |

---

## ✅ 17.3 — ЗАКРЫТ (май 2026) — Шаблонные ответы и отсутствие вариативности

### Проблема

Бот стабильно начинал ответы одинаковыми фразами — особенно на vision-запросы (фото, альбомы), но и на обычные текстовые тоже. Три наблюдаемых симптома:

1. **Vision path:** бот отвечал `"Изображения представляют собой..."` / `"Похоже, что у нас есть задача по биологии..."` — мета-комментарий вместо ответа по существу.
2. **Текстовые follow-up:** после vision-диалога бот писал `"Этот вопрос не связан с содержимым альбома..."` — тащил контекст предыдущего vision-разговора.
3. **Повтор стиля:** на одинаковый тип запроса бот отвечал идентично 2-3 раза подряд.

### Диагностика (совместно с ChatGPT, май 2026)

ChatGPT выявил **четыре корневые причины:**

1. **Prompt bias** — системный промпт или few-shot примеры создают шаблон.
2. **Response synthesizer делает шаблон** — post-processing унифицирует стиль.
3. **Temperature / sampling слишком стабильные** — модель выбирает одни и те же формулировки при одинаковых входах.
4. **LLM "находит локальный минимум"** и зацикливается.

**Дополнительно выявлено при анализе кода:**

- `_GROUP_EXTRACTION_SYSTEM` (vision_handler) не имел OUTPUT FORMAT правил в отличие от `_EXTRACTION_SYSTEM` — экстрактор для альбомов сам писал `"Изображения представляют собой..."`.
- `prompt_engine.py` содержал мёртвую инструкцию `"Never start two consecutive responses the same way"` — мёртвую, потому что модель не видела свои предыдущие ответы в нужном формате.
- История уже содержала assistant-туры (`role: assistant`) — проблема не в хранении, а в том что prompt_engine не вытаскивал их для явного контроля вариативности.
- `correction.py` не покрывал множественное число: `"Изображения представляют собой"` (plural) проходил мимо regex.
- `meta/analysis.py` анализировал только входящий текст пользователя — исходящий ответ не проверялся никем.

### Что сказал ChatGPT (архитектурное решение)

**Стратегия трёх уровней:**

```
Уровень 1 — Default (strip opener)           — 0 токенов, мгновенно, детерминировано
Уровень 2 — Smart guard (detect + strip)     — редко, быстро, лучше
Уровень 3 — Всегда регенерировать            — НЕ делать: сжигает токены, latency, нестабильность
```

**Регенерация = fallback, не основной инструмент.** Retry только если:
- Повторяется несколько ответов подряд
- Стиль реально ломает UX
- Простой strip делает текст хуже (обрывает смысл)
- Ответ короткий и весь состоит из шаблона

**Идеальная архитектура для проекта:**
```
vision_handler
    ↓
orchestrator
    ↓
prompt_engine  →  inject variation hints (history-aware)
    ↓
LLM
    ↓
meta.analysis  →  detect repetition
    ↓
meta.correction  →  light fix (no regen by default)
    ↓
response_synthesizer
```

**Дополнительно (variation layer):**
- `adaptive temperature`: если `context.is_repeated_query` → temperature 0.7, иначе 0.4
- `anti-repeat hint` в prompt: `"The user has asked a similar question before. Avoid repeating the same wording."`
- `history-aware variation`: `"Previous answers: {last_answers}. Avoid repeating these responses."`
- `Vision-specific фикс`: `"When describing images, vary structure and wording. Do not reuse previous phrasing."`

**Чего НЕ делать:**
- ❌ Запрещать конкретные фразы (whack-a-mole — модель найдёт синоним)
- ❌ Всегда регенерировать
- ❌ Игнорировать проблему

### Принятое решение

Реализованы направления 1 и 2 без регенерации.

### Изменения (май 2026) ✅

**`llm/prompt_engine.py`** — history-aware variation:
- Вместо мёртвой инструкции `"Never start two consecutive responses the same way"` — реальный механизм.
- Из `ctx.conversation_history[-6:]` извлекаются последние 3 assistant-ответа.
- Первые 80 символов каждого → `_recent_openings`.
- Если есть история: `"Your recent responses started with: '{o1}'; '{o2}'; '{o3}'. Do NOT start this response the same way. Vary your opening naturally."` — inject в system как core constraint (insert(1), перед truth block).
- Если нет истории: базовое правило вариативности без конкретики.

**`meta/analysis.py`** — новая функция `detect_repetitive_opening(text, history)`:
- Анализирует **исходящий** ответ (не входящий — это было слепое пятно).
- `_RE_TEMPLATED_OPENERS` — compiled regex на известные шаблонные opener'ы (RU + EN): `"похоже, что"`, `"этот вопрос"`, `"данный вопрос"`, `"изображение/изображения представляет/представляют"`, `"на данном/этом/всех изображениях"`, `"поскольку у меня нет"`, `"я не могу просмотреть"`, `"it seems like/that"`, `"this question/image/request"`, `"the image shows/depicts/represents"`.
- **Два условия оба должны выполниться** (smart guard, не blacklist):
  1. Ответ начинается с шаблонного opener'а.
  2. Тот же opening (первые 50 символов) уже встречался в последних 3 assistant-турах истории.
- `True` → opener шаблонный И повторяется → strip. `False` → оставить как есть.
- Если opener шаблонный но первый раз → `correction.py` patterns перехватят как fallback.
- Никаких LLM-вызовов. Никаких дополнительных токенов. Никогда не бросает исключение.

**`meta/correction.py`** — расширены preamble patterns:
- Добавлены Russian meta-commentary openers: `"Похоже, что у нас есть..."` (с `.+\n+`), `"Этот вопрос не связан с..."`, `"Данный вопрос..."`, `"Изображение представляет собой"` (ед.ч.), `"Изображения представляют собой {phrase}.\n"` (мн.ч.), `"На данном/этом/всех/представленных изображениях {phrase}.\n"`.
- Strip opener — контент после него сохраняется. Не blacklist — не запрещаем фразы, убираем артефакт.
- Реальные случаи из продакшна протестированы regex-тестом перед деплоем: все 4 варианта стрипаются до чистого контента.

**`cognition/response_synthesizer.py`** — подключение `detect_repetitive_opening`:
- `SynthesisInput` получил поле `conversation_history: list[dict] | None = None`.
- `_apply_correction(text, history)` — принимает историю, вызывает `detect_repetitive_opening()` перед `correction.apply()`.
- Smart guard: если detects повтор → `apply()` уже имеет нужные patterns → strip. Без регенерации.

**`core/execution/orchestrator.py`** — все три `SynthesisInput(...)` call-sites:
- Добавлен `conversation_history=request.conversation_history` во все основные SynthesisInput вызовы (lines 304, 380, 478). Deny-path вызовы (157, 731) не обновлялись — там нет реального контента.

**`transport/telegram/vision_handler.py`** — `_GROUP_EXTRACTION_SYSTEM` переписан:
- Добавлены те же 4 RULE блока что в `_EXTRACTION_SYSTEM` (TEXT/TASK, ANIMATED CHARACTER, REAL PERSON, OTHER).
- Добавлен OUTPUT FORMAT блок с явным запретом: `"Do NOT use meta-commentary openers like 'The images show', 'These images represent', 'Изображения представляют собой', 'На изображениях'..."`.
- `"Start each image description directly with its content."` — экстрактор теперь по контракту начинает с контента.
- Это решает проблему на уровне источника — не только стрипает постфактум, но предотвращает генерацию.

### Что осталось (не реализовано, следующий шаг)

- **Adaptive temperature** — `get_temperature(context)`: если `context.is_repeated_query` → 0.7, иначе текущая. Требует изменений в `reasoning_engine.py` и добавления `is_repeated_query` флага в OrchestratorRequest. Запланировано.
- **Регенерация как fallback** — условный retry при повторе 2-3 раза подряд. Не реализована намеренно (дополнительный LLM-вызов = токены + latency). Реализовать если текущих изменений недостаточно.

### Тест результатов (деплой май 2026)

После первого деплоя (без vision_handler фикса): `"Изображения представляют собой..."` продолжал появляться — plural форма не была в patterns, `_GROUP_EXTRACTION_SYSTEM` не был исправлен.

После второго деплоя (все файлы): тест regex подтверждён локально. Production наблюдение продолжается.

---

📋 **CI (planned):** coverage floor 75%, asyncio stress tests (13.4), integration tests compound pipeline, retrieval quality regression, mypy.