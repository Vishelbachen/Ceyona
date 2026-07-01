# Ceyona — Deep Audit: Новые Находки
*Полный анализ кода, не покрытый первым отчётом*

---

## НОВЫЕ БАГИ (не задокументированы нигде)

### ~~BUG-1: `contracts/orchestrator.py` не существует, но импортируется~~ — ЗАКРЫТО

**Исправлено:** импорт заменён на `from contracts.shared_types import EPKDecision as _EPKDecision`. Комментарий `# BUG-1 fix` присутствует в коде.

---

### ~~BUG-2: `ReflectionInput` вызывается с неверным именем поля~~ — ЗАКРЫТО

**Исправлено:** поле переименовано в `llm_cost_usd=result.usage.llm_cost_usd` в `update_handler.py`. Reflection работает.

---

### ~~BUG-3: `/providers` endpoint не имеет `@app.get` декоратора~~ — ЗАКРЫТО

**Исправлено:** декоратор `@app.get("/providers")` добавлен в `app/main.py`. Endpoint доступен.

---

### ~~BUG-4: `security/encryption.py` и `security/auth.py` — мёртвый код~~ — ЧАСТИЧНО ЗАКРЫТО (июнь 2026)

- `verify_token()` / `create_token()` — **ЗАКРЫТО**: `verify_token` используется в `require_admin` dependency в `app/main.py`. Защищены `/metrics`, `/models`, `/providers`, `/routing`, `/debug`.
- `encrypt()` / `decrypt()` — **OPEN**: обдуманно отложено. Fernet шифрование `MemoryEntry.content` требует версионирования ключей и фоновой миграции. Отдельная задача.

---

### ~~BUG-5: `security/origin_guard.py` — мёртвый код~~ — ЗАКРЫТО (июнь 2026)

`CORSMiddleware` подключён в `app/main.py`. `allowed_origins` берётся из `settings.allowed_origins` через `origin_guard`-логику. Для бота по умолчанию `*` — Telegram серверы не браузер, CORS им не нужен. Middleware готов для будущих веб-клиентов.

---

## АРХИТЕКТУРНЫЕ РАСХОЖДЕНИЯ

### ~~ARCH-1: `OrchestratorResult` определён в `core/execution/orchestrator.py`, а не в `contracts/`~~ — ЗАКРЫТО (июнь 2026)

**Решение:** `core/execution/__init__.py` — публичный фасад пакета.

**Почему не `contracts/orchestrator.py`:** типы принадлежат оркестратору — это его вход и выход. Перенос в `contracts/` создал бы второй центр ответственности и немедленно сломался бы на `CoordinationMetrics` (circular dependency). Проблема была не в том что transport импортирует из `core.execution` — проблема была в том что он импортировал из `core.execution.orchestrator` (внутренняя реализация). Правило: **transport не должен импортировать внутренности core. Публичный API — можно.**

**Что сделано:**
- `core/execution/__init__.py` реэкспортирует `run`, `OrchestratorRequest`, `OrchestratorResult`, `UsageRecord` с явным `__all__`
- `update_handler.py`: `from core.execution import ...` вместо `from core.execution.orchestrator import ...`
- Внутренние символы (`PipelineMetrics`, `_run_heavy`, `CoordinationMetrics`, хелперы) **не** реэкспортируются

**Ценность фасада:** если завтра `orchestrator.py` разобьётся на `runner.py` + `request.py` + `result.py` — ни один внешний импорт не изменится.

---

### ARCH-2: `meta/reflection.py` и `meta/memory_audit.py` — pure functions без persistence

Оба файла — это чистые функции без I/O, без записи в Sentry, без публикации в event_bus:
- `reflect()` → возвращает `ReflectionReport` → caller делает `logger.info("Reflection", ...)`
- `audit()` → возвращает `AuditReport` → caller делает `logger.warning("Memory audit", ...)` если не healthy

Данные уходят только в лог. **Не пишутся в Supabase, не пишутся в Redis, не пишутся в EventStore (который всё равно не получает publish).** Вся "observability side-channel" — это просто `logger.info/warning`.

Architecture.md §4 описывает их как "META Side-channel (reflection + memory_audit — async, non-blocking)" — это технически выполнено, но ценность от этого side-channel фактически нулевая, так как логи без агрегации = необработанный шум.

---

### ~~ARCH-3: `events/` — полная зомби-подсистема~~ — ЧАСТИЧНО ЗАКРЫТО (июнь 2026)

EventStore хранит события в Redis с TTL 30 дней, EventReplay может воспроизводить их по user_id и по имени события. Инфраструктура для audit trail, debug replay, и user event history полностью построена.

