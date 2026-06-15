# CEYONA — АНАЛИЗ СЕССИИ 3
**Дата:** май 2026  
**Источники:** audit.md, architecture.md, models.md, economic.md, CI_README.md + 37 скринов обсуждений с ChatGPT  
**Статус:** аналитический документ — не заменяет audit.md, дополняет его  
**Обновлён:** май 2026 (сессия 3 — закрыты B, C, D, 8.1)

---

## 1. ЧТО БЫЛО СДЕЛАНО К МОМЕНТУ ОБСУЖДЕНИЙ (сессия 2, закрыто)

Задачи 18.1–18.4 закрыты и задеплоены:

| # | Суть | Файл | Статус |
|---|------|------|--------|
| 18.1 | `_GROUP_SYNTHESIS_SYSTEM_TEMPLATE`: запреты → target pattern, убраны `Part N:` | vision_handler.py | ✅ |
| 18.2 | `_vision_image_context` не передавался в pipeline → инжект в `retrieved_context` | update_handler.py | ✅ |
| 18.3 | Нумерация "Первое/Второе изображение" — constraint в `_GROUP_EXTRACTION_SYSTEM` | vision_handler.py | ✅ |
| 18.4 | Guardrail `_MAX_GROUP_IMAGES=6` + `too_many_images` i18n (28 языков) | vision_handler.py, strings.py | ✅ |

**Подтверждено кодом:** все четыре фикса присутствуют в актуальной версии файлов.

---

## 2. ПОДТВЕРЖДЁННЫЕ ОТКРЫТЫЕ ЗАДАЧИ (из audit.md, верифицированы кодом)

### 🔴 19.x — Global formatting contract

**Проблема:** паттерн нумерации и шаблонных открытий потенциально кросс-слойный. Фикс 18.3 закрыл extraction, но тот же паттерн может всплыть в:
- synthesis (если descriptions приходят с нумерацией от другого источника)
- core/LLM если image_descriptions уходят в user_message без контракта
- retrieval/context если контекст содержит нумерованные структуры

**Верифицировано кодом:** `_GROUP_EXTRACTION_SYSTEM` содержит нужный constraint — ordinal labels запрещены. `_GROUP_SYNTHESIS_SYSTEM_TEMPLATE` — target pattern без запретов, корректно.

**Решение (спроектировано, не реализовано):**
- Уровень 1 (сделан — 18.3): локальный constraint в extraction
- Уровень 2 (не сделан): global formatting rule в LLM/response layer:
  ```
  Do not introduce structure not present in input.
  Do not enumerate unless explicitly required by user.
  ```
  ИЛИ `normalize_output()` post-processing в meta слое (remove_ordinals + remove_numbering)

**Приоритет:** средний. Реализовывать только если паттерн всплывёт снова после 18.3.

---

### 🟡 13.3 — CoT артефакты (остаточные случаи)

**Симптом:** `Constraints:`, `Candidates:`, `Verification table` в ответе.

**Верифицировано кодом:** `_strip_cot_artifacts()` в `response_synthesizer.py` реализован. Покрывает: Mode A (loop detection), Mode B (header stripping — Constraints, Candidates, Verification). НО: путь `vision → MATH/ANALYSIS classification` не тестируется отдельно.

**Что не покрыто:** если vision-запрос классифицируется как MATH/EXAM, CoT не стрипится (это intentional по коду — `from_vision=True` форсирует стриппинг). Проверить нужно только комбинацию: vision + не-MATH intent + CoT в ответе.

**Файлы:** `cognition/response_synthesizer.py` (строка 266+), `transport/telegram/vision_handler.py`.

---

### 🟡 13.4 — Classifier теряет контекст на follow-up

**Симптом:** короткое сообщение типа `"Вот, нашла"` → CONVERSATION вместо правильного intent.

**Верифицировано кодом:** частичный фикс присутствует. В `intent_engine.py` строка 428+: история инжектируется для сообщений `len(text.split()) <= 8`. Берутся последние 4 хода (2 пары), макс 150 символов на ход.

**Что осталось:** asyncio stress tests (13.4) — в CI_README.md отмечены как planned. Без стресс-тестов нет уверенности в корректности при concurrent запросах.

