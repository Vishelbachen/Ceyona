# CEYONA — AUDIT
Version: актуально на июнь 2026
Соответствует architecture.md v8.5

---

## ПРИНЦИП — ЧИТАТЬ ПЕРВЫМ

**Пользователь видит только ответ бота. Не архитектуру, не pipeline — только ответ.**
Целевой уровень: Claude / ChatGPT — живой, прямой, без роботизации.

**Без костылей.** Каждое решение — правильное и масштабируемое с первого раза.
Языковые словари, списки запрещённых строк, per-language exceptions — не решения.
Правильный подход: LLM умеет делать задачу универсально — делегировать ему.

**Критерий изменения:** стал ли ответ бота лучше или хуже.
Если хуже — откат, даже если изменение архитектурно красиво.

---

## ФАЙЛЫ, ОПРЕДЕЛЯЮЩИЕ КАЧЕСТВО ОТВЕТОВ

| Файл | Что решает |
|------|-----------|
| `transport/telegram/vision_handler.py` | Промпты для vision, лимиты |
| `transport/telegram/update_handler.py` | Flow ответа, routing, история, retrieval score filter |
| `transport/telegram/webhook.py` | Команды /balance, /start, /help, /clear, /reset_memory |
| `cognition/intent_engine.py` | System prompts для каждого intent — голос и стиль |
| `llm/prompt_engine.py` | Сборка промпта перед LLM |
| `core/execution/orchestrator.py` | intent → путь → ответ, STRICT truth gate, EPK |
| `cognition/response_synthesizer.py` | Финальная обработка перед отправкой |
| `agents/safety_agent.py` | Post-reasoning semantic validator — SOLE BLOCKING AUTHORITY |
| `cognition/multi_agent_coordinator.py` | Agent dispatch, consensus, safety_agent вызов |
| `memory/supabase_store.py` | Хранение и retrieval памяти, similarity scores |
| `retrieval/retrieval_engine.py` | Retrieval pipeline, score propagation |
| `i18n/strings.py` | Все локализованные строки бота |

---

## ТЕКУЩИЙ СТАТУС СИСТЕМЫ (июнь 2026)

### Что работает в production

- EPK pipeline (ALLOW / DENY / DEGRADED / HEAVY_REQUIRED)
- Billing: токены по всем путям включая safety_agent, compound, lc_transformer
- Safety Layer Pass 1/2 (observability, non-blocking)
- safety_agent на ALLOW + HEAVY путях (consensus + HEAVY tier)
- Conversation history с tier-зависимыми бюджетами
- Retrieval pipeline: similarity score propagation + score filter 0.75
- Vision pipeline: album aggregation, batch extraction, synthesis
- TTS / ASR pipeline
- Команды /clear, /reset_memory
- Multi-provider search fallback: Tavily → SerpAPI → SearXNG
- source_credibility call site A (search results filtering)
- Compound agent как синтезатор (не агент) для tool intents
- MediaGroupAggregator (Redis-backed, Lua atomicity)
- ResilientSupabase (auto-reconnect)
- Multilingual normalization: allam-2-7b (AR), qwen3.6-27b (other non-Latin)

---

## ЗАКРЫТЫЕ ЗАДАЧИ (хронология)

### ✅ сессии 1–3 (май 2026)

| # | Суть | Ключевое решение |
|---|------|-----------------|
| 8.1 | Мёртвые DENY-check в update_handler | Ветки удалены |
| 13.1 | Tool intents → «сервис недоступен» | compound = синтезатор; tool_choice убран |
| 13.5 | Описательный запрос → поиск по сырому тексту | `_understand_query()` — KNOWN_ENTITY vs DESCRIPTIVE |
| 13.6 | Бот отвечал на каждое фото альбома отдельно | Redis-backed MediaGroupAggregator, debounce, Lua |
| 13.6.1 | Lock bug, смешение партий, lang хардкод | `_LUA_FLUSH` атомарный DEL, `MediaGroupItem.lang` |
| 17.1 | CoT infinite loop | reasoning_engine: QUESTION → mode=DIRECT |
| 17.3 | Шаблонные ответы, «Изображения представляют собой» | target pattern в synthesis, `detect_repetitive_opening` |
| 18.1–18.4 | Vision: нумерация, caption нарратив, лимит фото | constraints в extraction prompt, `_MAX_GROUP_IMAGES=6` |
| 20.1 | Memory contamination | similarity score propagation + score filter 0.75 |
| 20.2 | /clear и /reset_memory отсутствовали | Две команды с разной семантикой, двухшаговое подтверждение |

### ✅ сессия 4 (июнь 2026) — Billing audit

*Номера BUG-O# соответствуют порядку обнаружения в `audit_orchestrator_billing.md` (BUG-O1…BUG-O5). BUG-O4 исправлен позже, в сессии 5 — см. ниже.*

