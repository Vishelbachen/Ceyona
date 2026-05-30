# CEYONA — АНАЛИЗ СЕССИИ 3
**Дата:** май 2026  
**Источники:** audit.md, architecture.md, models.md, economic.md, CI_README.md + 37 скринов обсуждений с ChatGPT  
**Статус:** аналитический документ — не заменяет audit.md, дополняет его

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

### 🔴 B — i18n слой: 1355 строк вместо ~150

**Суть проблемы:** `strings.py` вырос до 1355 строк. Основная причина: попытка решить через код то, что LLM уже умеет делать сама.

**Что верно оставить в i18n:**
- Системные сообщения (кнопки UI, технические ошибки): `too_many_images`, `vision_error`, `search_unavailable`, `balance_exhausted`, `low_balance_warning`
- Физические ограничения системы: лимиты, rate limits
- Специализированные метки: `weather_feels_like`, OW_LANG_MAP, SUPPORTED_LANGS

**Что нужно убрать (дублирует LLM):**
- `LANG_INSTRUCTIONS` (35+ строк) — LLM уже знает все языки. Достаточно одного global контракта в system prompt: `"Always answer in the user's language. If unclear — default to English."` + передать `lang` как параметр.
- Логика перевода ответов (`translate(response)`) если есть — убрать полностью.
- Языковые ветки типа `if lang == "ru": ...` внутри пайплайна.
- "Умные" системные тексты: объяснения, описания, форматирование — это делает LLM.

**Правило (из обсуждений):**
> Код — для ограничений. Модель — для смысла.

**Действие:** ревизия strings.py. Всё что LLM может сгенерировать сама — убрать. Цель: ~150–200 строк только инфраструктурных строк.

---

### 🟡 C — Отсутствие логирования поэтапного вывода vision pipeline

**Суть:** при дебаге нумерации две недели чинили не тот слой (`_GROUP_SYNTHESIS_SYSTEM_TEMPLATE` вместо `_GROUP_EXTRACTION_SYSTEM`). Причина — не было логов промежуточных состояний.

**Решение:** добавить структурированные логи:
```
[vision_input]
[after_extraction]
[after_grouping]  
[after_synthesis]
[final_output]
```
Без этого при следующем дефекте снова будет blind debugging.

**Файлы:** `transport/telegram/vision_handler.py`, `transport/telegram/update_handler.py`.

**Приоритет:** высокий — профилактика повторения сессии "2 недели в неправильном слое".

---

### 🟡 D — vision_handler.py делает прямые Groq вызовы без EPK

**Суть (из architecture.md §15):** vision_handler находится OUTSIDE EPK DAG by design — это ingress adapter. Но прямые Groq вызовы без EPK создают риск неконтролируемых расходов при больших альбомах.

**Текущее состояние:**
- `_MAX_GROUP_IMAGES = 6` — guardrail есть ✅
- `max_tokens` читается из `RUNTIME.tier_configs` ✅ (фикс май 2026)
- Но: нет биллинга vision вызовов в `usage_meter.py`

**Риск:** vision extraction токены не попадают в billing flow (economic.md §2: "Every model call that produces a response MUST be billed"). При интенсивном использовании — revenue leak.

**Действие:** добавить запись токенов vision вызовов в usage_meter с пометкой `source="vision_extraction"`.

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
| `i18n/strings.py` | 1355 | Разросся | Дублирует LLM (B) |
| `cognition/intent_engine.py` | 541 | 13.4 частично закрыт | Нет стресс-тестов |
| `cognition/response_synthesizer.py` | 416 | 7-step pipeline корректен | 13.3 не полностью покрыт |
| `llm/prompt_engine.py` | 120 | Компактный | — |

---

## 6. ПРИОРИТИЗИРОВАННЫЙ СПИСОК ДЕЙСТВИЙ

### Немедленно
1. Убедиться что 18.3 держит в продакшне (мониторинг нумерации в логах)
2. Добавить логи `[after_extraction]` / `[after_synthesis]` в vision pipeline (C)

### Ближайшие задачи
3. Ревизия `strings.py`: убрать всё что делает LLM (B) → цель ~150–200 строк
4. Добавить vision токены в `usage_meter.py` (D)
5. Закрыть 13.7 (грузинский i18n fallback — строка в strings.py)
6. Диагностика 13.1 через `fly logs | grep compound_agent`

### После стабилизации
7. Реализовать global formatting rule (19.x уровень 2) — только если паттерн всплывёт снова
8. Реализовать `truth_check()` для 17.2
9. Asyncio stress tests для 13.4
10. Поднять CI coverage до 75%

---

## 7. ЧТО НЕ ТРОГАТЬ

- `cognition/*` (intent_engine, reasoning_engine, multi_agent_coordinator) — здесь формируется смысл, нельзя добавлять format constraints
- `retrieval/*` — только данные, никакого влияния на стиль
- Архитектуру EPK — стабильна, не менять пока не закрыты текущие открытые задачи
- `_GROUP_EXTRACTION_SYSTEM` — фикс 18.3 свежий, дать постабилизироваться в продакшне