**Файл:** `cognition/intent_engine.py` → `_llm_pre_classify`, строка 388+.

---

### 🟡 17.2 — TruthMode как flag, не verification layer

**Симптом:** TruthMode меняет стиль промпта (`STRICT`/`HYBRID`), но не проверяет факты.

**Верифицировано кодом:** подтверждено. `TruthMode` используется в `orchestrator.py` как инструкция LLM ("не галлюцинируй") через `_build_messages()`. `truth_check(answer, retrieval_context) -> float` в `execution_policy_kernel.py` отсутствует полностью — функции нет ни в одном файле.

**Правильное решение:** `truth_check()` как отдельный verification pass: retrieval = кандидаты, LLM = генератор, truth_check = судья.

**Статус:** спроектировано, реализация после стабилизации vision.

---

### 🟢 13.7 — Грузинский i18n fallback

**Файл:** `i18n/strings.py`, ключ `search_unavailable`, lang `ka`. Простая строка — быстрое закрытие.

---

### 🟡 13.1 — tool intents → "сервис недоступен" (из models.md)

**Статус:** по models.md §6 — БАГ ОТКРЫТ. Groq/compound и groq/compound-mini подтверждены доступными на аккаунте. Вероятные причины: SERPAPI_KEY / OPENWEATHER_API_KEY не заполнены, либо compound-mini требует другой параметр tool_choice, либо таймаут.

**Действие:** `fly logs -a имя_приложения | grep compound_agent` — нужны реальные логи.

---

### 🔴 21.1 — Email уведомления (Brevo) — opt-in

**Проблема:** `event_notifier.py` реализован, `email_service.py` подключён, `BREVO_API_KEY` в секретах есть. Но email пользователя неоткуда взять — Telegram Bot API не передаёт его даже если пользователь регистрировался через email. Функция фактически мертва.

**Верифицировано кодом:** `event_notifier.on_balance_exhausted()` и `on_balance_credited()` отправляют письма только если `to_email` передан. Нигде в pipeline `to_email` не заполняется — значит письма не уходят никогда.

**Решение (спроектировано):**
- пользователь вводит email вручную через `/settings` или отдельный флоу
- новая таблица Supabase `user_notifications`:
  ```
  user_id
  email
  notify_balance_exhausted: bool  (default: false)
  notify_balance_credited: bool   (default: false)
  ```
- строгий opt-in — оба флага выключены по умолчанию
- `event_notifier.py` проверяет флаги перед отправкой
- тексты писем переписать в голосе Сэёны (текущие шаблоны корпоративные)

**Что слать:** только `balance_exhausted` (пользователь офлайн, пропустил) и опционально `balance_credited`. `safety_block` и `system_error` — только в логи / Sentry, не пользователю.

**Файлы:** `notifications/email_service.py`, `notifications/event_notifier.py`
**Приоритет:** низкий — требует UI для сбора email, нет срочности.

---

## 3. НОВЫЕ ПРОБЛЕМЫ — ВЫЯВЛЕНЫ В ОБСУЖДЕНИЯХ

### 🔴 A — Нет единой точки истины для формата ответа (Final Authority Layer)

**Суть проблемы (из обсуждений):** `vision_handler.py` вырос с 200 до 714 строк, `update_handler.py` до 707 строк. Код растёт, качество ответов не улучшается пропорционально.

**Корень:** поведение (формат, стиль) чинится на уровне промптов в разных слоях, но нет единой точки финального контроля. Каждый слой может "додумать" стиль заново:
- extraction layer
- synthesis layer  
- core/LLM layer
- meta/formatting layer

**Архитектурное несоответствие:** в `architecture.md §19` описан 7-step pipeline synthesizer. Steps 5 (correction) и 6 (output_normalizer) — это ближайший аналог Final Authority Layer. Но они не покрывают vision-специфичные артефакты (нумерация, "представляет собой").

**Решение:** добавить в `meta/output_normalizer.py` (step 6 synthesizer) обработку vision-артефактов — это не новый слой, это расширение уже существующего механизма в правильном месте. Не нарушает §2.1 (Single Policy Authority).

---

### ✅ B — i18n слой: рефакторинг (май 2026)

