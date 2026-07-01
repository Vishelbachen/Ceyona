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
~~Определяет `ContextChunk` и `ContextBlock`. **Нигде не импортируется** в продуктивном коде.~~ **ЗАКРЫТО (июнь 2026):** `ContextChunk` — внутренний тип retrieval pipeline (dense→BM25→RRF→reranker). `ContextBlock` — выход `assembler.assemble_chunks()`. Двухуровневые метаданные: `metadata` (документ) и `retrieval` (процесс) разделены явными полями.

### `context/serializer.py`
~~`to_prompt_string()` и `to_dict()`. **Нигде не импортируется.**~~ **ЗАКРЫТО (июнь 2026):** `to_prompt_string()` вызывается в `orchestrator.py`. Добавлены `block_to_prompt_string(ContextBlock)` и `block_to_dict(ContextBlock)` для полного провенанс-вывода.

### ~~`retrieval/sparse/bm25_engine.py`~~ — ЗАКРЫТО (июнь 2026)
Подключён в `retrieval_engine.py`. BM25 запускается параллельно с pgvector — независимый sparse поиск по полному корпусу памяти пользователя (лимит 200 записей).

### ~~`retrieval/fusion/hybrid_scorer.py`~~ — ЗАКРЫТО (июнь 2026)
`reciprocal_rank_fusion()` вызывается в `retrieval_engine.py` после параллельных dense+sparse поисков. Настоящий hybrid: два независимых поиска → RRF → reranker.

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
- ~~`security/origin_guard.py` — **мёртвый**.~~ **ЗАКРЫТО (июнь 2026):** `CORSMiddleware` подключён в `main.py`, `allowed_origins` из settings.
- ~~`security/auth.py` — JWT нигде не вызывается.~~ **ЗАКРЫТО (июнь 2026):** `verify_token` используется в `require_admin` Depends. Защищены `/metrics`, `/models`, `/providers`, `/routing`, `/debug`. `/health` и `/webhook` открыты.
- `security/encryption.py` — Fernet не используется. **OPEN** (отложено осознанно — требует key versioning и фоновой миграции).

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
| ~~Реально мёртвые~~ → все подключены | ~~`context/context_models.py`~~, ~~`context/serializer.py`~~, ~~`retrieval/sparse/bm25_engine.py`~~, ~~`retrieval/fusion/hybrid_scorer.py`~~ — **ЗАКРЫТО июнь 2026** |
| Зомби → частично закрыты | `events/` — частично активирован (4 из 6 событий); `notifications/` — частично (2 из 4 методов); ~~`security/origin_guard.py`~~ — ЗАКРЫТО |
| Живые, нет контракта в архитектуре | `i18n/t.py`, `i18n/strings.py`, `transport/telegram/update_handler.py`, `transport/telegram/auth_middleware.py`, `transport/telegram/message_router.py`, `transport/telegram/callback_handler.py`, `llm/groq_client.py`, `llm/hf_client.py`, `llm/fallback_handler.py`, `app/main.py`, `app/settings.py`, `security/rate_limiter.py`, `payments/pricing_engine.py`, `payments/ton_client.py`, `external/web_tools.py`, `infra/redis_keys.py`, `infra/config_loader.py` (planned/unused), `context/context_models.py`, `context/serializer.py`, `context/context_mapper.py`, `retrieval/retrieval_models.py`, `retrieval/sparse/bm25_engine.py`, `retrieval/fusion/hybrid_scorer.py`, `security/auth.py`, `security/origin_guard.py` |
| Описаны концептуально, не привязаны к файлам | `core/kernel/execution_policy_kernel.py`, `core/kernel/decision_matrix.py`, `core/kernel/policy_registry.py`, `cognition/reasoning_engine.py`, `cognition/response_synthesizer.py` |
| Полностью задокументированы | остальные ~32 файла |

---

## ЧТО ДЕЛАТЬ

**Приоритет 1 — ~~Удалить или формально пометить мёртвые~~ — ЗАКРЫТО (июнь 2026):**
> Все файлы из первоначального списка мёртвого кода подключены: `context_models.py`, `serializer.py`, `bm25_engine.py`, `hybrid_scorer.py`, `auth.py` (`verify_token`), `origin_guard.py` (CORS). Остаётся `encryption.py` — отложено осознанно.

**Приоритет 1 (остаток):**
- `security/encryption.py` — Fernet шифрование `MemoryEntry.content`. Отложено: требует версионирования ключей и фоновой миграции Supabase.
- `infra/config_loader.py` — **planned/unused**. Текущее содержимое: `getattr(settings, key, default)` — обёртка без ценности. Нигде не импортируется. Потенциальная роль: единый сервис конфигурации с `get_int()`, `get_bool()`, `require()`, валидацией. Реализовывать только при реальной потребности. `/debug`, `/health` — runtime diagnostics, не их ответственность.

**Retrieval pipeline — июнь 2026 (новое):**
Полная цепочка:
```
pgvector (dense)  ─┐
                   ├→ RRF (hybrid_scorer) → reranker → RetrievedDocument
BM25 (sparse)     ─┘
       ↓
context_mapper.to_context_chunks() → ContextChunk → assembler → ContextBlock → serializer → prompt
```
Ключевые архитектурные решения:
- `ScoredCandidate` + `RetrievalMetadata` — внутренний тип retrieval слоя (retrieval_models.py)
- `RetrievalMetadata` типизирована (не dict): `dense_score`, `sparse_score`, `rrf_score`, `geo_score`, `dense_rank`, `sparse_rank`, `rerank_score`
- `context_mapper.py` — единственная точка пересечения retrieval и context слоёв
- `ContextChunk.metadata` (документ) и `ContextChunk.retrieval` (процесс) — разделены явными полями
- `RetrievedDocument.metadata` на выходе: `{"doc": {...}, "retrieval": {...}}` — структура для оркестратора

**ARCH-1 — ЗАКРЫТО (июнь 2026):** `core/execution/__init__.py` стал публичным фасадом пакета.
`update_handler.py` теперь импортирует `from core.execution import ...` — публичный API, не внутренности.
Типы остались у владельца (оркестратор). `contracts/orchestrator.py` не создавался — это было бы искусственным раздвоением ответственности.

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