| # | Суть | Ключевое решение |
|---|------|-----------------|
| BUG-O1 | safety_agent токены не биллировались | `actual_safety_cost()` добавлен в `_run_allow()` |
| BUG-O2 | compound breakdown не передавался в UsageEntry | `compound_breakdown` поле добавлено в OrchestratorResult |
| BUG-O3 | MATH verifier токены не биллировались | `_math_extra_in/out` накапливается и передаётся в CoordinationResult |
| BUG-O5 | Failed primary agent токены терялись | `_failed_primary_in/out` суммируются в fallback result |
| Supabase migration | 6 новых колонок в `usage_log` | `tool_calls`, `safety_agent_input_tokens`, etc. |

### ✅ сессия 5 (июнь 2026) — Safety contract

| # | Суть | Ключевое решение |
|---|------|-----------------|
| BUG-O4 | `locals()` в coordinator — хрупкая проверка существования safety переменной *(найден раньше остальных в `audit_orchestrator_billing.md`, но исправлен только в этой сессии)* | `_safety_result: SafetyResult \| None = None` — явный паттерн |
| SAFETY-1 | `check()` из async контекста → молчаливый ALLOW | `RuntimeError` вместо warning+ALLOW |
| SAFETY-2 | `_llm_judge` except → ALLOW (невидимая дыра) | `SAFETY_UNAVAILABLE` вердикт + `increment("safety_agent.judge_unavailable")` |
| SAFETY-3 | `_REVISE_SIGNALS` — английские строки в мультиязычной системе | **Удалены полностью.** Fast path был языковым костылём. LLM judge покрывает REVISE семантически на всех языках без словарей. |
| ARCH-1 | architecture.md §21 не содержал полного контракта safety_agent | Переписан: уровни проверки, таблица вердиктов с действиями coordinator, профили одного агента |
| ARCH-2 | §20, §35, §44, §47, §48.3 расходились с реальностью | Статусы planned/not implemented зафиксированы явно |


### ✅ сессия 6 (июнь 2026) — SAFETY-6 + AgentCallMetrics

| # | Суть | Ключевое решение |
|---|------|-----------------|
| SAFETY-6 | REVISE loop не был реализован — verdict проходил насквозь как ALLOW | `_build_revision_messages()` + revision loop в consensus и HEAVY путях. Max 1 retry. `SafetyResult.reason` передаётся в revision hint. Если второй pass снова REVISE → pass-through, не BLOCK. |
| BILLING-R1 | Revision — отдельный Groq вызов, не биллировался | `revision_input_tokens` / `revision_output_tokens` через полную цепочку: `AgentCallMetrics` → `CoordinationResult` → `OrchestratorResult` → `webhook.py` (`_revision_cost`) → `UsageEntry` → Supabase |
| ARCH-3 | `CoordinationResult` имел плоские billing поля — паттерн ведущий к разрастанию | `AgentCallMetrics` dataclass (primary / revision / safety слоты). `CoordinationResult` несёт `metrics: AgentCallMetrics`. Convenience properties сохраняют обратную совместимость для orchestrator. Граница изоляции: orchestrator разворачивает `metrics` в плоские поля `OrchestratorResult` — webhook/usage_meter/Supabase остаются плоскими. |

---

### 🔴 SAFETY-4 — Safety Lite для FAST/DEGRADED путей

**Суть:** сейчас safety_agent не вызывается на FAST/DEGRADED. Контракт §21:
каждый ответ проходит post-check, глубина зависит от пайплайна.
Safety Lite = облегчённый промпт, тот же safeguard-20b, max_tokens=3.

**Что нужно:**
- `safety_check_lite(inp: SafetyInput) -> SafetyResult` в `safety_agent.py`
- Вызов в `_run_degraded()` в orchestrator
- Вызов в coordinator для FAST-tier путей

**Приоритет:** средний. Система работает, Safety Layer Pass 1/2 прикрывают вход.
Реализовать после стабилизации текущих изменений.

---

### 🔴 SAFETY-5 — Safety Extended для HEAVY пути

**Суть:** сейчас HEAVY использует тот же `check_async()` что и GENERAL.
Safety Extended = раздельная проверка reasoning_plan и draft_response.

**Что нужно:**
- `safety_check_extended(inp: SafetyInput) -> SafetyResult` в `safety_agent.py`
- Два LLM-вызова: один на reasoning_plan, один на draft_response
- Вызов в coordinator на HEAVY пути вместо текущего `safety_check()`

**Приоритет:** низкий. HEAVY уже проверяется. Extended — следующий уровень.

---

### 🟡 §35 — History load до EPK: архитектурный долг

**Суть:** история загружается с `GENERAL_HISTORY_BUDGET` до EPK, поэтому
на DEGRADED-пути prompt содержит больше истории чем нужно.

**Целевой порядок:**
```
Safety Gates → Feature Extraction → EPK (pre-check)
    → History Load (бюджет под EPK-решение)
    → Retrieval → Full pipeline
```

Требует двухфазного EPK или conservative estimate на первом проходе.

**Приоритет:** низкий. Не ломает систему, лишние токены на DEGRADED.

---

### 🟡 §47 — Verbatim return: не реализовано

**Суть:** WEATHER/MAPS tool output сейчас всегда идёт через LLM-синтез.
Verbatim return (прямой вывод без LLM) снизит latency и cost для tool-only запросов.