**Суть проблемы:** `strings.py` вырос до 1355 строк. Основная причина: попытка решить через код то, что LLM умеет делать сама.

**Сделано:**
- `LANG_INSTRUCTIONS` (51 строка, 50 языков) → `_LANG_ALIASES` (8 записей только для реально неоднозначных кодов: `zh`, `pt-br`, `zh-cn`, `zh-tw`, `sr`, `bs`, `ug`, `tt`)
- `lang_instruction()` переписана: нормализация регистра (`lower`/`strip`) + алиасы. Без guard — `lang` нормализован через `normalize_lang()` до вызова, мусор физически не доходит
- `help_display`: 8 языков → en+ru (описательный текст — LLM-домен, не инфраструктура)
- `emotional_fallback`: 47 языков → 4 (en/ru/ar/zh), текст стал нейтральным системным сообщением
- Дубль `maps_not_found` удалён (оставлен полный вариант с 34 языками)
- Итог: 1356 → 1216 строк (−140)

**Примечание по цели ~150–200 строк:** нереалистична. 1216 строк объясняются 50+ языками × инфраструктурные ключи (weather, maps, balance, errors). Всё оставшееся — необходимо.

**Принцип зафиксирован:** код — для ограничений и инфраструктуры. LLM — для смысла и контента.

**Файл:** `i18n/strings.py`
**Статус:** ✅ закрыт

---

### ✅ C — Логирование поэтапного вывода vision pipeline (май 2026)

**Суть:** при дебаге нумерации две недели чинили не тот слой. Причина — не было логов промежуточных состояний.

**Верифицировано кодом:** все метки присутствуют в `vision_handler.py`:
- `[vision_input]` — single (L235) и album (L626)
- `[after_extraction]` — single (L329) и album (L718)
- `[after_synthesis]` — album (L730)
- `[final_routing]` — single (L375) и album (L736)

Покрывает оба пути (single image + album). Blind debugging исключён.

**Файл:** `transport/telegram/vision_handler.py`
**Статус:** ✅ закрыт (верифицировано по коду)

---

### ✅ D — Vision токены в usage_meter (май 2026)

**Суть:** прямые Groq вызовы из vision_handler без биллинга → revenue leak.

**Верифицировано кодом:**
- `vision_handler.py` собирает `vision_input_tokens` / `vision_output_tokens` из Groq API response (поля `prompt_tokens` / `completion_tokens`)
- `update_handler.py` вызывает `vision_actual_cost()` из `cost_model.py` с этими токенами
- `cost_model.py` содержит `vision_actual_cost()` с тарифами `VISION_MODEL_RATES` и комментарием `# Used exclusively by vision_handler for image extraction`
- При `cost_usd == 0` (failure) биллинг пропускается — корректно

Revenue leak закрыт. Биллинг vision вызовов работает.

**Файлы:** `transport/telegram/vision_handler.py`, `transport/telegram/update_handler.py`, `core/kernel/cost_model.py`
**Статус:** ✅ закрыт (верифицировано по коду)

---

### 🟡 E — batching pipeline: текущая архитектура vs правильная

**Текущее состояние (из кода):**
- `_MAX_IMAGES_PER_BATCH = 4`
- Батчи обрабатываются параллельно через `asyncio.gather`
- При >1 батче вызывается `_synthesise_batch_descriptions()`
- Guardrail: `_MAX_GROUP_IMAGES = 6` → при текущем лимите второй батч никогда не создаётся (6 фото / batch_size 4 = max 2 батча, но guardrail не даёт >6)

**Проблема:** `_synthesise_batch_descriptions()` не имеет cross-batch reasoning. Если пользователь спрашивает "что общего на всех фото?" — каждый батч видит только часть. Synthesis делает формальное объединение, а не семантическое сравнение.

**Правильная архитектура (спроектирована в обсуждениях):**
- Stage 1: batch processing → partial insights per batch
- Stage 2: synthesis → final answer с cross-batch awareness
- Stage 3: optional refinement для сложных вопросов

**Приоритет:** средний. Текущий guardrail 6 фото делает это менее критичным прямо сейчас. Реализовывать на Этапе 2 (после стабилизации текущих фиксов).

---

### 🟡 F — CI: coverage floor 60%, нужно 75%

