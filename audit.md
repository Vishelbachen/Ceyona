# CEYONA — ARCHITECTURE AUDIT
**Дата:** май 2026
**Проверено:** architecture.md v8.3, models.md v7.3, economic.md v5.2 + весь runtime код
**Статус:** все архитектурные пункты закрыты. Открыто: 5 UX/качество багов + 2 архитектурных gap.

Обозначения: ✅ Закрыто | ⚠️ Открыто | 🔴 Критично | 🟡 Средний | 🟢 Низкий | 📋 Запланировано

---

## ⚡ АБСОЛЮТНЫЙ ПРИОРИТЕТ — КАЧЕСТВО ОТВЕТОВ

> **Прочитай это перед тем как открывать любой другой файл.**

**Ответы бота — это 99% продакшена.**
Без качественных ответов любая архитектурная работа, рефакторинг, оптимизация
и новые фичи не имеют смысла. Пользователь не видит pipeline. Пользователь
видит только то, что написал бот.

### Текущий статус (май 2026)
Целевой уровень ответов: **Claude / ChatGPT** — разговорный, тёплый, умный,
без роботизированных фраз, без холодных отказов.

Три критических фикса задеплоены (май 2026):
- `vision_handler.py` — `_EXTRACTION_SYSTEM` переписан: экстрактор пробует
  идентифицировать нарисованных персонажей, описывает реальных людей без
  попытки назвать, стартует прямо с контента без «Изображение представляет собой».
- `vision_handler.py` — маршрутизация: если экстрактор вернул «не знаю» /
  «cannot identify» → принудительно через pipeline, не отдавать raw пользователю.
- `intent_engine.py` — QUESTION prompt: убрана роботизированная фраза
  «Я не идентифицирую людей по фото, но вот что вижу:», добавлен тёплый голос,
  запрет на открытие с «Изображение представляет собой».
- `update_handler.py` — история: сохраняется caption, не vision dump
  (фикс 413 Payload Too Large на следующих сообщениях после фото).

### Правила для любого, кто открывает эти файлы

1. **Сначала — анализ ответов.** Прежде чем менять архитектуру, retrieval,
   агентов или pipeline — проверь: как бот отвечает прямо сейчас?
   Открой тестовый диалог, отправь несколько сообщений разных типов
   (вопрос, фото, голос, поиск). Если ответы роботизированные или пустые —
   это приоритет №1.

2. **Файлы, которые определяют КАК бот отвечает** — анализировать обязательно
   при каждой сессии (если файл недавно изменён и работает — можно пропустить):

   | Файл | Что решает |
   |------|-----------|
   | `cognition/intent_engine.py` | System prompts для каждого intent — голос и стиль ответа |
   | `transport/telegram/vision_handler.py` | Как обрабатываются изображения, что видит пользователь |
   | `transport/telegram/update_handler.py` | Общий flow ответа, история, fast-path vs pipeline |
   | `llm/fallback_handler.py` | Что происходит когда основной LLM не отвечает |
   | `llm/prompt_engine.py` | Сборка финального промпта перед LLM |
   | `core/execution/orchestrator.py` | Какой intent → какой путь → какой ответ |
   | `agents/fast_agent.py` | Ответы в быстром режиме |
   | `agents/deep_agent.py` | Ответы в глубоком режиме |
   | `cognition/response_synthesizer.py` | Финальная обработка ответа перед отправкой |

3. **Признаки что с ответами проблема** (смотреть в логах и тестах):
   - Начало ответа: «Изображение представляет собой», «На изображении»,
     «The image shows» → сломан vision fast-path или экстрактор
   - Ответ «Я не знаю» без попытки объяснить → сломана маршрутизация vision
   - Ответ содержит «Constraints:», «Candidates:», «Ограничения:» →
     CoT артефакты утекают (см. §13.3)
   - Ответ обрывается или пустой → 413 или LLM timeout (см. §13.1)
   - Тон сухой и дистанцированный на простых вопросах → проверь
     CONVERSATION system prompt в intent_engine

4. **Архитектурные изменения** (retrieval, agents, kernel, embeddings) —
   только после того как ответы стабильно на уровне. Не наоборот.

### Контекст: аудит архитектуры (ChatGPT + ручной анализ, май 2026)

Внешний аудит выявил реальные архитектурные проблемы — они валидны,
но это roadmap, не срочность:

- **«Распределённый мозг»**: решения принимаются в agents/ + cognition/ +
  core/kernel/ одновременно. Нет единого центра. Это технический долг,
  не блокер ответов.
- **Multi-agent преждевременно**: fast/deep/creative agent — физическое
  разделение ролей, но ChatGPT/Claude делают это через режимы одного LLM,
  не отдельные агенты. Долгосрочно — правильное направление: kernel выбирает
  режим, один LLM исполняет.