| Событие | Статус |
|---|---|
| `balance_credited` | ✅ `wallet_manager.py` публикует `BalanceCreditedEvent` |
| `balance_exhausted` | ✅ `webhook.py` публикует `BalanceExhaustedEvent` при `insufficient_balance` |
| `request_denied` | ✅ `webhook.py` публикует `RequestDeniedEvent` при других deny_reason |
| `llm_called` / `llm_fallback` | ✅ `llm/fallback_handler.py` публикует оба события |
| `safety_block` | 🔴 **OPEN** — `coordinator` не публикует `SafetyBlockEvent` при BLOCK вердикте |
| `request_completed` | 🔴 **OPEN** — `update_handler.py` не публикует `RequestCompletedEvent` в конце pipeline |

`event_dispatcher` подписан на все активные события и маршрутизирует их в `EventStore` + `EventNotifier`.

---

### ~~ARCH-4: `notifications/event_notifier.py` — события без триггера~~ — ЧАСТИЧНО ЗАКРЫТО (июнь 2026)

`EventNotifier` имеет методы: `on_balance_credited`, `on_balance_exhausted`, `on_safety_block`, `on_system_error`.

| Метод | Статус |
|---|---|
| `on_balance_credited` | ✅ Вызывается из `event_dispatcher` при `BALANCE_CREDITED` → email уведомление |
| `on_balance_exhausted` | ✅ Вызывается из `event_dispatcher` при `BALANCE_EXHAUSTED` → email уведомление |
| `on_safety_block` | 🔴 **OPEN** — handler в dispatcher зарегистрирован, но `SafetyBlockEvent` не публикуется из coordinator (см. ARCH-3) |
| `on_system_error` | 🔴 **OPEN** — нигде не вызывается |

---

### ~~ARCH-5: `ContextChunk` — двухуровневые метаданные~~ — ЗАКРЫТО (июнь 2026)

`ContextChunk` теперь имеет два явных поля вместо одного плоского `metadata`:
- `metadata` — атрибуты документа (`document_id`, `mem_type`, `source_url`). Стабильны, задаются при индексации.
- `retrieval` — атрибуты процесса (`bm25_score`, `rrf_score`, `dense_rank`, `sparse_rank`, `rerank_score`). Заполняются во время pipeline.

На выходе pipeline `RetrievedDocument.metadata` содержит `{"doc": {...}, "retrieval": {...}}` — структура сохранена для внешнего контракта. Реализовано и подключено — двухуровневая модель метаданных используется всей retrieval pipeline (см. ARCH-6).

---

### ~~ARCH-6: Retrieval pipeline — полная архитектура~~ — ЗАКРЫТО (июнь 2026)

Реализован настоящий hybrid retrieval с чёткими границами между слоями.

**Цепочка:**
```
query
  ├─ pgvector similarity_search()  → ScoredCandidate(source='memory',  retrieval=RetrievalMetadata(dense_score=...))
  └─ BM25Engine.search()           → ScoredCandidate(source='bm25',    retrieval=RetrievalMetadata(sparse_score=...))
         ↓
  reciprocal_rank_fusion()         → ScoredCandidate(source='hybrid',  retrieval=RetrievalMetadata(rrf_score, dense_rank, sparse_rank, ...))
         ↓
  cross_encoder.rerank()           → (content, rerank_score)
         ↓
  RetrievedDocument(metadata={"doc":{...}, "retrieval":{rerank_score, query_kind, ...}})
         ↓  [context layer boundary — context_mapper.py]
  to_context_chunks()              → ContextChunk(content, score, source, metadata)
         ↓
  assemble_chunks()                → ContextBlock(chunks, total_chars, truncated)
         ↓
  block_to_prompt_string()         → str → prompt
```

**Ключевые архитектурные решения:**

| Решение | Обоснование |
|---|---|
| `ScoredCandidate` не смешивается с `ContextChunk` | Retrieval знает как нашли; context знает как подать в LLM |
| `RetrievalMetadata` — dataclass, не dict | Typo-safe; IDE подсказывает; соответствует стилю `RoutingProfile`, `AgentCallMetrics` |
| `context_mapper.py` — единственная точка пересечения слоёв | Все остальные context-файлы не знают про `retrieval/` |
| `ContextChunk.metadata` vs `ContextChunk.retrieval` | metadata = документ (стабильно); retrieval = процесс (pipeline-only) |
| BM25 corpus limit = 200, pgvector top_k = 5 | BM25 видит всю память пользователя; оба поиска независимы |
| `retrieval_models.py` активирован | Был quasi-мёртвым (только тесты); теперь `ScoredCandidate` + `RetrievalMetadata` — основные типы pipeline |

