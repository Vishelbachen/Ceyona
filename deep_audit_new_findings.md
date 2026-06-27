# Ceyona — Deep Audit: Новые Находки
*Полный анализ кода, не покрытый первым отчётом*

---

## НОВЫЕ БАГИ (не задокументированы нигде)

### BUG-1: `contracts/orchestrator.py` не существует, но импортируется
**Файл:** `transport/telegram/webhook.py`, строка 477

```python
from contracts.orchestrator import EPKDecision as _EPKDecision
```

**Факт:** `contracts/orchestrator.py` не существует. Файл `contracts/` содержит только:
`context_contracts.py`, `retrieval_contracts.py`, `shared_types.py`.

`EPKDecision` находится в `contracts/shared_types.py`.

**Когда крашит:** этот импорт находится внутри блока billing в `webhook.py` и срабатывает только когда `result.multilingual_input_tokens > 0` на не-HEAVY пути. Т.е. при каждом запросе с многоязычной нормализацией (нелатинский текст) → `ImportError` → billing падает → деньги не списываются.

**Исправление:** заменить на `from contracts.shared_types import EPKDecision as _EPKDecision`

---

### BUG-2: `ReflectionInput` вызывается с неверным именем поля
**Файл:** `transport/telegram/update_handler.py`, строка ~709

```python
ref_input = ReflectionInput(
    ...
    cost_usd=result.usage.llm_cost_usd,   # ← НЕВЕРНО
    ...
)
```

**Факт:** поле в `meta/reflection.py` называется `llm_cost_usd: float`, а не `cost_usd`. Это `TypeError` при каждом запросе в meta side-channel. Поскольку вся reflection обёрнута в `try/except`, он молча глотается и логируется как "Meta layer failed (non-critical)".

**Эффект:** reflection никогда не работает. `logger.info("Reflection", ...)` никогда не вызывается.

---

### BUG-3: `/providers` endpoint не имеет `@app.get` декоратора
**Файл:** `app/main.py`, строка 395

```python
async def providers(request: Request):  # ← нет @app.get("/providers")
    ...
```

Функция определена, но не зарегистрирована как FastAPI route. GET `/providers` вернёт 404. Судя по размеру (200+ строк с проверками Redis, Supabase, Groq, Telegram и т.д.) — это должен был быть полноценный diagnostic endpoint.

---

### BUG-4: `security/encryption.py` и `security/auth.py` — мёртвый код
Оба файла упоминаются в `app/settings.py` и `infra/env_validator.py` как проверка наличия env vars (`encryption_key`, `jwt_secret`), но сами функции:
- `encrypt()` / `decrypt()` — **нигде не вызываются**
- `create_token()` / `verify_token()` — **нигде не вызываются**

`security/auth.py` с JWT создан для чего-то (возможно, планировался REST API с авторизацией), но Telegram bot не использует JWT вообще — аутентификация идёт через Telegram update signature в `auth_middleware.py`.

`encryption.py` — Fernet шифрование, но никакие данные не шифруются. Возможно, планировалось шифровать webhook payload или данные пользователей в Supabase.

---

### BUG-5: `security/origin_guard.py` — мёртвый код
`is_allowed_origin()` проверяет `settings.allowed_origins`, но нигде не вызывается. CORS настройка через `allowed_origins` env var существует, но FastAPI CORS middleware с ней не подключён нигде в `main.py`.

---

## АРХИТЕКТУРНЫЕ РАСХОЖДЕНИЯ

### ARCH-1: `OrchestratorResult` определён в `core/execution/orchestrator.py`, а не в `contracts/`

`update_handler.py` и `webhook.py` импортируют `OrchestratorResult`, `OrchestratorRequest`, `UsageRecord` напрямую из `core.execution.orchestrator`. По принципу Single Policy Authority (architecture.md §2.1) и по смыслу contracts layer — эти типы должны жить в `contracts/orchestrator.py`. Тогда `transport` не импортировал бы из `core.execution` напрямую.

Текущий importlinter (`canonical_layer_order`) это не запрещает (transport → core.execution разрешён по слоям), но архитектурно неправильно: контракт между слоями должен жить в `contracts/`, а не внутри `core/execution/`.

---

### ARCH-2: `meta/reflection.py` и `meta/memory_audit.py` — pure functions без persistence

Оба файла — это чистые функции без I/O, без записи в Sentry, без публикации в event_bus:
- `reflect()` → возвращает `ReflectionReport` → caller делает `logger.info("Reflection", ...)`
- `audit()` → возвращает `AuditReport` → caller делает `logger.warning("Memory audit", ...)` если не healthy

Данные уходят только в лог. **Не пишутся в Supabase, не пишутся в Redis, не пишутся в EventStore (который всё равно не получает publish).** Вся "observability side-channel" — это просто `logger.info/warning`.