**Зависимость:** реализуется совместно с §44 multi-intent decomposition.

**Приоритет:** низкий. Функционально работает, только дороже.

---

### 🟡 §44 — Multi-intent decomposition: не реализовано

**Суть:** `classify()` возвращает один `IntentResult`. Параллельного
исполнения tool-intents через `asyncio.gather` нет.

**Что нужно:**
- `classify()` → `list[IntentResult]` с `is_primary: bool`
- `asyncio.gather` для tool-intents в orchestrator
- EPK агрегирует суммарный cost всех sub-intents

**Приоритет:** низкий. Реализовать после Safety fixes.

---

### 🟡 §20 — source_credibility Call site B: не активен

**Суть:** `MemoryRecord.source_url` определён и propagated через `vector_memory.py`,
но `source_credibility.score_documents()` в retrieval_engine — pass-through.

**Что нужно перед активацией:**
1. Аудит и коррекция токенных ставок в `cost_model.py` по актуальным ценам Groq
2. Активация `score_documents()` в `retrieval_engine.py`

**Приоритет:** низкий.

---

### 🟡 §48.3 — Product Knowledge Фазы 2 и 3: не реализованы

**Суть:** Фаза 1 (inline) реализована. Фазы 2 (static files) и 3 (pgvector indexed)
реализуются по мере роста объёма product knowledge.

**Приоритет:** низкий. Реализовать когда inline перестанет умещаться.

---

### 🟡 17.2 — TruthMode: частично реализовано

**Что реализовано:** retrieval scoring + threshold gating + STRICT pre-execution gate.
Production-grade implicit truth proxy для Telegram-scale.

**Что НЕ реализовано:**
- Post-generation factual verification
- Contradiction detection
- Memory-vs-context separation
- Time-awareness (устаревшие факты в памяти)

**Позиция:** `truth_check` как отдельный LLM-pass нецелесообразен при текущих
constraints (latency, cost). Следующий уровень — contradiction detection.

**Приоритет:** низкий. После стабилизации safety.

---

### 🟡 13.4 — Classifier теряет контекст на follow-up

**Симптом:** короткое сообщение «Вот, нашла» → CONVERSATION вместо правильного intent.
**Частично закрыт:** history context добавлен для сообщений ≤ 8 слов.
**Осталось:** asyncio stress tests при concurrent запросах.
**Файл:** `cognition/intent_engine.py` → `_llm_pre_classify`

---

### 🟢 13.7 — Грузинский i18n fallback (быстро закрыть)

**Симптом:** вопрос на грузинском → «уточните вопрос» вместо «технический сбой».
**Файл:** `i18n/strings.py`, ключ `search_unavailable`, lang `ka`.
**Приоритет:** высокий по простоте. Одна строка.

---

### 🔴 21.1 — Email уведомления (Brevo) — opt-in

**Суть:** `event_notifier.py` умеет слать письма, но email неоткуда брать.
Telegram Bot API не передаёт email.

**Решение (спроектировано):**
- Пользователь вводит email через `/settings`
- Supabase таблица `user_notifications`: `user_id`, `email`, `notify_balance_exhausted`, `notify_balance_credited`
- Оба флага по умолчанию выключены (strict opt-in)
- Слать: DENY (баланс 0), подтверждение пополнения
- НЕ слать: safety_block, system_error — только в логи/Sentry
- Текст писем переписать в голосе Сэёны

**Приоритет:** низкий. Требует UI для сбора email.

---

## АРХИТЕКТУРНЫЕ ПРИНЦИПЫ ЗАФИКСИРОВАННЫЕ В АУДИТЕ

### Fast path должен быть детерминированным, не лингвистическим

Если есть LLM который решает задачу универсально — не писать языковые словари.
`_REVISE_SIGNALS` удалены именно по этой причине: они были параллельной
языковой системой с более узким scope чем LLM judge.

Если fast path нужен — он проверяет структурные инварианты, служебные флаги,
технические маркеры. Не текст на конкретном языке.

### Fail-open с полной observability лучше чем молчаливый ALLOW

`SAFETY_UNAVAILABLE` как явный статус важнее чем fail-open сам по себе.
Разница между «проверен и безопасен» и «не удалось проверить» должна быть
видна в метриках, логах, и обрабатываться coordinator явно.

### Контракт до кода

Перед реализацией любого нового компонента — сначала зафиксировать в
architecture.md: что делает, что не делает, уровни, вердикты, действия coordinator.
safety_agent §21 — пример правильного контракта.

---

## CI (planned)

Coverage floor 75%, asyncio stress tests (13.4), integration tests compound pipeline,
retrieval quality regression, mypy strict mode.

---

## СЛЕДУЮЩИЙ ШАГ

Приоритет реализации открытых задач:

1. **SAFETY-4** — Safety Lite для FAST/DEGRADED
2. **SAFETY-5** — Safety Extended для HEAVY
3. **§44 + §47** — multi-intent + verbatim return (совместно)
4. **§35** — history-after-EPK
5. **§20** — source_credibility call site B