---

### ARCH-7: `infra/config_loader.py` — planned/unused (июнь 2026)

Файл существует с содержимым `getattr(settings, key, default)`. Нигде не импортируется в продуктивном коде.

**Решение:** зафиксировать как `planned/unused`, не удалять и не реализовывать без реальной потребности.

**Когда станет нужен:** появление логики вроде `get_int()`, `get_bool()`, `require()`, multi-source fallback (ENV → Secrets → default). Простой `getattr` — не повод для существования отдельного модуля.

**Что НЕ его ответственность:** `/debug`, `/health`, `/providers`, `/routing`, `/models` — это runtime diagnostics, не конфигурация. `main.py` правильно их содержит.

---

### ~~ARCH-8: `transport/telegram/callback_handler.py` — контракт есть, dispatch был в webhook~~ — ЗАКРЫТО (июнь 2026)

*(было пронумеровано как ARCH-5 — дублировало номер ARCH-5 «ContextChunk» выше; исправлено на следующий свободный номер по порядку в файле, ARCH-8)*

`callback_handler.py` правильно определяет `CallbackAction` enum и `parse_callback()`. Раньше весь if/elif dispatch по `ctx.action` (BALANCE, TOPUP, HELP, CANCEL) жил прямо в `webhook.py` (строки ~380-430) — нарушение Single Responsibility, `webhook.py` знал про "topup", "balance" и т.д.

**Исправлено:** `callback_handler.py` теперь владеет обеими частями — `parse_callback()` и `dispatch_callback()`. Вся billing/TOPUP/BALANCE логика и выбор i18n-строк переехали внутрь него. `webhook.py` (строки ~711–721) только вызывает `parse_callback()` → `dispatch_callback()` и ничего не знает о конкретных действиях.

---

## НЕЗАДОКУМЕНТИРОВАННЫЕ СЛОИ

### Полный список живых файлов без записи в architecture.md

| Файл | Реальная роль | Используется |
|---|---|---|
| `app/main.py` | FastAPI app, lifespan, все HTTP endpoints, wallet poller | ✅ Точка входа |
| `app/settings.py` | Pydantic Settings, все env vars | ✅ Везде |
| `transport/telegram/update_handler.py` | Главный pipeline handler: Safety Gates, history, retrieval, orchestrator, TTS, billing assembly | ✅ Центральный |
| `transport/telegram/webhook.py` | FastAPI router, lang detection, rate limit, commands, callback dispatch, billing записи | ✅ |
| `transport/telegram/auth_middleware.py` | Webhook secret verify + Telegram user_id extraction | ✅ |
| `transport/telegram/message_router.py` | Classify UpdateType, extract text/photo/voice/media_group | ✅ |
| `transport/telegram/callback_handler.py` | Parse callback_query → CallbackContext | ✅ |
| `llm/groq_client.py` | AsyncGroq wrapper, ToolCallResponse, context truncation | ✅ Всё через него |
| `llm/fallback_handler.py` | Tier cascade, 413 truncation, per-model params | ✅ |
| `llm/hf_client.py` | HuggingFace Inference API client (embeddings, reranker) | ✅ |
| `security/auth.py` | JWT create/verify | ✅ `verify_token` в `require_admin` dependency (июнь 2026) |
| `security/encryption.py` | Fernet encrypt/decrypt | ⏸ OPEN — отложено осознанно |
| `security/origin_guard.py` | CORS origin check | ✅ `CORSMiddleware` в `main.py` (июнь 2026) |
| `security/rate_limiter.py` | Redis sliding window rate limiter | ✅ |
| `payments/pricing_engine.py` | TON/USD price, vision_cost(), apply_margin() | ✅ |
| `payments/ton_client.py` | TON blockchain transactions | ✅ (via wallet_manager) |
| `i18n/t.py` | `t()`, `lang_instruction()`, `SUPPORTED_LANGS` | ✅ 100+ файлов |
| `i18n/strings.py` | Строки UI по языкам | ✅ |
| `observability/logger.py` | ExtraFormatter, setup_logging | ✅ |
| `observability/metrics.py` | In-memory counters/gauges, /metrics endpoint | ✅ |
| `observability/tracing.py` | contextvar-based span tracing | ✅ |
| `observability/sentry.py` | Sentry init | ✅ |
| `events/` (все 5 файлов) | Redis event bus + store + replay | ❌ publish не вызывается |
| `notifications/` (оба файла) | Email + event notifications | ❌ не вызывается |
| `context/assembler.py` | resolve_truth_mode + assemble context | ✅ |
| `context/context_models.py` | ContextChunk (внутренний тип retrieval), ContextBlock (выход assembler) | ✅ Подключён (июнь 2026) |
| `context/serializer.py` | `to_prompt_string()`, `block_to_prompt_string()`, `block_to_dict()` | ✅ Подключён (июнь 2026) |
| `retrieval/sparse/bm25_engine.py` | BM25 sparse retrieval | ✅ Подключён (июнь 2026) |
| `retrieval/fusion/hybrid_scorer.py` | RRF fusion dense+sparse | ✅ Подключён (июнь 2026) |
| `external/web_tools.py` | Tool dispatcher (weather/search/maps/translate) | ✅ Orchestrator |
| `ceyona-worker/worker.js` | Cloudflare Worker: Telegram→HF relay | ✅ Деплой |
| `infra/redis_keys.py` | Canonical Redis key registry (ключи + TTL константы) | ✅ Добавлен июнь 2026 |
| `infra/config_loader.py` | `getattr(settings, key, default)` — обёртка без ценности | ⏸ planned/unused — нигде не импортируется |
| `retrieval/retrieval_models.py` | `QueryVector`, `RetrievalMetadata`, `ScoredCandidate` | ✅ Активирован июнь 2026 |
| `context/context_mapper.py` | Граница retrieval→context: `to_context_chunks()` | ✅ Новый файл июнь 2026 |