**Из CI_README.md:** текущий floor 60%, цель 75%.

**Что не покрыто тестами:**
- speech/billing тесты
- asyncio stress tests (13.4)
- integration tests compound_agent tool execution (13.1 regression)
- retrieval quality regression
- mypy type checking

**Из audit.md:** все эти пункты помечены как planned. Реализация блокирована стабилизацией vision.

---

## 4. ИНСАЙТЫ ИЗ ОБСУЖДЕНИЙ — ДЛЯ ДОКУМЕНТИРОВАНИЯ

### Принципы, выработанные в сессии

**Про дебаг:**
- Проблему ищи по горизонтали (поток данных), а не по вертикали (слои)
- "Чинить слой" — тупик. "Проследить поток данных" — решение
- Без логов `[after_extraction]` / `[after_synthesis]` ты слепая

**Про архитектуру:**
- Код растёт ≠ система становится лучше. 714 строк хуже 200, если проблема межслойная
- Масштабируемость = предсказуемое поведение, а не больше кода
- "Не каждый повторяющийся паттерн = архитектурная проблема. Иногда это просто утечка поведения из одного слоя"

**Про LLM vs код:**
- Код — для ограничений (физических: лимиты, rate limits, технические ошибки)
- Модель — для смысла (язык, стиль, объяснения, форматирование)
- Не дублировать в коде то, что уже умеет LLM

**Про эволюционный подход:**
- Этап 1: guardrail сейчас (лимит + сообщение пользователю)
- Этап 2: batching + простая конкатенация
- Этап 3: synthesis слой с cross-batch reasoning
- Правило: "guardrail сейчас → архитектура потом"

**Про костыли vs правильные решения:**
- `images[:6]` — костыль (теряешь данные, пользователь не знает)
- `if len > 6: return too_many_images` — приемлемый guardrail ✅ (реализован в 18.4)
- batching с synthesis — архитектурное решение (следующий этап)

---

## 5. СОСТОЯНИЕ ФАЙЛОВ — АКТУАЛЬНО

| Файл | Строк | Статус | Проблема |
|------|-------|--------|----------|
| `transport/telegram/vision_handler.py` | 714 | Актуален, фиксы 18.x задеплоены | Нет поэтапных логов (C) |
| `transport/telegram/update_handler.py` | 707 | Актуален, 18.2 задеплоен | Нет поэтапных логов (C) |
| `i18n/strings.py` | 1216 | ✅ Рефакторинг B закрыт | — |
| `cognition/intent_engine.py` | 541 | 13.4 частично закрыт | Нет стресс-тестов |
| `cognition/response_synthesizer.py` | 416 | 7-step pipeline корректен | 13.3 не полностью покрыт |
| `llm/prompt_engine.py` | 120 | Компактный | — |

---

## 6. ПРИОРИТИЗИРОВАННЫЙ СПИСОК ДЕЙСТВИЙ

### Немедленно
1. Убедиться что 18.3 держит в продакшне (мониторинг нумерации в логах)
2. ~~Добавить логи vision pipeline (C)~~ — ✅ закрыто

### Ближайшие задачи
3. ~~Ревизия strings.py (B)~~ — ✅ закрыто
4. ~~Vision токены в usage_meter (D)~~ — ✅ закрыто
5. Закрыть 13.7 (грузинский i18n fallback — строка в strings.py)
6. Диагностика 13.1 через `fly logs | grep compound_agent`

### После стабилизации
7. Реализовать global formatting rule (19.x уровень 2) — только если паттерн всплывёт снова
8. Реализовать `truth_check()` для 17.2
9. Asyncio stress tests для 13.4
10. Поднять CI coverage до 75%

---

## 8. ПОЛНЫЙ АУДИТ ПО 37 СКРИНАМ (сессия 3 — Claude, май 2026)

### 8.0 — Что обсуждалось в 37 скринах: полный список тем

