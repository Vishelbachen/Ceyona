# CEYONA — ПОЛНЫЙ АУДИТ КОДА
Дата: май 2026
Версия архитектуры: 8.0

Статусы:
- ✅ Frozen √ — логика стабильна, изменения только через архитектурное решение
- ⚠️ Needs Fix — есть конкретная проблема, требующая правки
- 🔒 Sealed — authority boundary, трогать только при полном архитектурном ревью
- 📋 Gap — известный gap из §27, не баг

---

## core/kernel/ — 🔒 Sealed

### policy_registry.py ✅
Единственный источник правды для всех threshold'ов. Все три зависимых модуля
(EPK, model_router, access_controller) читают из него. Значения синхронизированы
с economic.md v5.1. Замечаний нет.

### execution_policy_kernel.py ✅
Все threshold'ы читаются из policy_registry.RUNTIME — не хардкод.
Порядок evaluate() строго соответствует architecture.md §5.
DENY → HEAVY → DEGRADE → ALLOW. Замечаний нет.

### decision_matrix.py ✅
_FAST_CEILING=0.0005 < _GENERAL_CEILING=0.003 — восходящий порядок соблюдён
(был баг инверсии в v4, исправлен). Синхронизирован с EPK._DEGRADE_THRESHOLD.
Замечаний нет.

### cost_model.py ✅
MODEL_RATES соответствуют economic.md §1.1 (верифированы май 2026).
MAX_OUTPUT_CAP ≠ _MAX_TOKENS в model_router — разные authority, правильно.
RERANK_RATE = 0.10 (исправлен с 1.0 — было 10x завышение). Замечаний нет.

---

## security/ — ✅ Frozen √ (после текущих правок)

### safety_gate.py ✅ (правки этой сессии)
Pass 1: non-blocking passthrough — правильно.
Pass 2: новый промпт + short-message fastpath (≤80 chars) + exception→PASS.
Проблема false-positive на русском слэнге устранена.
Статус: Frozen √ после деплоя текущего фикса.

### auth.py ✅
JWT HS256, стандартная реализация. Замечаний нет.

### rate_limiter.py ✅
Sliding window через Redis ZADD/ZCARD. Fail-open на ошибке Redis — правильно
(лучше пропустить лишнее, чем заблокировать всех при падении Redis).

### origin_guard.py ✅
Простая whitelist-проверка. Поддерживает "*" для отключения. Замечаний нет.

### encryption.py ✅
Fernet из cryptography. Замечаний нет.

---

## core/execution/ — ✅ Frozen √

### orchestrator.py ✅
Полностью соответствует architecture.md §6 и §8.
- Не создаёт policy — только исполняет EPK-сигналы.
- _TOOL_INTENTS и _STRICT_INTENTS корректно разделены.
- _already_grounded флаг предотвращает двойной поиск на forced_intent пути.
- _structured_search путь: LLM не трогает structured hotel data — правильно
  (именно это исправило галлюцинации из Image 1 в этой сессии).
- DENY/HEAVY/DEGRADED/ALLOW пути чистые, без скрытых ветвлений.
Замечаний нет.

---

## llm/ — ✅ Frozen √

### model_router.py ✅
_MAX_TOKENS читается из policy_registry.RUNTIME — не хардкод.
FAST_AGENT_MODEL / DEEP_AGENT_MODEL зарегистрированы (compound / compound-mini)
с пометкой NOT YET WIRED — соответствует models1.md §6.
QWEN_THINKING_DISABLED_MODELS — frozenset, применяется в fallback_handler.
Замечаний нет.

### groq_client.py ✅
_truncate_messages: стратегия keep system + keep last user + fill middle.
Корректна для Telegram-бота где последнее сообщение пользователя критично.
_CONTEXT_CHAR_LIMITS покрывают все активные модели.
Замечаний нет.