---

## СПЕЦИФИЧЕСКИЕ НАБЛЮДЕНИЯ ПО КОДУ

### `groq_client.py` — важная заметка про compound models
В `complete_with_tools()` есть критический комментарий:
> "CRITICAL: check message.tool_calls FIRST — some compound model variants (notably groq/compound-mini) return finish_reason="stop" WITH tool_calls populated"

Это задокументировано в коде, но не в architecture.md. Это production-confirmed quirk Groq API от May 2026.

### `security/safety_gate.py` — полная инверсия роли от May 2026
Файл содержит развёрнутое объяснение почему Pass 1/2 стали NON-BLOCKING:
- 22m и safeguard-20b дают неприемлемый false-positive rate на RU/AR
- safeguard-20b не следует system prompt инструкциям (не instruction-tuned)
- blocking authority перенесена в safety_agent

Это задокументировано в architecture.md §21 — одно из редких мест где код и архитектура полностью синхронизированы.

### `app/main.py` — 3 незарегистрированных факта
1. **Wallet poller** запускается как фоновая задача (`asyncio.create_task`) каждые 10 секунд. В architecture.md не упомянут.
2. **MediaGroup callback** (`_on_group_ready`) строит синтетический update `{"_voice_transcript": ...}` и передаёт его в `handle_message` с `input_type="image_group"`. Это обходной путь для обработки альбомов через тот же pipeline что и голосовые сообщения.
3. **5 HTTP endpoints**: `/`, `/health`, `/metrics`, `/models`, `/routing`, `/debug`, `/providers`. ~~`/providers` был без decorator (BUG-3)~~ — **ЗАКРЫТО**.

### `llm/fallback_handler.py` — billing gotcha задокументирована в коде
```python
# response.actual_tier reflects the tier that actually executed,
# which may be lower than the requested tier after cascade.
# Callers MUST use response.actual_tier for billing (not the requested tier).
```
Это правильная defensive programming, но в architecture.md нет упоминания cascade billing semantics.

### `meta/analysis.py` — двойная роль
В architecture.md §4: "analysis.py (pre-reasoning hints)". Но файл также содержит `detect_repetitive_opening()` — отдельная функция которая используется в `prompt_engine.py` для детекции повторяющихся открывающих фраз. Это не "pre-reasoning hints" — это prompt assembly support. Две разные роли в одном файле.

---

## ИТОГ: ПОЛНАЯ КАРТА ПРОБЛЕМ

### Критические (runtime errors)
1. ~~**BUG-1**: `from contracts.orchestrator import EPKDecision` → `ImportError` → billing падает при многоязычных запросах~~ — **ЗАКРЫТО**
2. ~~**BUG-2**: `cost_usd=` вместо `llm_cost_usd=` в ReflectionInput → TypeError → reflection никогда не работает~~ — **ЗАКРЫТО**