- **Over-engineered retrieval**: dense + sparse + fusion + reranker —
  уровень production FAANG без базы под это. Зафиксировать на dense (BGE)
  пока нет измеренной потребности в остальном.
- **Embeddings dataset вместо rule-наборов**: вместо exam_rules / image_rules /
  voice_rules — единый dataset примеров с mode/constraints, поиск через
  embeddings. Правильное направление, но это месяц работы, не срочно.

**Эти пункты — для следующей итерации, когда ответы стабильны.**

---

## ОТКРЫТЫЕ ПРОБЛЕМЫ

### 🔴 13.1 — Все tool intents → «сервис временно недоступен»

**Симптом:** поиск, маршруты, погода — всегда возвращают `search_unavailable`.

**Предполагаемые причины:**
- SERPAPI_KEY / OPENWEATHER_API_KEY не заполнены в fly.io secrets
- compound-mini не поддерживает `tool_choice="auto"` с текущими параметрами
- httpx.ReadTimeout в `_execute_tool`
- unexpected `finish_reason` → defensive `success=False` в `_run_compound`

**Диагностика:** `fly logs | grep "compound_agent"` — искать `"API call failed"`, `"tool execution failed"`.

**Влияние:** критическое — все data-driven интенты деградируют.

---

### 🟡 13.3 — CoT reasoning format утекает в финальный ответ (частично)

**Симптом:** ответы содержат `Constraints / Candidates / Verification table`.

**Причина:** `_strip_cot_artifacts()` не покрывает все сценарии (vision → MATH/ANALYSIS classification).

**Частично закрыто:** двухрежимный фикс в `response_synthesizer.py` (май 2026) закрыл infinite loop (13.1→17.1). Остаточные случаи — vision-input через reasoning_engine.

---

### 🟡 13.4 — Classifier теряет контекст на follow-up сообщениях

**Симптом:** «Вот, нашла» / «Туговатый поиск» → CONVERSATION вместо правильного intent.

**Причина:** `_llm_pre_classify(text)` получает только `text[:500]` без истории.

**Решение-кандидат:** передавать последние 2–3 реплики как контекст в pre-classifier.

---

### 🟡 13.5 — SEARCH не переформулирует описательный запрос

**Симптом:** «глава якудзы подставляет к дочери охранника» — 3 попытки, не находит тайтл.

**Причина:** compound передаёт user message как-есть в `web_search` без rewrite.

**Решение-кандидат:** инструкция в SEARCH system prompt — переформулировать в keyword query на английском.

---

### 🟡 17.2 — Epistemic gap: TruthMode как execution flag

**Проблема:** нет `confidence_score`, `contradiction_detection`, `hallucination_risk` на уровне pipeline.
Система может уверенно галлюцинировать — особенно критично при multi-agent coordination.

**Решение-кандидат:** `TruthAssessmentPipeline` собрать из существующих компонентов
(`consensus_engine.py`, `source_credibility.py`, `reflection.py`, `analysis.py`).

**Статус:** требует отдельного проектирования, не быстрый фикс.

---

### 🟢 13.7 — Грузинский: i18n fallback некорректен по смыслу

**Симптом:** чёткий вопрос на грузинском → «уточните вопрос» вместо «технический сбой».

**Причина:** `search_unavailable` строка для `ka` формулирует отказ как неясность запроса.

---

## ИСТОРИЯ РЕШЕНИЙ

Все архитектурные проблемы закрыты в мае 2026. Краткая сводка по категориям:

### Нондетерминизм и классификация (§1)
- `_classify_complexity()` переписан: code detection только по fenced blocks, JSON требует key:value паттерн, threshold поднят до 800 chars.
- `_build_messages()` принимает реальный `tier` — FAST/HEAVY получают разные instruction_prefix.

### Governance theater (§2)
- Safety Gate задокументирован как **observability-only** (non-blocking) — false-positive rate на коротком/русском/арабском тексте неприемлем. Единственный blocking authority — `safety_agent`.
- `analysis.py` подключён: `update_handler → analyse() → OrchestratorRequest.analysis_report → intent_engine.classify(analysis_hints=...)`.
- `decision_matrix.py` читает пороги из `policy_registry.RUNTIME` вместо hardcoded значений.

### Orchestration (§3, §9, §12)
- Web search routing перенесена из transport в `orchestrator.run()`.
- `forced_intent` / `_already_grounded` coupling устранён — заменён на `vision_intent: IntentResult | None`.
- Billing cascade (HEAVY→GENERAL→FAST) исправлен: используется `actual_tier` из `CoordinationResult`.
- Unified agentic path: все 5 tool intents (SEARCH, WEATHER, MAPS, MAPS_POI, MAPS_ROUTE) через `compound_agent`. `_STRICT_INTENTS` → пустое множество (STRICT = LLM policy, не pre-execution gate).

