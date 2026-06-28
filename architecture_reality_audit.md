# Ceyona — Architecture vs Reality: Full Audit
*Проверено по коду из zip + architecture.md*

---

## ИТОГ ВЕРХНЕГО УРОВНЯ

architecture.md описывает **32 файла** по имени (с полным путём). В репозитории **91 Python-файл** (без `__init__` и тестов). Из них:

- **Полностью задокументированы:** ~32 файла
- **Живые, но не упомянуты в архитектуре:** 40+ файлов
- **Реально мёртвые (не импортируются нигде в продуктивном коде):** 5 файлов
- **Зомби (bootstrapped, но publish не вызывается никогда):** целая подсистема events/

---

## КАТЕГОРИЯ 1 — РЕАЛЬНО МЁРТВЫЕ ФАЙЛЫ

Код существует, нигде не импортируется, роль поглощена другим файлом.

### `context/context_models.py`
Определяет `ContextChunk` и `ContextBlock`. **Нигде не импортируется** в продуктивном коде. Те же концепции живут в `contracts/context_contracts.py`. Подтверждено: GPT прав, это мёртвый файл.

### `context/serializer.py`
`to_prompt_string()` и `to_dict()`. **Нигде не импортируется.** Конвертация `AssembledContext → str` делается инлайн в `prompt_engine.py`. Мёртвый файл.

### `retrieval/sparse/bm25_engine.py`
`BM25Engine` **нигде не импортируется** — ни в `retrieval_engine.py`, ни в `hybrid_scorer.py`, ни в bootstrap. Задуман для sparse retrieval, но retrieval_engine использует только dense (BGE) + reranker.

### `retrieval/fusion/hybrid_scorer.py`
`HybridScorer` **нигде не импортируется.** Hybrid fusion (dense + sparse) не реализован в production pipeline. Нет упоминания в architecture.md.

### `notifications/event_notifier.py` + `notifications/email_service.py`
`EventNotifier.on_balance_credited()`, `on_safety_block()` etc. **Нигде не вызываются** в продуктивном коде (только в тестах `test_coverage_gap3/4.py`). Синглтон `event_notifier` создан, но не подключён ни к wallet_manager, ни к safety_gate, ни к orchestrator.

> **UPDATE (июнь 2026):** Частично подключено. `event_dispatcher.py` теперь вызывает `event_notifier.on_balance_credited()` через `BALANCE_CREDITED` подписку, и `on_safety_block()` через `SAFETY_BLOCK`. `wallet_manager` публикует `BalanceCreditedEvent` в EventBus. `notifications/` больше не полностью зомби — email уведомления при пополнении баланса работают.

---

## КАТЕГОРИЯ 2 — ЗОМБИ-ПОДСИСТЕМА: events/

Самое интересное. Подсистема **архитектурно полноценная**, но **полностью отвязана от потока запросов**.

### Что есть:
- `events/event_bus.py` — pub/sub шина
- `events/event_store.py` — Redis-хранилище с TTL 30 дней
- `events/event_dispatcher.py` — регистрирует handlers: лог + store
- `events/event_replay.py` — replay событий из store
- `events/event_types.py` — типы событий (`BaseEvent`)

### Что происходит в реальности:
1. `bootstrap.py` инициализирует `EventStore`, вызывает `setup_dispatcher(event_bus, store)` — handlers зарегистрированы ✅
2. `event_store` кладётся в `app.state["event_store"]` ✅
3. **Но `event_bus.publish()` не вызывается НИГДЕ.** Ни в `update_handler`, ни в `orchestrator`, ни в `webhook`, ни в `usage_meter`.

Итог: шина работает, store подключён.

> **UPDATE (июнь 2026):** Подсистема частично активирована:
> - `wallet_manager.py` публикует `BalanceCreditedEvent` ✅
> - `webhook.py` публикует `BalanceExhaustedEvent` и `RequestDeniedEvent` ✅  
> - `llm/fallback_handler.py` публикует `LLMFallbackEvent`, `LLMCalledEvent` ✅
> - `event_dispatcher` подписан на `BALANCE_CREDITED` → email + `store.clear_low_balance_warning()` ✅
> - `event_dispatcher` подписан на `BALANCE_EXHAUSTED` → email ✅
> - `event_dispatcher` подписан на `SAFETY_BLOCK` → log ✅
> 
> Не публикуются (open): `SafetyBlockEvent` из coordinator/safety_agent, `RequestCompletedEvent` из update_handler. Подсистема больше не dead end, но покрытие неполное.

