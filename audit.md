# CEYONA — ARCHITECTURE AUDIT
**Дата:** май 2026  
**Проверено:** architecture.md v8.1, models1.md v7.1, economic.md v5.1 + весь runtime код  
**Статус:** 10 категорий × верификация кода. Последнее обновление: май 2026.

Обозначения: ✅ Закрыто | ⚠️ Открыто / known gap | 🔴 Критично | 📋 Not yet wired (намеренно)

---

## 1. HIDDEN NONDETERMINISM

### 1.1 ✅ EPK — детерминирован
`execution_policy_kernel.py` читает пороги из `policy_registry.RUNTIME`.
Порядок строгий: DENY → HEAVY → DEGRADE → ALLOW. Нет случайности.

### 1.2 ✅ `_classify_complexity()` — исправлен (май 2026)
~~Четыре пробела = HIGH. Любой `{}` = HIGH. Шумовой классификатор.~~

**Закрыто:** переписан в `update_handler.py`:
- Code detection: только fenced blocks (` ``` `), не отступы
- JSON detection: `{` + `}` + `:` — требует key:value паттерн
- Length threshold повышен до 800 chars (было 500)
- Результат логируется: `complexity`, `length`, `has_code`, `has_json`

### 1.3 ✅ `_build_messages()` — hardcoded `Tier.GENERAL` исправлен (май 2026)
~~`select_strategy(intent, Tier.GENERAL)` для всех путей включая FAST.~~

**Закрыто:** `_build_messages()` принимает реальный `tier` как параметр.
FAST-запросы получают lightweight `instruction_prefix`, HEAVY — тяжёлый.
Фиксирует audit §1.3 и §6.3 одновременно.

### 1.4 ✅ MATH self-correction — bounded
Максимум 1 correction pass. Сработает только при `Intent.MATH`. Детерминировано.

---

## 2. GOVERNANCE THEATER

### 2.1 ✅ Safety Gate — docs/runtime gap закрыт (май 2026)
~~architecture.md говорил DENY, runtime всегда возвращал PASS.~~

**Закрыто:** `architecture.md §21` и `§27` обновлены — Safety Gate официально
задокументирован как **observability-only layer (non-blocking)**. Обоснование:
prompt-guard модели дают неприемлемый false-positive rate на русском/арабском/коротком
тексте. Единственный blocking authority — `safety_agent` (post-reasoning, §21).
`safety_gate.py` содержит полное обоснование в docstring.

### 2.2 ✅ `analysis.py` — реализован (май 2026)
~~Объявлен как pre-reasoning DAG step, нигде не вызывается. Мёртвый модуль.~~

**Закрыто:** подключён через Вариант А (строго по архитектуре §4):
```
update_handler.py → analyse(text) [после Pass 2, до orchestrator]
→ AnalysisReport → OrchestratorRequest.analysis_report
→ orchestrator.run() → intent_engine.classify(analysis_hints=...)
```
В `intent_engine.classify()`:
- `HAS_MATH` confidence ≥ 0.80 → немедленный return MATH (пропускает LLM pre-check)
- `IS_SHORT` или `IS_MULTILINGUAL` → повышает effective_min до max(текущий, 0.72)
- `HAS_CODE_BLOCK` → снижает effective_min до min(текущий, 0.50)

### 2.3 ✅ `decision_matrix.py` — читает из `policy_registry` (май 2026)
~~Пороги hardcoded `0.0005` / `0.003`. При изменении EPK — рассинхронизация молча.~~

**Закрыто:** `decision_matrix.py` импортирует `RUNTIME` из `policy_registry`:
```python
from core.kernel.policy_registry import RUNTIME
_FAST_CEILING    = RUNTIME.epk.fast_ceiling        # 0.0005
_GENERAL_CEILING = RUNTIME.epk.degrade_threshold   # 0.003
```
Теперь изменение порога в `policy_registry.py` автоматически подхватывается.

---

## 3. ORCHESTRATION CENTRALIZATION

### 3.1 ✅ EPK — единственный policy authority
Оркестратор не создаёт policy, не выбирает модели напрямую. Чистая реализация.

### 3.2 ✅ Coordinator вызывается только из orchestrator
`multi_agent_coordinator.coordinate()` — один call site. Нет скрытых вызовов.

### 3.3 ✅ `update_handler.py` — web search authority перенесена в orchestrator (май 2026)
~~Двойной intent classification. `forced_intent` / `_already_grounded` coupling.~~

**Закрыто:** web search routing logic (`_NO_SEARCH_INTENTS`) перенесена из transport слоя
в `core/execution/orchestrator.py`. Web search вызывается внутри `orchestrator.run()`,
после `classify()`, до EPK — authority однозначна.
`update_handler` не выполняет intent classification и не вызывает web search.
`forced_intent` / `_already_grounded` coupling устранён: `OrchestratorRequest` использует
`vision_intent` (typed `IntentResult | None`) вместо неявных флагов.

Что остаётся в `update_handler` (Safety Gate, multilingual, analysis, history, retrieval) —
это корректный pre-processing pipeline строго по architecture.md §4 execution lifecycle.
Retrieval передаётся как `retrieved_context` в `OrchestratorRequest` — это параметр,
не coupling. Вынос в отдельный pre-processor слой не даёт архитектурной выгоды.

Верифицировано: `tests/test_orchestrator_web_search.py`.

### 3.4 ✅ `fallback_handler.py` — billing по actual_tier исправлен (май 2026)
~~Cascade HEAVY → GENERAL → FAST: billing шёл по изначальному tier, не фактическому.~~

**Закрыто:** `coordination.actual_tier` передаётся из `fallback_handler` в
`CoordinationResult`. Все три пути (`_run_allow`, `_run_degraded`, `_run_heavy`)
используют `_billing_tier = coordination.actual_tier or tier` для billing.

---

## 4. EMERGENT COMPLEXITY

### 4.1 ✅ MATH correction loop — bounded
Max 1 correction pass. Нет рекурсии.

### 4.2 ✅ Consensus — mutex с HEAVY
`use_consensus=False` при `Tier.HEAVY`. Mutex соблюдён.

### 4.3 ✅ Bias-free candidate selection для safety_agent + observability fallback (май 2026)
~~`best_candidate = max(candidates, key=lambda r: len(r.text))` — выбор по длине.~~

**Закрыто (два фикса):**

**Фикс 1 — `cognition/multi_agent_coordinator.py`:**
`best_candidate` заменён на `safety_candidate = candidates[0]` — первый выживший
кандидат по позиции. `candidates` строится как `[primary_result, *validator_results]`,
поэтому primary всегда первый если он выжил. Если primary упал — он отсутствует
в candidates, следующий по позиции принимается без bias по длине.
Позиционный выбор детерминирован, не смещён, не делегирует доверие router.
`actual_tier` в `CoordinationResult` обновлён на `candidates[0].actual_tier`.

**Фикс 2 — `agents/consensus_engine.py`:**
Fallback по длине (аварийный путь при падении gpt-oss-120b) сохранён как честная
эвристика, но перестал быть silent downgrade:
- `increment("consensus.arbitration_failed")` — счётчик в metrics
- `logger.warning(...)` вместо `logger.info(...)` — мониторинг видит деградацию
Sustained arbitration outages теперь обнаруживаются через `/metrics`.

---

## 5. RETRIEVAL INSTABILITY

### 5.1 ✅ pgvector bug fix — исправлен
`candidates` больше не всегда пустой. `similarity_search()` реально вызывается.

### 5.2 ✅ `rerank_tokens` — реальная оценка (май 2026)
~~`rerank_tokens = len(retrieval_result.documents) * 10`~~
~~Константа 10 не связана с реальной длиной документов.~~

**Закрыто:** `retrieval_engine.py` считает реальные символы cross-encoder пар:
```python
_query_tokens    = max(1, len(clean_query) // 4)
_avg_doc_tokens  = max(1, sum(len(t) for t in _candidate_texts) // (4 * len(_candidate_texts)))
rerank_tokens    = (_query_tokens + _avg_doc_tokens) * len(candidates)
```
1 token ≈ 4 chars (conservative для mixed-language текста).
Соответствует billing unit economic.md §1.5: per 1M token-pairs.

### 5.3 ✅ `source_credibility.score_documents()` — активирован (май 2026)
~~SerpAPI результаты фильтруются активно. pgvector результаты — нет.~~
~~Асимметрия задокументирована в architecture.md §20 как "reserved".~~

**Закрыто:**
- Supabase: `ALTER TABLE memory ADD COLUMN source_url text DEFAULT NULL`
- `MemoryRecord` получил поле `source_url: str | None = None`
- `fetch_by_user()` и `similarity_search()` маппят `source_url` из БД
- `score_documents()` в `retrieval_engine.py` активен — pass-through устранён

### 5.4 ✅ Retrieval при недоступном Redis — исправлен (май 2026)
~~При `redis is None` → retrieval полностью пропускался молча.~~

**Закрыто:** retrieval теперь гейтируется только на `supabase is not None`.
Redis — опциональный кэш. При `redis is None` retrieval продолжается без кэша
(degraded mode), логируется WARNING. При `supabase is None` — пропускается с явным
WARNING (pgvector требует Supabase).

---

## 6. TIER INFLATION

### 6.1 ✅ EPK estimate tier — adaptive (май 2026)
~~EPK всегда оценивал по `Tier.GENERAL` → ~10x завышение для коротких запросов.~~

**Закрыто:** adaptive `_estimate_tier` в `orchestrator.run()`:
```python
_estimate_tier = (
    Tier.FAST
    if request.complexity == Complexity.LOW and request.input_tokens < 300
    else Tier.GENERAL
)
```
Короткие LOW-complexity запросы оцениваются по FAST rates. Снижает ложные
DEGRADED_MODE для обычного чата.

### 6.2 ✅ decision_matrix — ascending order исправлен
`0.0005 < 0.003` — корректно. Прежний баг (GENERAL unreachable) устранён.

### 6.3 ✅ `_build_messages()` — tier mismatch исправлен (май 2026)
~~FAST-запросы получали GENERAL `instruction_prefix`. Модель 8B получала инструкции для 70B.~~

**Закрыто:** см. §1.3 — `_build_messages()` принимает реальный tier.

---

## 7. FAKE BOUNDED CONTEXTS

### 7.1 ✅ `UsageEntry` — все поля заполняются (май 2026)
~~`intent`, `audio_seconds`, `tts_characters` никогда не передавались в `UsageEntry`.~~

**Закрыто:** `webhook.py` передаёт:
```python
await meter.record(UsageEntry(
    ...
    intent=result.intent,           # ✅
    audio_seconds=result.audio_seconds,     # ✅
    tts_characters=result.tts_characters,   # ✅
))
```
`OrchestratorResult` объявляет `audio_seconds` и `tts_characters` как поля,
заполняемые `update_handler` после TTS synthesis.

### 7.2 ✅ `OrchestratorResult` — speech fields добавлены (май 2026)
~~TTS char_count логировался, но не доходил до billing pipeline.~~

**Закрыто:** `OrchestratorResult` объявляет:
```python
audio_seconds: float = 0.0
tts_characters: int = 0
```
`update_handler` заполняет их после TTS synthesis через `dataclasses.replace()`.
`webhook.py` читает и передаёт в `UsageEntry`.
📋 Speech billing columns в Supabase: добавлены через `migrate_usage_log.sql` (май 2026).
`usage_meter.py` имеет PGRST204 fallback на период до выполнения миграции.

### 7.3 ✅ `observability/metrics.py` — `/metrics` endpoint добавлен (май 2026)
~~`snapshot()` доступен, но не подключён к внешнему sink.~~

**Закрыто:** `GET /metrics` добавлен в `app/main.py` — возвращает JSON snapshot.
Мёртвый импорт `snapshot as metrics_snapshot` удалён из `webhook.py`.
Явный контракт зафиксирован в `metrics.py` и `architecture.md §27`:
Metrics are in-memory, per-process, reset on restart. No persistence layer by design.
`increment()` и `gauge()` — pure in-memory, без side effects.
Prometheus/StatsD — отдельная задача, external adapter, без изменений `metrics.py`.

---

## 8. RUNTIME/DOCS DIVERGENCE

### 8.1 ✅ Safety Gate: docs/runtime gap закрыт (май 2026)
~~architecture.md §21 говорил DENY, runtime всегда возвращал PASS.~~

**Закрыто:** см. §2.1. `architecture.md §21` и `§27` обновлены.
Non-blocking observability layer задокументирован с полным обоснованием.

### 8.2 ✅ `architecture.md §4` lifecycle — обновлён (май 2026)
~~Pass 1 и Pass 2 показаны вместе. Multilingual после обоих. History/Retrieval/Web Search не упомянуты.~~

**Закрыто:** `§4` переписан — полный explicit lifecycle с обоснованием порядка
(Вариант А: Multilingual между Pass 1 и Pass 2):
```
Pass 1 → Feature Extraction → Multilingual → Pass 2
→ History → Retrieval → Web Search → EPK → ... → History Save → META → TTS → Output
```
Добавлен подраздел с обоснованием: Pass 2 (gpt-oss-safeguard-20b) работает точнее
на нормализованном тексте → Multilingual перед Pass 2 снижает false-positive rate.

### 8.3 ✅ `analysis.py` — gap закрыт (май 2026)
~~models1.md §11: "automatic" — механизм не документирован, вызова нет.~~

**Закрыто:** см. §2.2. Явный вызов в `update_handler.py`, `architecture.md §4` и `§27` обновлены.

---

## 9. HIDDEN AUTHORITY PATHS

### 9.1 ✅ `fallback_handler` — billing по actual_tier (май 2026)
~~Cascade HEAVY → GENERAL → FAST: пользователь мог получить FAST-качество при HEAVY-billing.~~

**Закрыто:** см. §3.4. `actual_tier` из `CoordinationResult` используется для billing
во всех трёх execution paths.

### 9.2 ✅ Web search — balance guard добавлен (май 2026)
~~Web search запускался до EPK. SerpAPI вызывался даже для zero-balance пользователей.~~

**Закрыто:** balance guard в `update_handler.py` перед web search:
```python
if user_balance <= 0:
    logger.info("Web search skipped — zero balance (pre-EPK guard)")
else:
    web_result = await run_tool(...)
```
EPK по-прежнему не знает о pre-search (полное устранение требует выноса в pre-processor),
но zero-balance пользователи больше не расходуют SerpAPI quota.

### 9.3 ✅ Vision fast-path — balance guard добавлен (май 2026)
~~Vision fast-path: hardcoded cost `0.001`, EPK не вызывался, zero-balance пользователи получали ответ.~~

**Закрыто:** balance guard перед vision fast-path response:
```python
_vision_cost_usd = 0.001
if user_balance <= 0 or _vision_cost_usd > user_balance:
    return OrchestratorResult(..., denied=True, deny_reason="insufficient_balance")
```
EPK authority сохранён: проверка структурно идентична EPK rule #1.

---

## 10. OBSERVABILITY COLLAPSE

### 10.1 ✅ `metrics.py` — `/metrics` endpoint добавлен (май 2026)
~~Нет внешнего экспорта. `snapshot()` API готов. Нужен sink + scrape endpoint.~~

**Закрыто:** см. §7.3. `GET /metrics` в `app/main.py` — JSON snapshot.
Prometheus/StatsD: отдельная будущая задача, не требует изменений `metrics.py`.

### 10.2 ✅ `tracing.py` — structured JSON spans + trace_id propagation (май 2026)
~~`elapsed_ms` в stdout. Нет structured span export.~~

**Закрыто:** `observability/tracing.py` переписан — log-based distributed tracing:
- `trace_id` генерируется на корневом span, наследуется вложенными через `contextvars`
- `span_id` уникален на каждый span, `parent_id` фиксирует вложенность
- Span эмитируется как structured JSON в `extra["span_json"]` — читается `fly logs`
  и любым JSON-aware log aggregator (Grafana Loki, Datadog)
- `status: ok | error` — span помечается при исключении автоматически
- `current_trace_id()` — публичный API для корреляции из других модулей
- Интерфейс `with trace(name, **tags)` не изменился — `webhook.py` и `orchestrator.py`
  не тронуты

`opentelemetry-api` и `opentelemetry-sdk` удалены из `pyproject.toml` —
были мёртвыми зависимостями (задекларированы, нигде не импортировались).

**OTLP migration path:** заменить backend реализации `tracing.py` —
все call sites остаются без изменений. Collector не нужен до появления
Jaeger / Grafana Tempo / Honeycomb в инфраструктуре.

### 10.3 ✅ Safety Gate signals — разделены по типу (май 2026)
~~UNSAFE сигнал мог быть потерян молча при API ошибке.~~

**Закрыто:** в `_classify_with_model()` два типа событий разделены:
- API error → `"Safety Gate signal lost"` + `event: "safety_signal_lost"` (ERROR)
- UNSAFE verdict → `"Safety Gate Pass 2: UNSAFE signal detected"` (WARNING)
Разные severity и event keys позволяют мониторингу различать их.

### 10.4 ✅ `request_id` — сквозная корреляция реализована (май 2026)
~~Нет `request_id` через pipeline. Логи невозможно связать без ручной корреляции по времени.~~

**Закрыто:** `webhook.py` генерирует `request_id = "{update_id}:{user_id}"`.
Передаётся через `handle_message()` → `OrchestratorRequest.request_id` →
логируется в orchestrator, coordinator. Все pipeline стадии теперь корреляционно связаны.

---

## 11. CI / TEST SUITE

### 11.1 ✅ `.github/workflows/ci.yml` — существует
`project-root/.github/workflows/ci.yml`: Python 3.12, pip cache, import checks, ruff, pytest.
Корректно настроен для push на main и pull_request.

### 11.2 ✅ Test suite — создан (май 2026)
~~`pytest` запускался без тестовых файлов → CI падал.~~

**Закрыто:** `project-root/tests/` создан, покрывает все обязательные области:
- `test_epk.py` — `policy_registry`, `execution_policy_kernel`, `decision_matrix`, `cost_model` (Sealed layer)
- `test_safety_gate.py` — оба прохода non-blocking, API errors не блокируют, UNSAFE → WARNING не DENY
- `test_analysis.py` — публичный API, lightweight/full режимы, never raises
- `test_usage_meter.py` — normal record, extended fields, PGRST204 fallback, double-failure path
- `test_intent_engine_hints.py` — analysis_hints integration: HAS_MATH fast-path, effective_min adjustments
- `test_orchestrator_web_search.py` — §3.3 верификация: `_NO_SEARCH_INTENTS` в orchestrator, не в transport
- `conftest.py` — shared fixtures, asyncio marker
Все тесты pure unit — no Supabase, Redis, Groq, HuggingFace. Внешний I/O замокан на границе.

### 11.3 ✅ `fly.toml` — обновлён до production machine spec (май 2026)
~~`fly.toml` содержал `memory = '2gb'`, `cpu_kind = 'shared'` — не соответствовало
фактической машине. При следующем `fly deploy` машина откатилась бы на 2GB.~~

**Закрыто:** `fly.toml` обновлён:
```toml
[[vm]]
  memory = '8gb'
  cpu_kind = 'performance'
  cpus = 1
```
Причина апгрейда: `healthcheck.py` (`full_health()`) выполняет Redis ping +
Supabase query при каждом `/health` запросе (interval=30s). На 2GB shared CPU
под нагрузкой healthcheck мог не укладываться в timeout=5s → машина перезапускалась.
8GB performance-cpu-1x устраняет эту проблему.

---

## 12. UNIFIED AGENTIC PATH

### 12.1 ✅ Tool-only bypass path удалён (май 2026)

**Решение:** все пять data-driven интентов (SEARCH, WEATHER, MAPS, MAPS_POI, MAPS_ROUTE)
теперь идут через compound_agent без исключений.

**Изменения:**
- `orchestrator.py`: `_TOOL_INTENTS` удалён, `_AGENTIC_INTENTS` задекларирован (все 5).
  Tool-only bypass (WEATHER/MAPS/MAPS_ROUTE → форматтер → выход) удалён.
- `compound_agent.py`: добавлен `get_route` tool schema + `_execute_tool()` handler.
  Теперь compound вызывает `MapsService.get_route()` напрямую.
- `multi_agent_coordinator.py`: комментарий обновлён — unified agentic path задокументирован.
- Supported tools: `web_search`, `get_weather`, `geocode`, **`get_route`**.

**Обоснование:**
Детерминированные форматтеры (format_current, format_geocode, format_route) производят
структурированный текст — и это правильно. Но доставка этого текста напрямую пользователю,
минуя LLM reasoning, означает что бот не может:
- интерпретировать данные в контексте вопроса ("стоит ли ехать в горы?")
- верифицировать полноту и корректность retrieved data
- корректно обработать частичные результаты или failure
- добавить nuance ("ветер 15 м/с — это сильный ветер для пляжа")

Compound получает форматированный результат как tool output, и делает reasoning над ним
перед ответом пользователю. Форматтеры остаются в `compound_agent._execute_tool()` —
они не исчезли, они стали input для reasoning, а не финальным output.

### 12.2 ✅ STRICT truth gate — agentic интенты исключены (май 2026)

**Проблема:** `_STRICT_INTENTS` в orchestrator содержал все пять agentic интентов.
STRICT gate проверяет `has_grounding = bool(tool_output) or bool(retrieved_context)`
ДО того, как compound_agent успевает выполниться. При `tool_output=None` (legacy `_run_tool`
больше не вызывается для agentic интентов) → gate блокировал бы все запросы на погоду,
маршруты и поиск с `no_grounded_data`.

**Решение:**
- `_STRICT_INTENTS` в orchestrator → пустое множество (`set()`). Задокументировано
  как placeholder для будущих non-agentic STRICT интентов (AVAILABILITY, SCHEDULE).
- `_run_tool()` вызывается только для `intent not in _AGENTIC_INTENTS` — agentic
  интенты полностью исключены из legacy tool path.
- `TruthMode.STRICT` остаётся в `context/assembler.py` для всех пяти интентов —
  это LLM-инструкция "не выдумывай", она доходит до compound через `_build_messages()`.
  Это правильно и не меняется.
- `assembler.py` получил явный комментарий: STRICT здесь = LLM policy, не pre-execution gate.

**Инвариант:** grounding для agentic интентов обеспечивает compound_agent изнутри.
Orchestrator gate не может и не должен это проверять — compound ещё не запустился.

| # | Категория | Статус |
|---|---|---|
| 1.1 | EPK детерминизм | ✅ |
| 1.2 | `_classify_complexity` шум | ✅ Закрыто май 2026 |
| 1.3 | `_build_messages` tier mismatch | ✅ Закрыто май 2026 |
| 1.4 | MATH correction bounded | ✅ |
| 2.1 | Safety Gate docs/runtime gap | ✅ Закрыто май 2026 |
| 2.2 | `analysis.py` не вызывался | ✅ Закрыто май 2026 |
| 2.3 | `decision_matrix` hardcoded пороги | ✅ Закрыто май 2026 |
| 3.1 | EPK единственный policy authority | ✅ |
| 3.2 | Coordinator — один call site | ✅ |
| **NEW** | **Unified agentic path для всех tool intents** | **✅ Закрыто май 2026** |
| **NEW** | **STRICT gate — agentic интенты исключены** | **✅ Закрыто май 2026** |
| 3.3 | web search authority → orchestrator, coupling устранён | ✅ Закрыто май 2026 |
| 3.4 | fallback billing по actual_tier | ✅ Закрыто май 2026 |
| 4.1 | MATH correction bounded | ✅ |
| 4.2 | Consensus mutex с HEAVY | ✅ |
| 4.3 | bias-free safety selection + fallback observability | ✅ Закрыто май 2026 |
| 5.1 | pgvector bug fix | ✅ |
| 5.2 | rerank_tokens реальная оценка | ✅ Закрыто май 2026 |
| 5.3 | source_credibility активирован + source_url в MemoryRecord | ✅ Закрыто май 2026 |
| 5.4 | Retrieval при недоступном Redis | ✅ Закрыто май 2026 |
| 6.1 | EPK estimate всегда GENERAL | ✅ Закрыто май 2026 |
| 6.2 | decision_matrix ascending order | ✅ |
| 6.3 | `_build_messages` GENERAL для FAST | ✅ Закрыто май 2026 |
| 7.1 | UsageEntry поля не заполнялись | ✅ Закрыто май 2026 |
| 7.2 | OrchestratorResult без speech fields | ✅ Закрыто май 2026 |
| 7.3 | metrics.py — `/metrics` endpoint | ✅ Закрыто май 2026 |
| 8.1 | Safety Gate docs/runtime | ✅ Закрыто май 2026 |
| 8.2 | architecture.md §4 lifecycle | ✅ Закрыто май 2026 |
| 8.3 | analysis.py "automatic" | ✅ Закрыто май 2026 |
| 9.1 | fallback billing overbilling | ✅ Закрыто май 2026 |
| 9.2 | web search до EPK | ✅ Balance guard май 2026 |
| 9.3 | vision fast-path bypass EPK | ✅ Balance guard май 2026 |
| 10.1 | metrics.py — `/metrics` endpoint | ✅ Закрыто май 2026 |
| 10.2 | structured JSON spans + trace_id propagation | ✅ Закрыто май 2026 |
| 10.3 | Safety Gate signals потеря | ✅ Закрыто май 2026 |
| 10.4 | Нет request_id корреляции | ✅ Закрыто май 2026 |
| 11.1 | ci.yml существует | ✅ |
| 11.2 | Test suite создан | ✅ Закрыто май 2026 |
| 11.3 | fly.toml machine spec | ✅ Закрыто май 2026 |
| 12.1 | tool_calls billing gap | ✅ Закрыто май 2026 |
| 12.2 | Execution ownership conflict SEARCH/MAPS_POI | ✅ Закрыто май 2026 |

### Открытые пункты по приоритету

Все зафиксированные пункты закрыты. Новых открытых пунктов нет.

---

## 12. COMPOUND AGENT — BILLING & OWNERSHIP (май 2026)

### 12.1 ✅ tool_calls billing gap — закрыт (май 2026)
~~tool_calls: int объявлен в UsageEntry и Supabase, но в webhook.py не передавался.
compound web_search вызовы не биллились. Revenue leak.~~

**Закрыто:** chain замкнут без разрывов:
```
compound_agent._run_compound() — total_tool_calls += len(result.tool_calls) за каждый round
→ AgentResult.tool_calls: int
→ CoordinationResult.tool_calls: int (coordinator агрегирует из primary/fallback/consensus)
→ OrchestratorResult.tool_calls: int (_run_allow, _run_degraded, _run_heavy — все три пути)
→ webhook.py: meter.record(UsageEntry(..., tool_calls=result.tool_calls))
→ Supabase usage_log.tool_calls
```
UsageEntry.tool_calls и Supabase колонка уже были объявлены — миграции не требуется.

### 12.2 ✅ Execution ownership conflict — закрыт (май 2026)
~~SEARCH и MAPS_POI: два параллельных пути к одному результату.
Оркестратор перехватывал их в tool-only / _structured_search path раньше compound.
compound_agent был недостижим для этих интентов. plan_agents() → coordinator
→ compound_agent никогда не вызывался для SEARCH/MAPS_POI.~~

**Закрыто:** Execution ownership разделён чётко:

**_TOOL_INTENTS (WEATHER, MAPS, MAPS_ROUTE) → оркестратор → детерминированные форматтеры.**
format_current / format_geocode / format_route уже возвращают финальный текст.
LLM там не нужен. tool-only path корректен и намерен для этих интентов.

**SEARCH, MAPS_POI → compound_agent через agentic path (plan_agents → coordinator).**
SEARCH: compound сам решает что искать и как синтезировать результаты.
MAPS_POI: compound reasoning нужен для релевантности и представления.
_structured_search path удалён из оркестратора — больше не нужен.
_NO_SEARCH_INTENTS включает "search" и "maps_poi" — pre-EPK web search не запускается
для этих интентов (compound сам владеет tool execution).

**STRICT truth gate сохранён в оркестраторе как policy (§2.1).**
Compound не видит STRICT gate — это EPK-level policy, не agent-level logic.
Если compound не нашёл grounding data — возвращает AgentResult(success=False) →
coordinator пробует fallback → оркестратор может вернуть no_grounded_data через
STRICT truth gate если has_grounding=False после всего pipeline.
---

## 13. OBSERVED BUGS — тестирование май 2026

Зафиксированы по скриншотам живых сессий. Статус: **OPEN**, подлежат исправлению.

---

### 13.1 🔴 OPEN — Все tool intents → «сервис временно недоступен»

**Наблюдение:**
Поиск отелей, маршруты из аэропорта, погода в Сан-Франциско, погода в Молдове —
все запросы с tool execution возвращают одно и то же:
> 🔍 Не удалось получить актуальную информацию прямо сейчас — сервис поиска временно недоступен.

**Причина (предположительная):**
compound_agent пытается вызвать `web_search` / `get_weather` / `get_route`, но tool execution
падает — API ключ, недоступность Groq compound endpoint (beta/waitlist), таймаут.
Fallback в coordinator → AgentType.DEEP без tool context → synthesizer отдаёт i18n строку
`search_unavailable`.

Дополнительный риск: после наших изменений (unified agentic path, май 2026) WEATHER/MAPS/MAPS_ROUTE
тоже переведены на compound. Если compound endpoint недоступен — **весь** tool-traffic падает.
Раньше WEATHER/MAPS работали через детерминированные форматтеры независимо от compound.

**Что проверить:**
- Доступность `groq/compound` и `groq/compound-mini` через Groq API
- Ключи SerpAPI / OpenWeatherMap / Mapbox в `app/settings.py`
- Логи `compound_agent._run_compound()` — на каком tool call round падает
- `fallback_handler.py` — что происходит при AgentResult(success=False)

**Влияние:** критическое. Все data-driven интенты отдают error вместо ответа.

---

### 13.2 🔴 OPEN — Потеря контекста разговора

**Наблюдение:**
- «Вот, нашла» → бот переводит фразу как idiomatic expression вместо понимания контекста
- «Походу да» → бот переводит вместо интерпретации как согласия
- Поиск аниме: после 3+ уточнений бот снова просит описать сюжет

**Причина (code-level):**
`_MAX_HISTORY_TOKENS = 1200` в `conversation_history.py` — агрессивный обрезатель.
System prompt для tool/STRICT интентов весит ~1300-1800 токенов (задокументировано там же).
После trim history сокращается до 0-2 реплик. Compound получает почти пустую историю.

Отдельно: `_llm_pre_classify(text)` в `intent_engine.py` получает только текущее сообщение
без истории. Короткий follow-up «Вот, нашла» → pre-classifier не понимает контекст →
не может вернуть правильный intent.

**Влияние:** серьёзное. Бот воспринимается как «без памяти» уже через 2-3 хода.

---

### 13.3 🟡 OPEN — Reasoning chain-of-thought утекает в финальный ответ

**Наблюдение:**
Ответы содержат внутренний reasoning format:
```
Constraints: 1. ... 2. ...
Candidates: - ...
Verification: - ...
Verification table: Поле | Значение
```

**Причина:**
`reasoning_engine.py` `instruction_prefix` для MATH/ANALYSIS требует «list ALL constraints»,
«show verification table». `response_synthesizer.py` не фильтрует CoT структуру.

Для vision запросов: `vision_handler` передаёт extracted text в pipeline →
classifier видит структурированный текст → классифицирует как MATH/ANALYSIS →
reasoning format применяется и весь CoT попадает в ответ пользователю.

**Влияние:** ответы выглядят как отладочный вывод, не как ответ ассистента.

---

### 13.4 🟡 OPEN — Classifier теряет контекст на follow-up сообщениях

**Наблюдение:**
«Вот, нашла» / «Туговатый у тебя поиск)» / «Реально поисковик сдох)» после диалога →
classifier видит изолированную фразу → CONVERSATION → бот отвечает не по контексту.

**Причина:**
`_llm_pre_classify(text)` получает только `text[:500]` без истории.
`classify()` принимает `conversation_history` параметр, но в pre-classifier он не передаётся.
Embedding classifier тоже работает на изолированном тексте.

**Решение-кандидат:**
Передавать последние 2-3 реплики из `conversation_history` в `_llm_pre_classify` как контекст.
«[Предыдущий контекст: ...]\n\nТекущее сообщение: {text}»

**Влияние:** серьёзное для conversational UX. Любой follow-up теряет контекст.

---

### 13.5 🟡 OPEN — SEARCH не оптимизирует запрос для поиска

**Наблюдение:**
Описательный поиск аниме («глава якудзы подставляет к своей дочери охранника, умерли родители») →
3 попытки, не находит «Ojou to Banken-kun». Когда пользователь сам называет — бот сразу находит.

**Причина:**
compound_agent передаёт user message как query в `web_search` без переформулирования.
Русскоязычный описательный запрос → SerpAPI → нерелевантные результаты.
`_MAX_TOOL_ROUNDS = 3` — три попытки, но запрос почти не меняется.

**Решение-кандидат:**
В SEARCH system prompt явно инструктировать compound:
«Переформулируй описание в оптимальный поисковый запрос на английском языке, используй ключевые слова».

**Влияние:** умеренное. Поиск по описанию — частый и ожидаемый сценарий.

---

### 13.6 🟢 ПРОВЕРЕНО — 25 000 × 40 000 = 1 000 000 000 (не баг)

Бот ответил 1 000 000 000. Это математически верно: 25 × 10³ × 40 × 10³ = 1000 × 10⁶ = 10⁹.
CoT format в ответе — проблема 13.3, не математическая ошибка.

---

### 13.7 🟢 НИЗКИЙ — Грузинский: fallback-строка некорректна по смыслу

**Наблюдение:**
«რა ამინდია ამ წუთას მოლდოვაში?» → «სანდო ინფორმაცია ვერ მოიძება. გთხოვთ დააზუსტოთ კითხვა.»
(«Уточните вопрос» — хотя вопрос чёткий).

**Причина:**
Та же, что 13.1 (compound failure). Плюс: i18n строка `search_unavailable` для `ka`
формулирует отказ как «запрос неясен», а не «технический сбой».

**Влияние:** низкое, но создаёт неверное впечатление.

---

### СВОДНАЯ ТАБЛИЦА ОТКРЫТЫХ БАГОВ

| # | Приоритет | Описание | Файлы |
|---|---|---|---|
| 13.1 | 🔴 КРИТИЧЕСКИЙ | Все tool intents → «сервис недоступен» | compound_agent, groq_client, settings |
| 13.2 | 🔴 СЕРЬЁЗНЫЙ | Потеря контекста (history trim слишком агрессивна + pre-classifier без истории) | conversation_history, intent_engine |
| 13.3 | 🟡 СРЕДНИЙ | CoT reasoning format в финальном ответе | response_synthesizer, reasoning_engine, vision_handler |
| 13.4 | 🟡 СРЕДНИЙ | Classifier теряет контекст на follow-up фразах | intent_engine._llm_pre_classify |
| 13.5 | 🟡 СРЕДНИЙ | SEARCH не переформулирует описательный запрос | compound_agent, SEARCH system prompt |
| 13.7 | 🟢 НИЗКИЙ | Грузинский: i18n fallback-строка некорректна по смыслу | i18n/strings.py |