Скрины 1–4 (19:16): pipeline как система, разделение "как думать" vs "как говорить", слои cognition/llm/meta/contracts, предложение VisionResponseMode.
Скрины 5–12 (3:37): причина 2 недель дебага (_GROUP_SYNTHESIS вместо _GROUP_EXTRACTION), кто прав локально vs стратегически, cross-layer паттерн нумерации, два уровня решения (локальный + global rule), batching pipeline без cross-batch reasoning.
Скрины 13–16 (3:37–3:38): контракт данных (Extraction output: plain descriptions, no ordering), "чинить слой — тупик", поток данных vs вертикальные слои, поэтапные логи, Final Authority Layer, голос vs изображения.
Скрины 17–20 (3:37–3:40): guardrail 6 фото (правильное решение), классификация костыль/guardrail/архитектура, batching pipeline (Stage 1→2→3).
Скрины 4, 6, 10–12, 14, 16 (4:21–4:22): i18n разрастание до 1400 строк, Lingua vs мультиязычность через модель, что убрать из strings.py, "код для ограничений — модель для смысла", Final Authority Layer (ввести одну точку контроля финального текста).

---

### ✅ 8.1 — Мёртвый DENY-check в update_handler (май 2026)

**Суть:** `safety_gate.py` всегда возвращает `GateVerdict.PASS`, но три места в `update_handler.py` проверяли `gate.verdict == GateVerdict.DENY` — мёртвый код.

**Верифицировано кодом:** все три ветки заменены комментарием:
```
# DENY branch removed: safety_gate v2 (May 2026) is observability-only.
```
(строки 163, 364, 395 актуальной версии)

**Файл:** `transport/telegram/update_handler.py`
**Статус:** ✅ закрыт (верифицировано по коду)

---

### 8.2 — i18n/strings.py: что реально используется и где

**strings.py используется в следующих слоях (верифицировано grep):**

- `external/weather.py` → `_t("weather_feels_like", lang)`, `_t("weather_humidity", lang)`, `_t("weather_wind", lang)` — локализованные метки weather-карточки. Убирать нельзя, LLM их не генерирует — они часть форматированного вывода.
- `external/maps.py` → `_t("maps_coord_label", ...)`, `_t("maps_poi_result", ...)`, `_t("maps_route_result", ...)`, `_t("maps_not_found", ...)` — все user-facing строки maps приходят из i18n. Правильно.
- `cognition/response_synthesizer.py` → `_t` для deny-сообщений, truncation_suffix, emotional_fallback.
- `cognition/multi_agent_coordinator.py` → `_t` для блокирующих сообщений safety_agent.
- `transport/telegram/update_handler.py` → `get_system_message` в 8+ местах для ошибок pipeline.
- `transport/telegram/vision_handler.py` → `t("vision_error", lang)`, `t("too_many_images", lang)`.
- `transport/telegram/webhook.py` → UI-строки, low_balance_warning.
- `meta/output_normalizer.py` → `SUPPORTED_LANGS` для валидации _LEAK_MAPS.
- `llm/prompt_engine.py` и `cognition/intent_engine.py` → `lang_instruction(lang)` — теперь через `_LANG_ALIASES`.

**`LANG_INSTRUCTIONS` удалена** (май 2026, пункт B). Заменена на `_LANG_ALIASES` (8 записей для неоднозначных кодов) + `lang_instruction()` с нормализацией регистра. Архитектура корректна: нет `if lang ==` веток, нет `translate()`.

**Итоговое состояние strings.py:** 1216 строк. Оставшееся — необходимо: weather-метки, maps-строки, системные ошибки, balance/billing, UI-кнопки. Цель ~150–200 строк была нереалистична при 50+ языках.
---

### 8.3 — Полный аудит слоёв влияющих на ответы бота

#### transport/ (update_handler, vision_handler, webhook)

**Состояние:** pipeline соответствует architecture.md §4. Порядок: Safety Pass 1 → complexity → multilingual → Safety Pass 2 → analysis → history → retrieval → orchestrator.

**Проблемы:**
- Три мёртвых DENY-check (строки 166, 372, 415 update_handler) — safety_gate всегда PASS. Технический долг, не функциональный баг.
- `is_vision` определяется через `locals().get("_vision_text_override") is not None` — хрупко. Работает, но если имя переменной изменится — сломается молча без ошибки.
- Vision токены групповых батчей (`_call_groq_vision`, `_synthesise_batch_descriptions`) не биллятся. Fast-path биллится через hardcoded `$0.001` — неточно. Revenue leak при интенсивном использовании.
- **Нет поэтапных логов** `[vision_input]` / `[after_extraction]` / `[after_synthesis]` / `[final_output]`. Главная причина 2 недель слепого дебага.