---

## КАТЕГОРИЯ 3 — ЖИВЫЕ, НО АРХИТЕКТУРНО "НЕВИДИМЫЕ"

Файлы активно используются, но в architecture.md нет их описания или контракта.

### `security/origin_guard.py`
**Нигде не импортируется** в продуктивном коде (кроме `__init__`). В architecture.md `security/` упоминается только как `safety_gate` в §21. `origin_guard`, `auth.py`, `rate_limiter`, `encryption` — не задокументированы.

- `security/auth.py` — используется в `webhook.py`, `update_handler.py`, `vision_handler.py` (проверка Telegram токена). **Живой, не задокументирован.**
- `security/rate_limiter.py` — подключён в `webhook.py` и `bootstrap.py`. **Живой, не задокументирован.**
- `security/encryption.py` — используется в `app/main.py`, `settings.py`, `env_validator.py`. **Живой, не задокументирован.**
- `security/origin_guard.py` — **мёртвый или только в __init__ re-export.** Нигде не вызывается.

### `transport/telegram/` — роль расплылась
architecture.md описывает только `media_group_aggregator` (§42) и `vision_handler` (§15).

Не описаны:
- `auth_middleware.py` — middleware аутентификации для FastAPI. Используется в `main.py`. Нет контракта.
- `callback_handler.py` — парсит Telegram callback_query. Используется в `webhook.py`. GPT был прав: монетизационная логика частично осталась здесь вместо того чтобы жить в `payments/`. Нет контракта в архитектуре.
- `message_router.py` — маршрутизирует входящие сообщения по типу. Живой, не задокументирован.
- `update_handler.py` — **центральный обработчик запросов**, инициализирует весь pipeline. В architecture.md не упомянут вообще. Это самый критичный пропуск.
- `webhook.py` — точка входа FastAPI. Упомянут косвенно (§4 lifecycle начинается с "User Input"), но explicit ownership отсутствует.

### `i18n/` — целый слой без контракта
- `i18n/t.py` — **импортируется в 100+ файлов** (буквально самый используемый модуль в проекте). `t()`, `lang_instruction()`, `SUPPORTED_LANGS`. В architecture.md не упомянут ни разу.
- `i18n/strings.py` — строки ответов по языкам. Используется везде. Не упомянут.

### `app/main.py` и `app/settings.py`
Точки входа FastAPI приложения. В architecture.md есть только `app/bootstrap.py` (§26.4). `main.py` и `settings.py` не описаны.

### `llm/fallback_handler.py`, `llm/groq_client.py`, `llm/hf_client.py`
Все три — критические компоненты: клиент Groq, клиент HuggingFace, fallback логика. **Импортируются в 25+ файлах каждый.** В architecture.md не задокументированы. `groq_client` — буквально единственный способ вызвать LLM, и у него нет описания контракта.

### `cognition/reasoning_engine.py` и `cognition/response_synthesizer.py`
`response_synthesizer` описан в §19 (9-step pipeline), но под именем просто "synthesizer" без явного указания что это `cognition/response_synthesizer.py`. `reasoning_engine.py` — упомянут в §7 концептуально ("Reasoning Engine"), но не привязан к файлу.

### `core/kernel/` — EPK описан, файлы не привязаны
EPK описан в §5 подробно, но не указано явно что EPK = `core/kernel/execution_policy_kernel.py`. Аналогично `cost_model.py` = §8, `decision_matrix.py` = §8, `policy_registry.py` = §26 (vision_handler раздел) — всё это требует угадывания.

### `retrieval/` — cache layer подвешен
- `retrieval/cache/` (4 файла): инициализируются в `update_handler.py`, передаются в `RetrievalEngine`. Описаны в architecture.md §20 лишь вскользь ("MemoryRecord.source_url... Token rates... to be audited"). Нет явного контракта.
- Кэши инжектируются только когда Redis доступен — graceful degradation реализована, но нигде не задокументирована.

### `payments/pricing_engine.py` и `payments/ton_client.py`
Активно используются (`pricing_engine` → `usage_meter`, `wallet_manager`; `ton_client` → `wallet_manager`). В architecture.md payments описаны через `usage_meter`, `wallet_manager`, `access_controller` — но не через `pricing_engine` и `ton_client`. Ownership TON-транзакций не задокументировано.

### `external/web_tools.py`
Используется в `orchestrator.py` (вызов инструментов — weather, maps). В architecture.md есть `external/search.py` (§28), `speech_to_text` (§32), `text_to_speech` (§33), `external/maps.py` (§11), но `web_tools.py` как orchestration-facing API не описан.