Architecture.md §4 описывает их как "META Side-channel (reflection + memory_audit — async, non-blocking)" — это технически выполнено, но ценность от этого side-channel фактически нулевая, так как логи без агрегации = необработанный шум.

---

### ARCH-3: `events/` — полная зомби-подсистема (подтверждено глубоко)

EventStore хранит события в Redis с TTL 30 дней, EventReplay может воспроизводить их по user_id и по имени события. Инфраструктура для audit trail, debug replay, и user event history полностью построена.

Но `event_bus.publish()` не вызывается ни разу. Полная карта событий которые должны были публиковаться:

| Событие | Где должно было вызываться |
|---|---|
| balance_credited | `payments/wallet_manager.py` при successful TopUp |
| balance_exhausted | `webhook.py` при `deny_reason == "insufficient_balance"` |
| safety_block | `cognition/multi_agent_coordinator.py` при BLOCK verdict |
| request_completed | `transport/telegram/update_handler.py` в конце handle_message |
| request_denied | `webhook.py` при `result.denied == True` |

`events/event_types.py` содержит `EPKDecisionEvent`, `SafetyEvent` и др. — типы определены, но никогда не создаются.

---

### ARCH-4: `notifications/event_notifier.py` — события без триггера

`EventNotifier` имеет методы: `on_balance_credited`, `on_balance_exhausted`, `on_safety_block`, `on_system_error`. Все написаны корректно (логирование + опциональный email).

Но: `event_notifier` (singleton) **нигде не вызывается** в продуктивном коде. `wallet_manager.process_incoming()` успешно кредитует баланс → не уведомляет. `safety_agent` блокирует ответ → не уведомляет.

Это связано с events/: `event_notifier` должен был вызываться из обработчиков событий EventBus, но EventBus не получает publish.

---

### ARCH-5: `transport/telegram/callback_handler.py` — контракт есть, dispatch — в webhook

`callback_handler.py` правильно определяет `CallbackAction` enum и `parse_callback()`. Но весь if/elif dispatch по `ctx.action` (BALANCE, TOPUP, HELP, CANCEL) живёт прямо в `webhook.py` (строки ~380-430).

GPT и архитектура правы: должен быть отдельный `dispatch_callback(ctx)`, который маршрутизирует в `balance_handler`, `topup_handler` и т.д. Сейчас `webhook.py` знает про "topup", "balance" — нарушение Single Responsibility.

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
| `security/auth.py` | JWT create/verify | ❌ Нигде не вызывается |
| `security/encryption.py` | Fernet encrypt/decrypt | ❌ Нигде не вызывается |
| `security/origin_guard.py` | CORS origin check | ❌ Нигде не вызывается |
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
| `context/context_models.py` | ContextChunk, ContextBlock | ❌ Мёртвый |
| `context/serializer.py` | to_prompt_string() | ❌ Мёртвый |
| `retrieval/sparse/bm25_engine.py` | BM25 sparse retrieval | ❌ Не подключён |
| `retrieval/fusion/hybrid_scorer.py` | Dense+sparse fusion | ❌ Не подключён |
| `external/web_tools.py` | Tool dispatcher (weather/search/maps/translate) | ✅ Orchestrator |
| `ceyona-worker/worker.js` | Cloudflare Worker: Telegram→HF relay | ✅ Деплой |

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
3. **5 HTTP endpoints**: `/`, `/health`, `/metrics`, `/models`, `/routing`, `/debug`. `/providers` — зарегистрирован, но без decorator (см. BUG-3).

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
1. **BUG-1**: `from contracts.orchestrator import EPKDecision` → `ImportError` → billing падает при многоязычных запросах
2. **BUG-2**: `cost_usd=` вместо `llm_cost_usd=` в ReflectionInput → TypeError → reflection никогда не работает

### Серьёзные (функциональность отсутствует)
3. **BUG-3**: `/providers` endpoint без `@app.get` декоратора → 404 всегда
4. **ARCH-3**: `events/` — bootstrapped, но `publish()` не вызывается → аудит trail отсутствует, event replay бесполезен
5. **ARCH-4**: `notifications/` — написан, но не подключён → нет email уведомлений при пополнении/исчерпании баланса

### Мёртвый код (занимает место, вводит в заблуждение)
6. `security/auth.py` — JWT не используется
7. `security/encryption.py` — Fernet не используется
8. `security/origin_guard.py` — CORS guard не вызывается
9. `context/context_models.py` — ContextChunk/ContextBlock не импортируются
10. `context/serializer.py` — to_prompt_string() не вызывается
11. `retrieval/sparse/bm25_engine.py` — BM25 не подключён к retrieval_engine
12. `retrieval/fusion/hybrid_scorer.py` — hybrid scoring не подключён

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