---

#### cognition/ (intent_engine, reasoning_engine, multi_agent_coordinator, response_synthesizer)

**intent_engine:**
- System prompts для каждого intent детальные и продуманные. `_NO_CUTOFF` блок корректен. `_FORMAT_RULES` применяется где нужно.
- `_llm_pre_classify` с history context для сообщений ≤ 8 слов (§13.4 частично закрыт). Asyncio stress tests не написаны.
- **analysis_hints реально используется** в classify(): IS_SHORT/IS_MULTILINGUAL поднимают effective_min порог, HAS_CODE_BLOCK снижает. Это правильная интеграция meta → cognition без нарушения authority.

**reasoning_engine:**
- Матрица (Intent, Tier) → ReasoningStrategy корректна. instruction_prefix'ы защищают от CoT утечки через явные запреты ("Never list internal reasoning steps").
- Нет стратегий для EMOTIONAL, WEATHER, SEARCH, MAPS — они идут через default FAST plan. Это правильно: для этих intent'ов CoT не нужен.

**multi_agent_coordinator:**
- Все agentic intents (WEATHER, MAPS, MAPS_POI, MAPS_ROUTE, SEARCH) → compound_agent. Архитектурное решение май 2026, задокументировано в audit.md §12.1.
- EMOTIONAL → FAST с temperature=0.85. Правильно — тепло, быстро, без CoT.
- CREATIVE → consensus=True с FAST validator. Разумно для качества.

**response_synthesizer:**
- 7-step pipeline соответствует architecture.md §19.
- `_strip_cot_artifacts` — два режима (loop detection + header stripping). `from_vision=True` форсирует strip даже для MATH/EXAM. Правильно.
- `_apply_correction` с history-aware детекцией повторений через `detect_repetitive_opening` из meta/analysis. Правильная интеграция.
- **variation_rule вставляется на позицию 1 всегда** через `system_parts.insert(1, ...)`. Для EMOTIONAL может конфликтовать с "Keep it SHORT (1-3 sentences)" из intent prompt. Конфликт не критичный, но есть.
- **13.3 не полностью закрыт:** vision + не-MATH intent + CoT в ответе не покрыт отдельными тестами.

---

#### llm/ (prompt_engine, model_router, groq_client)

**prompt_engine (120 строк — компактный):**
- Правильный порядок: lang_instruction → variation_rule → intent system_prompt → truth_mode → history → user_message+context.
- Context инжектируется в user turn, не в system — правильно для small models (они читают user turn ближе к генерации).
- History-aware variation: извлекает последние 3 opening фразы assistant и явно запрещает их повторение. Это конкретная, actionable инструкция — не абстрактная.

---

#### meta/ (analysis, correction, output_normalizer, reflection, memory_audit)

**meta/analysis.py:**
- Pure function, no I/O. Структурный анализ (code blocks, math, URLs, script detection, length).
- `detect_repetitive_opening` — используется в response_synthesizer для smart guard повторений. Правильно.
- Hints передаются в intent_engine как non-binding — не нарушает Single Policy Authority.

**meta/correction.py:**
- Паттерны preamble для RU/EN/DE/FR/ES/TR/KA/AR.
- Паттерны для "изображение представляет собой" (строки 37–39) **уже есть**. Это и есть та "Final Authority Layer" которую ChatGPT предлагал добавить — она существует в correction.py.

**meta/output_normalizer.py:**
- Source tags, garbled URLs, language leak maps для 30+ языков.
- **Vision-специфичные артефакты ("На изображении видно...", "Данное изображение демонстрирует...")** не покрыты здесь. Частично покрыты в correction.py (строки 37–39), но не полностью. Это 19.x уровень 2 — реализовывать только если 18.3 не держит.

---

#### retrieval/ (retrieval_engine, source_credibility, reranker)

- Полностью изолирован от стиля ответа. Только данные.
- source_credibility фильтрует BLOCKED/VERY_LOW тиры до LLM. Правильно.
- Call site B (pgvector → source_credibility.score_documents) — pass-through пока у MemoryRecord нет source_url.
- **Retrieval не влияет на стиль** — это правильно и нарушать не нужно. ChatGPT подтвердил: retrieval = только данные.