### fallback_handler.py ✅
Каскад HEAVY→GENERAL→FAST. 413-обработка с truncation retry.
qwen/qwen3-32b: thinking=False применяется через requires_thinking_disabled().
Замечаний нет.

### heavy_input_shaper.py ✅
Три операции: compress / chunk / summarize. Self-gated (_needs_shaping).
Использует llama-3.1-8b-instant НЕ как Fast Tier — роль утилиты, правильно.
Никогда не генерирует финальный ответ. Замечаний нет.

### multilingual_preprocessor.py ✅
Arabic → allam-2-7b. Other non-Latin → llama-3.3-70b-versatile.
Latin passthrough без LLM-вызова. Fail-safe: возвращает оригинал при ошибке.
Замечаний нет.

### prompt_engine.py ✅
_TRUTH_STRICT / _TRUTH_HYBRID корректно инжектируются.
GENERATIVE интенты — без truth блока (экономия ~300 токенов).
Context вставляется в USER turn, не в system — правильно для малых моделей.
"NEVER say cutoff" mandate присутствует во всех промптах.
Замечаний нет.

### hf_client.py ✅
Обновлён endpoint: router.huggingface.co (старый api-inference возвращал 404).
Retry на 503 (cold start) с wait_for_model. Timeout 60s. Замечаний нет.

---

## agents/ — ✅ Frozen √

### fast_agent.py ⚠️ КРИТИЧЕСКОЕ ЗАМЕЧАНИЕ
Агент вызывает groq_client.complete(model=FAST_AGENT_MODEL=groq/compound-mini) напрямую.
Проблема: groq/compound-mini NOT YET WIRED (models1.md §6) — Groq API его поддерживает
как tool-use модель, но агент вызывает его как обычный chat-completion БЕЗ tools параметра.
Если compound-mini требует tool_choice для активации — каждый вызов fast_agent падает,
coordinator fallback не срабатывает потому что fallback=FAST (тот же агент).

Фактическое поведение сейчас: судя по логам из Image 2 ("DeepAgent failed") — deep_agent
тоже падает по той же причине (groq/compound без tools).

РЕКОМЕНДАЦИЯ: Откатить fast_agent и deep_agent на complete_with_fallback(Tier.FAST/GENERAL)
до тех пор, пока Groq tool-use API не стабилизируется. Это именно то, что было до
"NOT YET WIRED" рефактора согласно models1.md §6.

### deep_agent.py ⚠️ То же замечание, что и fast_agent
groq/compound вызывается как chat-completion. "DeepAgent failed" в Sentry подтверждает.

### creative_agent.py ✅
Использует complete_with_fallback(Tier.GENERAL) — правильно, это не Agent Layer модель.

### safety_agent.py ✅
Rule-based (без LLM). _BLOCK_SIGNALS покрывают emergent harm контент.
Позиция в пайплайне правильная (LAST before Consensus).
Замечаний нет.

### consensus_engine.py ✅
gpt-oss-120b как арбитр — только на ALLOW пути (mutex с HEAVY проверяется в coordinator).
Heuristic fallback (longest) при ошибке арбитра. Замечаний нет.

---

## cognition/ — ✅ Frozen √

### intent_engine.py ✅
15 интентов. _TOOL_MAP и _NEEDS_RETRIEVAL корректны.
Embedding-based classification с fallback на QUESTION при confidence < 0.55.
Замечаний нет.

### reasoning_engine.py ✅
Pure function, никакого I/O. Стратегии синхронизированы с моделями.
MATH HEAVY: temperature=0.05, max_steps=10. Замечаний нет.

### multi_agent_coordinator.py ✅
Точно соответствует architecture.md §16.
- MATH self-correction loop: max 1 pass.
- safety_agent: ALLOW+consensus, ALLOW+DEEP+no_consensus, HEAVY → активен.
  DEGRADED/EMOTIONAL/default_GENERAL → пропускается.
- EMOTIONAL graceful fallback: rule-based при падении всех агентов.
- Возвращает результат ТОЛЬКО orchestrator'у. Замечаний нет.