### Retrieval (§5)
- pgvector `similarity_search()` bug исправлен.
- `rerank_tokens` считает реальные символы (1 token ≈ 4 chars).
- `source_credibility.score_documents()` активирован для pgvector результатов; `source_url` добавлен в `MemoryRecord`.
- Retrieval при `redis is None` не пропускается — деградирует без кэша с WARNING.

### Tier inflation (§6)
- `_estimate_tier` в `orchestrator.run()`: LOW complexity + <300 input tokens → оценка по FAST rates.

### Billing completeness (§7)
- `UsageEntry` заполняется полностью: `intent`, `audio_seconds`, `tts_characters`, `tool_calls`.
- `OrchestratorResult` объявляет speech fields; `update_handler` заполняет через `dataclasses.replace()`.
- Speech billing columns добавлены через `migrate_usage_log.sql`; PGRST204 fallback до миграции.

### Observability (§10)
- `GET /metrics` добавлен в `main.py` — JSON snapshot. In-memory, per-process, без persistence (by design).
- `tracing.py` переписан: structured JSON spans, `trace_id` через `contextvars`, `parent_id`, `status: ok|error`. OpenTelemetry deps удалены как мёртвые.
- Safety Gate signals разделены: API error → `safety_signal_lost` (ERROR), UNSAFE → WARNING.
- `request_id = "{update_id}:{user_id}"` сквозная корреляция через весь pipeline.

### CI / Tests (§11, §16)
- Test suite создан: EPK, safety gate, analysis, usage meter, intent hints, web search routing. Все pure unit, без внешних зависимостей.
- Coverage поднят с 41% до ≥60% добавлением тестов transport/retrieval/payments/cache.
- `fly.toml` обновлён до `8gb / performance-cpu-1x` (healthcheck не укладывался в 5s timeout на 2GB shared).

### Search provider (§14)
- Three-tier fallback: **Tavily** (primary) → **SerpAPI** (secondary) → **SearXNG** (tertiary, self-hosted).
- `docker-compose.yml` добавлен сервис `searxng`; `.env.example` обновлён.

### Healthcheck (§15)
- `asyncio.wait_for()` с timeout 3s для Redis и Supabase; проверки параллельные через `asyncio.gather`.
- `/providers` исправлен: `user_balances` вместо несуществующей `healthcheck`, `asyncio.to_thread` для sync Supabase call.

### Conversation history (§13.2)
- `_MAX_HISTORY_TOKENS = 1200` заменён tier-зависимыми бюджетами: FAST=1800, GENERAL=3500 tokens.
- SQL fetch limit поднят с 20 до 40 turns.

### CoT infinite loop (§17.1)
- `reasoning_engine.py`: QUESTION на GENERAL/HEAVY → `mode=DIRECT`, убран CoT instruction.
- `intent_engine.py` QUESTION system prompt: explicit graceful exit rule, запрет simulate search.
- `response_synthesizer._strip_cot_artifacts()`: Mode A (pure CoT loop → честное признание), Mode B (partial stripping). Русские паттерны добавлены.

### Balance guards (§9.2, §9.3)
- Web search и vision fast-path не выполняются при `user_balance <= 0`.

---

## СВОДНАЯ ТАБЛИЦА ОТКРЫТЫХ ПУНКТОВ

| # | Приоритет | Описание | Файлы |
|---|---|---|---|
| 13.1 | 🔴 КРИТИЧЕСКИЙ | Все tool intents → «сервис недоступен» | compound_agent, groq_client, settings |
| 13.3 | 🟡 СРЕДНИЙ | CoT format в финальном ответе (остаточные случаи) | response_synthesizer, vision_handler |
| 13.4 | 🟡 СРЕДНИЙ | Classifier теряет контекст на follow-up фразах | intent_engine._llm_pre_classify |
| 13.5 | 🟡 СРЕДНИЙ | SEARCH не переформулирует описательный запрос | compound_agent, SEARCH system prompt |
| 17.2 | 🟡 СРЕДНИЙ | Epistemic gap: TruthMode как flag вместо verification layer | consensus_engine, source_credibility |
| 13.7 | 🟢 НИЗКИЙ | Грузинский: i18n fallback-строка некорректна по смыслу | i18n/strings.py |

📋 **Из CI_README (planned):** coverage floor 75% (speech/billing тесты), asyncio stress tests (13.4), integration tests compound tool execution (13.1 regression), retrieval quality regression, mypy.