---

#### context/ (assembler)

- `resolve_truth_mode()` — чистая функция, маппинг intent → TruthMode.
- `assemble()` — склейка документов с лимитом по символам.
- **Contracts содержат только типы данных** (TruthMode, Tier, EPKDecision, Complexity). ChatGPT предлагал добавить "типы поведения ответа" в contracts — это было бы нарушением архитектуры §2.3 (contracts не должны содержать policy). Правильно что этого нет.

---

#### events/ (event_bus, event_dispatcher, event_types)

- `event_bus.publish()` **нигде не вызывается** в основном pipeline. EventBus инициализируется в bootstrap но реально не используется для доставки сообщений.
- События типа `LLM_CALLED`, `RETRIEVAL_COMPLETED` задекларированы, но не эмитируются из orchestrator/agents.
- Это не баг — events слой зарезервирован для future observability. На качество ответов не влияет.

---

#### core/ (orchestrator, EPK, cost_model, decision_matrix)

- EPK: sole policy authority. Читает только estimated_cost + user_balance. Не обращается к LLM, агентам, модели.
- cost_model и model_router не импортируют друг друга — separation of authority соблюдена.
- `_fast_token_threshold = 300` hardcoded в orchestrator.py — это магическое число. Не критично, но по архитектуре должно быть в policy_registry.

---

### 8.4 — Итоговая оценка советов ChatGPT по 37 скринам

**Правильно и реализовано/подтверждено:**
- Guardrail `_MAX_GROUP_IMAGES=6` + `too_many_images` — правильный производственный guardrail (18.4 ✅).
- "Код для ограничений, модель для смысла" — уже реализовано. Нет `if lang ==` веток, нет `translate()`, lang_instruction = одна строка в system prompt.
- Чинить локально → смотреть держит ли → только потом global rule — правильная инженерная стратегия.
- "Final Authority Layer" как концепция — correction.py строки 37–39 уже содержат паттерны "изображение представляет собой". Концепция реализована, новый слой не нужен.
- Поэтапные логи `[after_extraction]` / `[after_synthesis]` — правильная рекомендация, не реализована.

**Правильно стратегически, не применимо сейчас:**
- `VisionResponseMode` enum — архитектурно грамотно для масштабирования multimodal. Оверхед для текущей проблемы. Реализовывать когда batching pipeline будет расширяться.
- Stage 1→2→3 batching (partial insights → synthesis → optional refinement) — правильная архитектура для 20+ фото. При guardrail 6 не актуально.

**Неверно или введено в заблуждение:**
- "`contracts/` — недоиспользованный потенциал, добавь типы поведения ответа" — нарушает архитектуру §2.3. Contracts содержат только типы данных. Policy в EPK, поведение в system prompts.
- `detect_vision_mode(images, user_input)` в orchestrator — сам ChatGPT признал это оверхедом. Orchestrator не видит images напрямую.
- "Нет единой точки истины для формата ответа" — неверно. Точки контроля существуют: correction.py (step 5) + output_normalizer (step 6) + _strip_cot_artifacts + variation_rule в prompt_engine.

**Что упустил ChatGPT (не обсуждалось в скринах):**
- Мёртвые DENY-check в update_handler (строки 166/372/415).
- `is_vision` через `locals().get()` — хрупкость.
- `_fast_token_threshold = 300` hardcoded в orchestrator — нарушает Single Policy Authority (должно быть в policy_registry).
- Events слой (event_bus, event_dispatcher) задекларирован но нигде не используется для эмитирования событий из pipeline.
- variation_rule конфликт с EMOTIONAL intent prompt.

---

## 7. ЧТО НЕ ТРОГАТЬ

- `cognition/*` (intent_engine, reasoning_engine, multi_agent_coordinator) — здесь формируется смысл, нельзя добавлять format constraints
- `retrieval/*` — только данные, никакого влияния на стиль
- Архитектуру EPK — стабильна, не менять пока не закрыты текущие открытые задачи
- `_GROUP_EXTRACTION_SYSTEM` — фикс 18.3 свежий, дать постабилизироваться в продакшне