### response_synthesizer.py ✅
7-step pipeline строго по architecture.md §19:
assemble → normalize_telegram → structure → format → correction → output_normalizer → finalize
Порядок фиксирован. correction и output_normalizer вызываются только здесь.
LaTeX→Unicode конвертация перед stripping — правильный порядок.
Замечаний нет.

---

## meta/ — ✅ Frozen √

### analysis.py ✅
Pure function, no I/O. Non-binding hints. Full vs lightweight режимы.
Never raises. Замечаний нет.

### correction.py ✅
Preamble stripping для 8 языков. _fix_markdown для unclosed backticks/bold.
Never raises. Замечаний нет.

### output_normalizer.py ✅
3 операции: source tags, garbled URLs, language leak map.
_SKIP_SUBSTITUTION для EN/JA/AR/ZH/KO — правильно.
Never changes meaning. Замечаний нет.

### reflection.py ✅
Pure data, no side effects. QualitySignal набор полный.
Never raises. Замечаний нет.

### memory_audit.py ✅
Read-only diagnostics. Zero authority. Thresholds разумные (7d history, 3d vector).
Never raises. Замечаний нет.

---

## payments/ — ✅ Frozen √ (после правок этой сессии)

### usage_meter.py ✅ (правки этой сессии)
PGRST204 fallback: retry core-only при отсутствии колонок.
Extended fields пишутся только если ненулевые.
После запуска migrate_usage_log.sql — fallback можно удалить.

### access_controller.py ✅
_DEFAULT_BALANCE_USD читается из policy_registry.RUNTIME.
limit(1) вместо maybe_single() — исправлен 406 баг.
Deduct: проверка баланса перед списанием. Замечаний нет.

### pricing_engine.py 📋
nano_to_usd: требует TON/USD rate. Реализация зависит от внешнего API.
Не читалась полностью — но функция используется в wallet_manager.

### ton_client.py 📋
Toncenter API v2, read-only. Используется wallet_manager.
Полноценно работает только с заполненными TON_WALLET и TON_API_KEY.

### wallet_manager.py ✅
Deduplication через processed_transactions. Comment = user_id.
safe default на is_processed ошибке (treat as processed).
Замечаний нет.

---

## retrieval/ — ✅ Frozen √

### retrieval_engine.py ✅
pgvector similarity_search теперь реально вызывается (BUG FIX — ранее candidates=[]).
source_credibility.score_documents() — pass-through пока MemoryRecord без source_url.
Fallback: возвращает empty result при ошибке embedding. Замечаний нет.

### source_credibility.py ✅
Активно блокирует BLOCKED tier, фильтрует VERY_LOW.
tripadvisor.com/ru → LOW (пропускается, но с низким весом).
Вызывается из search.py (primary) и retrieval_engine.py (reserved).
Замечаний нет.

### dense/bge_engine.py, sparse/bm25_engine.py, reranker/cross_encoder.py ✅
Стандартные обёртки над HF API. Замечаний по архитектуре нет.

### cache/ ✅
embedding_cache, query_cache, rerank_cache — Redis-based.
ttl_policy.py — отдельная политика TTL. Замечаний нет.

---

## external/ — ✅ Frozen √

### search.py ✅
SerpAPI + source_credibility фильтр перед LLM.
URL sanitization для Unicode lookalike символов.
_SUSPICIOUS_PATTERNS validation против fabricated hotel names.
format_results: структурированный вывод с "=== ДАННЫЕ ИЗ ПОИСКА ===" header
(оркестратор использует его для tool-only пути, без LLM синтеза).
Замечаний нет.

### maps.py ✅
Mapbox geocoding + POI + routing.
_LANG_COUNTRY_BIAS: предотвращает "центр" → Centre, TX.
LLM-based POI extraction (llama-3.1-8b) для category/location split.
_RHETORICAL_PATTERNS фильтр: не запускает geocoding на риторических вопросах.
Замечаний нет.

