# CEYONA — ARCHITECTURE AUDIT
**Дата:** май 2026 (обновлён май 2026)
**Проверено:** architecture.md v8.4, models.md v7.3, economic.md v5.2 + весь runtime код
**Статус:** 13.1, 13.5 закрыты. Открыто: 3 UX/качество + 1 архитектурный gap.

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

### Задеплоены (май 2026)
- `vision_handler.py` — экстрактор переписан: идентифицирует нарисованных персонажей, описывает реальных людей без именования, не начинает с мета-фраз
- `vision_handler.py` — маршрутизация: «не знаю» → pipeline, не raw output
- `intent_engine.py` — QUESTION prompt: убрана роботизация, тёплый голос
- `update_handler.py` — история: сохраняется caption, не vision dump (фикс 413)
- `intent_engine.py` — LLM pre-classifier вместо hardcoded signal tuples (все 75 языков)
- `intent_engine.py` — history context для follow-up сообщений (§13.4 частично)
- `prompt_engine.py` — переписан: lang → system prompt → truth block → format. Контекст в user turn
- `reasoning_engine.py` — QUESTION на GENERAL/HEAVY: mode=DIRECT, CoT убран

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

**Решение:**
- `external/web_tools.py` — добавлена функция `_rewrite_search_query()`: семантический классификатор **KNOWN_ENTITY vs DESCRIPTIVE_SEARCH**. Один prompt к llama-3.1-8b-instant (FAST tier, max_tokens=30, temperature=0.0) — LLM определяет, знает ли пользователь точное название. KNOWN_ENTITY → запрос передаётся as-is (или переводится на английский). DESCRIPTIVE_SEARCH → конвертируется в краткий английский keyword query (3-8 слов) по уникальным признакам: роль, отношения, жанр, год, сеттинг. Никаких hardcoded списков слов — классификация полностью семантическая, работает на всех 75 языках. Fallback на оригинальный запрос при любой ошибке (non-blocking).
- `cognition/intent_engine.py` — SEARCH prompt: удалена ложная инструкция «3 search rounds» (compound — синтезатор, не агент, повторный вызов search невозможен). Заменена на «SEARCH RESULTS SELECTION»: выбирать из кандидатов в ## CONTEXT, не генерировать, при неоднозначности предлагать top 2-3, запрещено галлюцинировать тайтлы.

**Архитектурное соответствие:** rewrite живёт в retrieval path (web_tools → search_service), не нарушает §26. Новый module не создан. llama-3.1-8b-instant используется по аналогии с `_extract_poi_parts_via_llm` и `_extract_route_endpoints_via_llm` — паттерн уже существует в кодовой базе.

---

### 🟡 17.2 — TruthMode как flag вместо verification layer

**Проблема:** TruthMode меняет стиль промпта, но не проверяет факты. LLM может галлюцинировать уверенно.

**Правильное решение:** одна функция `truth_check(answer, retrieval_context) -> float` в `execution_policy_kernel.py`. Retrieval = кандидаты, LLM = генератор, truth_check = судья.

**Что НЕ делать:** не создавать `truth/verifier.py` и другие новые модули — это замена файлов, не решение.

**Статус:** спроектировано. Реализация после стабилизации ответов.

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

---

## СВОДНАЯ ТАБЛИЦА ОТКРЫТЫХ ПУНКТОВ

| # | Приоритет | Описание | Файлы |
|---|---|---|---|
| 13.3 | 🟡 | CoT артефакты (остаточные случаи) | response_synthesizer, vision_handler |
| 13.4 | 🟡 | Classifier теряет контекст на follow-up | intent_engine._llm_pre_classify |
| 13.5 | ✅ | SEARCH query rewriter — ЗАКРЫТ (май 2026) | external/web_tools.py, cognition/intent_engine.py |
| 17.2 | 🟡 | TruthMode как flag, не verification layer | execution_policy_kernel |
| 13.7 | 🟢 | Грузинский i18n fallback некорректен | i18n/strings.py |

📋 **CI (planned):** coverage floor 75%, asyncio stress tests (13.4), integration tests compound pipeline, retrieval quality regression, mypy.