### Серьёзные (функциональность отсутствует)
3. ~~**BUG-3**: `/providers` endpoint без `@app.get` декоратора → 404 всегда~~ — **ЗАКРЫТО**
4. ~~**ARCH-3**: `events/` — bootstrapped, но `publish()` не вызывается~~ → **ЧАСТИЧНО ЗАКРЫТО** (июнь 2026): balance/llm события публикуются. Open: `SafetyBlockEvent`, `RequestCompletedEvent`
5. ~~**ARCH-4**: `notifications/` — написан, но не подключён~~ → **ЧАСТИЧНО ЗАКРЫТО** (июнь 2026): `on_balance_credited` и `on_balance_exhausted` работают. Open: `on_safety_block` (зависит от ARCH-3), `on_system_error`

### Мёртвый код (занимает место, вводит в заблуждение)
6. ~~`security/auth.py` — JWT не используется~~ — **ЗАКРЫТО**: `verify_token` используется в `require_admin` в `main.py`
7. `security/encryption.py` — Fernet не используется — **OPEN** (отложено осознанно, требует key versioning)
8. ~~`security/origin_guard.py` — CORS guard не вызывается~~ — **ЗАКРЫТО**: `CORSMiddleware` подключён в `main.py`
9. ~~`context/context_models.py` — ContextChunk/ContextBlock не импортируются~~ — **ЗАКРЫТО**: `ContextChunk` — внутренний тип retrieval pipeline; `ContextBlock` — выход `assemble_chunks()`
10. ~~`context/serializer.py` — to_prompt_string() не вызывается~~ — **ЗАКРЫТО**: `to_prompt_string()` вызывается в `orchestrator.py`; добавлены `block_to_prompt_string()` и `block_to_dict()`
11. ~~`retrieval/sparse/bm25_engine.py` — BM25 не подключён к retrieval_engine~~ — **ЗАКРЫТО**: BM25 запускается параллельно с pgvector в `retrieval_engine.py`
12. ~~`retrieval/fusion/hybrid_scorer.py` — hybrid scoring не подключён~~ — **ЗАКРЫТО**: `reciprocal_rank_fusion()` вызывается в `retrieval_engine.py` после параллельных dense+sparse поисков

### Документационные пробелы (код работает, но не описан)
13. `i18n/` — самый используемый слой проекта, отсутствует в architecture.md
14. `transport/telegram/update_handler.py` — центральный pipeline handler, не упомянут
15. `app/main.py` — 3 незадокументированных механизма (wallet poller, album callback, HTTP endpoints)
16. `llm/groq_client.py` + `fallback_handler.py` + `hf_client.py` — LLM client layer без контракта
17. `security/rate_limiter.py` — живой, не задокументирован
18. `payments/pricing_engine.py` + `ton_client.py` — платёжный слой без контракта в architecture.md
19. `observability/` — 4 файла, используются везде, нет раздела в architecture.md
20. `meta/reflection.py` + `memory_audit.py` — output уходит только в логи, persistence не реализована
21. `ceyona-worker/worker.js` — Cloudflare Worker упомянут в §29, но без deployment contract

### Закрыто в июне 2026
- ~~6~~ `security/auth.py` — `verify_token` в `require_admin`
- ~~8~~ `security/origin_guard.py` — CORS middleware
- ~~9~~ `context/context_models.py` — `ContextChunk`/`ContextBlock` внутри retrieval+context pipeline
- ~~10~~ `context/serializer.py` — `to_prompt_string`, `block_to_prompt_string`, `block_to_dict`
- ~~11~~ `retrieval/sparse/bm25_engine.py` — параллельный sparse поиск
- ~~12~~ `retrieval/fusion/hybrid_scorer.py` — RRF fusion

### Новые открытые (июнь 2026)
- ~~ARCH-1~~ — **ЗАКРЫТО**: `core/execution/__init__.py` публичный фасад
- ~~ARCH-5~~ — **ЗАКРЫТО**: `ContextChunk` двухуровневые метаданные (`metadata` / `retrieval`)
- ~~ARCH-6~~ — **ЗАКРЫТО**: retrieval pipeline (dense + sparse → RRF → rerank → context)
- **ARCH-7** — `infra/config_loader.py` — planned/unused, зафиксировано осознанно, OPEN
- ~~ARCH-8~~ — **ЗАКРЫТО**: `callback_handler.py` теперь владеет и parse, и dispatch callback-логики (ранее ошибочно пронумерован как ARCH-5, см. секцию выше)

- `security/encryption.py` — Fernet отложен (key versioning + миграция)
- `retrieval/retrieval_models.py` — активирован, не задокументирован в architecture.md
- `context/context_mapper.py` — новый файл, не задокументирован в architecture.md