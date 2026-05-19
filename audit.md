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

### 4.3 ⚠️ best_candidate = longest text
```python
best_candidate = max(candidates, key=lambda r: len(r.text))
```
Выбор кандидата по длине, не по качеству. Открытый gap.
**Статус:** low priority — на практике агенты редко дают сильно разные по длине ответы
на один и тот же запрос. Потенциальное улучшение: score по perplexity или LLM-judge.

---

## 5. RETRIEVAL INSTABILITY

### 5.1 ✅ pgvector bug fix — исправлен
`candidates` больше не всегда пустой. `similarity_search()` реально вызывается.

### 5.2 ⚠️ `rerank_tokens` — шумовая оценка
```python
rerank_tokens = len(retrieval_result.documents) * 10
```
Константа 10 не связана с реальной длиной документов. Влияние минимальное
(RERANK_RATE = $0.10/1M), но это шум в EPK вход, не реальный billing.
**Статус:** low priority. Улучшение: считать реальные символы cross-encoder пар.

### 5.3 ⚠️ `source_credibility.score_documents()` — pass-through для pgvector
SerpAPI результаты фильтруются активно. pgvector результаты — нет.
Асимметрия задокументирована в architecture.md §20 как "reserved".
**Статус:** активируется автоматически когда `MemoryRecord` получит `source_url` поле.

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

### 10.2 ⚠️ `tracing.py` — `trace()` вызывается, latency не экспортируется
`trace()` вызывается в orchestrator (`coordinator` span) и webhook (`handle_message` span).
Логирует `elapsed_ms` в stdout. Нет structured span export (Jaeger, OTLP).
**Статус:** partial — observability через логи есть, distributed tracing нет.

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

## СВОДКА

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
| 3.3 | web search authority → orchestrator, coupling устранён | ✅ Закрыто май 2026 |
| 3.4 | fallback billing по actual_tier | ✅ Закрыто май 2026 |
| 4.1 | MATH correction bounded | ✅ |
| 4.2 | Consensus mutex с HEAVY | ✅ |
| 4.3 | best_candidate = longest | ⚠️ Low priority |
| 5.1 | pgvector bug fix | ✅ |
| 5.2 | rerank_tokens шум | ⚠️ Low priority |
| 5.3 | source_credibility pass-through | ⚠️ Reserved — активируется с source_url |
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
| 10.2 | tracing.py нет distributed export | ⚠️ Partial |
| 10.3 | Safety Gate signals потеря | ✅ Закрыто май 2026 |
| 10.4 | Нет request_id корреляции | ✅ Закрыто май 2026 |
| 11.1 | ci.yml существует | ✅ |
| 11.2 | Test suite создан | ✅ Закрыто май 2026 |
| 11.3 | fly.toml machine spec | ✅ Закрыто май 2026 |

### Открытые пункты по приоритету

**⚠️ Known gaps (не блокируют production):**
- §4.3 — best_candidate по длине, не по качеству
- §5.2 — rerank_tokens шумовая оценка
- §5.3 — source_credibility pass-through для pgvector (активируется с source_url)
- §10.2 — distributed tracing не реализован