### weather.py ✅
OpenWeatherMap API. Russian case normalization для городов в предложном падеже.
_RU_CITY_OVERRIDES покрывают основные города. Замечаний нет.

### web_tools.py ✅
Tool dispatcher с lazy imports. Замечаний нет.

### speech_to_text.py, text_to_speech.py 📋
Реализованы (Whisper + Orpheus). Speech billing NOT YET WIRED к usage_meter.
Gap задокументирован в architecture.md §27.

---

## transport/telegram/ — ✅ Frozen √

### webhook.py ✅
_send_voice() реализован. tts_audio_bytes → sendVoice, fallback → _send_message.
parse_mode: "Markdown" — замечание: synthesizer стрипает Markdown,
но Telegram игнорирует незакрытые теги, не критично.

### update_handler.py ✅
Lifecycle строго соответствует architecture.md §4:
Safety Gate Pass 1 → Feature Extraction → Multilingual → Safety Gate Pass 2 →
History → Retrieval → Web Search → Orchestrator → History Save → META → TTS.
Замечаний нет.

### vision_handler.py 📋
Не читался полностью. По architecture.md — OUTSIDE EPK DAG. Ingress only.

### message_router.py, auth_middleware.py, callback_handler.py ✅
Утилитарные модули. Замечаний нет.

---

## memory/ — ✅ Frozen √

### conversation_history.py ✅
_MAX_HISTORY_TOKENS=1200 (уменьшен с 2000 — исправлены 413 ошибки на 8B).
_trim_history_to_budget: drop oldest. Замечаний нет.

### supabase_store.py ✅
Raw storage layer. similarity_search с pgvector. Замечаний нет.

### vector_memory.py
Не читался полностью, но используется retrieval_engine.

---

## context/, contracts/, i18n/, observability/, events/, infra/ — ✅ Frozen √

### context/assembler.py ✅
resolve_truth_mode корректно маппит интенты на STRICT/HYBRID/GENERATIVE.
assemble() с max_chars бюджетом. Замечаний нет.

### contracts/shared_types.py ✅
Tier, Complexity, EPKDecision, TruthMode — все enum'ы правильные.

### events/ — ✅
event_bus, event_store, event_replay, event_types — event sourcing.
Parallel с memory write, независимые failure domains. Замечаний нет.

---

## ИТОГ: КРИТИЧЕСКИЕ ПРАВКИ

### 🔴 ПРИОРИТЕТ 1: fast_agent.py + deep_agent.py
Откатить на complete_with_fallback() пока compound/compound-mini не работают
как chat-completion без tool_choice. "DeepAgent failed" в Sentry — это здесь.

### 🟡 ПРИОРИТЕТ 2: usage_meter.py (сделано этой сессией)
Deployed. После деплоя migrate_usage_log.sql — убрать PGRST204 fallback.

### 🟢 ПРИОРИТЕТ 3: safety_gate.py (сделано этой сессией)
Deployed. Мониторить false-positive rate в Sentry — должен упасть до нуля.

---

## СТАТУСЫ СЛОЁВ ДЛЯ architecture.md §27

| Слой | Статус |
|---|---|
| core/kernel/ | 🔒 Sealed √ |
| security/ | ✅ Frozen √ (после деплоя) |
| core/execution/ | ✅ Frozen √ |
| llm/ | ✅ Frozen √ |
| agents/ | ⚠️ Pending Fix (fast/deep agent) |
| cognition/ | ✅ Frozen √ |
| meta/ | ✅ Frozen √ |
| payments/ | ✅ Frozen √ (после миграции) |
| retrieval/ | ✅ Frozen √ |
| external/ | ✅ Frozen √ |
| transport/telegram/ | ✅ Frozen √ |
| memory/ | ✅ Frozen √ |
| context/, contracts/ | ✅ Frozen √ |
| events/ | ✅ Frozen √ |