---

## КАТЕГОРИЯ 4 — РОЛЬ "ПОПЛЫЛА"

### `transport/telegram/callback_handler.py`
GPT правильно указал: файл содержит `CallbackAction`, `CallbackContext`, `parse_callback()` — это хороший контракт. Но монетизационная dispatching логика осталась в `webhook.py` вместо отдельного `billing_handlers/`. В architecture.md про callback_handler нет ни слова.

### `meta/analysis.py` — роль расширилась
В architecture.md (§4 lifecycle): "analysis.py (pre-reasoning hints) [IMPLEMENTED ✅ — see §27]". Но `analysis.py` также импортируется в `model_router.py` и `prompt_engine.py`. Роль шире чем "pre-reasoning hints" — нет полного контракта.

### `meta/reflection.py`
Описан в lifecycle (§4) как "META Side-channel (reflection + memory_audit — async, non-blocking)". Но в `update_handler.py` reflection также вызывается — и там же `memory_audit`. Принцип "async, non-blocking side-channel" выглядит соблюдённым, но явного контракта файла нет.

---

## ИТОГОВАЯ ТАБЛИЦА

| Статус | Файлы |
|---|---|
| Реально мёртвые | `context/context_models.py`, `context/serializer.py`, `retrieval/sparse/bm25_engine.py`, `retrieval/fusion/hybrid_scorer.py` |
| Зомби (bootstrapped, но не используется) | `events/` (весь слой), `notifications/` (весь слой), `security/origin_guard.py` |
| Живые, нет контракта в архитектуре | `i18n/` (оба файла), `transport/telegram/update_handler.py`, `transport/telegram/auth_middleware.py`, `transport/telegram/message_router.py`, `transport/telegram/callback_handler.py`, `llm/groq_client.py`, `llm/hf_client.py`, `llm/fallback_handler.py`, `app/main.py`, `app/settings.py`, `security/auth.py`, `security/rate_limiter.py`, `security/encryption.py`, `payments/pricing_engine.py`, `payments/ton_client.py`, `external/web_tools.py`, **`infra/redis_keys.py` (новый, июнь 2026)** |
| Описаны концептуально, не привязаны к файлам | `core/kernel/execution_policy_kernel.py`, `core/kernel/decision_matrix.py`, `core/kernel/policy_registry.py`, `cognition/reasoning_engine.py`, `cognition/response_synthesizer.py` |
| Полностью задокументированы | остальные ~32 файла |

---

## ЧТО ДЕЛАТЬ

**Приоритет 1 — Удалить или формально пометить мёртвые:**
- `context/context_models.py`, `context/serializer.py` → удалить
- `retrieval/sparse/bm25_engine.py`, `retrieval/fusion/hybrid_scorer.py` → пометить как `# planned, not wired`

**Приоритет 2 — Подключить или явно закрыть зомби:**
- `events/` — ~~либо начать publish в update_handler (при успешном ответе, при billing событиях), либо удалить всю подсистему~~ **Частично закрыто (июнь 2026):** `BalanceCreditedEvent`, `BalanceExhaustedEvent`, `RequestDeniedEvent`, `LLMFallbackEvent` публикуются. Остаётся: `SafetyBlockEvent` из coordinator, `RequestCompletedEvent` из update_handler.
- `notifications/` — ~~либо подключить к wallet_manager (on_balance_credited) и safety_gate (on_safety_block), либо удалить~~ **Частично закрыто (июнь 2026):** `on_balance_credited` и `on_balance_exhausted` подключены через EventBus. Остаётся: `on_safety_block` вызывается из dispatcher, но `SafetyBlockEvent` не публикуется из coordinator.

**Приоритет 3 — Задокументировать в architecture.md:**

> **UPDATE (июнь 2026):** Добавлен `infra/redis_keys.py` — canonical Redis key registry. Canonical rule: все новые Redis-ключи добавляются сюда; старые мигрируются при касании модуля. Не описан в architecture.md — добавить в §infra или §26 (bootstrap/infra layer).
- §N: `i18n/` — контракт локализации, ownership `t.py`
- §N: `transport/telegram/update_handler.py` — это main request handler, центральнее чем webhook
- §N: `llm/groq_client.py`, `llm/hf_client.py`, `llm/fallback_handler.py` — LLM client layer
- §N: `security/` полный контракт всех 5 файлов
- §N: `payments/pricing_engine.py`, `payments/ton_client.py`