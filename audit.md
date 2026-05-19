# CEYONA — ARCHITECTURE AUDIT
**Дата:** май 2026  
**Проверено:** architecture.md v8.0, models1.md v7.1, economic.md v5.1 + весь runtime код  
**Статус:** 10 категорий × верификация кода

---

## 1. HIDDEN NONDETERMINISM

### 1.1 ✅ EPK — детерминирован
`execution_policy_kernel.py` читает пороги из `policy_registry.RUNTIME`. Порядок строгий: DENY → HEAVY → DEGRADE → ALLOW. Нет случайности.

### 1.2 ⚠️ `_classify_complexity()` в `update_handler.py` — упрощённая эвристика
```python
def _classify_complexity(text: str) -> Complexity:
    has_code = "```" in text or "    " in text
    has_json = "{" in text and "}" in text
```
Четыре пробела в начале строки = `Complexity.HIGH`. Любой текст с `{}` = HIGH. Это не feature extraction — это шумовой классификатор. Результат влияет на `estimate_output_tokens()` → EPK вход. Нет логирования того, что именно сработало.

### 1.3 ⚠️ `_build_messages()` в `orchestrator.py` использует `Tier.GENERAL` принудительно
```python
def _build_messages(...):
    strategy = select_strategy(intent_result.intent, Tier.GENERAL)  # ← hardcoded
```
Вызывается для всех трёх путей (ALLOW / HEAVY / DEGRADED). Для FAST-запроса формируется промпт с `instruction_prefix` стратегии GENERAL. Для HEAVY — тоже GENERAL. Фактический tier, переданный в агент, не влияет на сборку промпта. Скрытый недетерминизм: промпт может включать тяжёлый prefix для лёгкого запроса и наоборот.

### 1.4 ✅ MATH self-correction — bounded
Максимум 1 correction pass. Сработает только при `Intent.MATH`. Детерминировано.

---

## 2. GOVERNANCE THEATER

### 2.1 🔴 Safety Gate — полностью отключён, архитектура говорит обратное
`architecture.md §21`: *"deterministic, unavailability → DENY"*  
`models1.md §1`: *"Unavailability rule: Safety model unavailable → DENY by default. NO fallback to ALLOW."*

Фактический код:
```python
async def check_pass1(text: str) -> GateResult:
    logger.debug("Safety Gate Pass 1: non-blocking pass-through")
    return GateResult(verdict=GateVerdict.PASS, model_used="pass1-nonblocking")

async def check_pass2(text: str) -> GateResult:
    # всегда возвращает PASS
    return GateResult(verdict=GateVerdict.PASS, model_used=_PASS2_MODELS[1])
```

`update_handler.py` при этом проверяет `gate1.verdict == GateVerdict.DENY` — **этот код никогда не выполнится**. Архитектура описывает двухпроходной firewall. Runtime реализует логгер. Safety Gate — это governance theater в чистом виде.

Причина задокументирована в коде: false positives на русском/арабском тексте. Но архитектура об этом не говорит — она описывает DENY как гарантию.

### 2.2 ⚠️ `analysis.py` — объявлен как pre-reasoning DAG step, но нигде не вызывается
`models1.md §11`: *"Position: pre-reasoning DAG step (automatic, not called by Orchestrator explicitly)"*  
Поиск по всему коду: ни один файл не импортирует `meta.analysis` кроме `__init__`. Это либо магия ("automatic"), либо мёртвый модуль. Если "automatic" — механизм не документирован и не прослеживается в коде.

### 2.3 ⚠️ `decision_matrix.py` — пороги hardcoded, не читает `policy_registry`
EPK читает пороги из `RUNTIME.epk.*`. Decision matrix — нет:
```python
_FAST_CEILING:    float = 0.0005  # hardcoded
_GENERAL_CEILING: float = 0.003   # hardcoded
```
Комментарий говорит "synced with EPK _DEGRADE_THRESHOLD" — это ручная синхронизация, не автоматическая. При изменении порога в `policy_registry.py` decision_matrix рассинхронизируется молча.

---

## 3. ORCHESTRATION CENTRALIZATION

### 3.1 ✅ EPK — единственный policy authority
Оркестратор не создаёт policy, не выбирает модели напрямую. Чистая реализация.

### 3.2 ✅ Coordinator вызывается только из orchestrator
`multi_agent_coordinator.coordinate()` — один call site в `orchestrator.py`. Нет скрытых вызовов.

### 3.3 ⚠️ `update_handler.py` — скрытая pre-orchestration логика
`update_handler` выполняет до запуска оркестратора:
- Intent classification (`classify()`)
- Web search (`run_tool("search", ...)`)
- Retrieval

Это создаёт де-факто двойной intent classification: один в `update_handler`, второй в `orchestrator` (если `forced_intent` не передан). При `forced_intent` оркестратор пропускает классификацию — но тогда `_already_grounded` логика зависит от `forced_intent is not None`, создавая неявный coupling между двумя местами.

### 3.4 ⚠️ `fallback_handler.py` — тихий tier cascade обходит EPK
```python
_FALLBACK_CASCADE = {Tier.HEAVY: Tier.GENERAL, Tier.GENERAL: Tier.FAST, ...}
```
Если HEAVY-модель недоступна → fallback_handler молча переходит на GENERAL, затем FAST. EPK при этом не вызывается. Биллинг идёт по изначальному tier'у, хотя выполнился FAST-запрос. Архитектура §24: *"Runtime nodes MUST NOT invent fallback chains or mutate fallback behavior silently."*

---

## 4. EMERGENT COMPLEXITY

### 4.1 ✅ MATH correction loop — bounded
Max 1 correction pass. Нет рекурсии.

### 4.2 ✅ Consensus — mutex с HEAVY
`use_consensus=False` при `Tier.HEAVY`. Mutex соблюдён.

### 4.3 ⚠️ Параллельные validators + consensus + safety_agent — непредсказуемый порядок при partial failure
В `coordinate()`:
```python
candidates = [r for r in [primary_result, *validator_results] if _agent_succeeded(r)]
best_candidate = max(candidates, key=lambda r: len(r.text))
```
Выбор "лучшего" кандидата — по длине текста. Не по качеству, не по score. Самый длинный ответ идёт на safety_agent. Это emergent behavior: результат зависит от того, какой агент ответил больше слов, а не лучше.

---

## 5. RETRIEVAL INSTABILITY

### 5.1 ✅ pgvector bug fix задокументирован и исправлен
`candidates` больше не всегда пустой. `similarity_search()` реально вызывается.

### 5.2 ⚠️ `rerank_tokens` — оценка шумовая
```python
rerank_tokens = len(retrieval_result.documents) * 10
```
Это не реальные token-пары. Константа 10 не связана с длиной документов или запроса. Входит в EPK estimate через `estimate_cost()`. Влияние минимальное (RERANK_RATE = $0.10/1M), но это не billing — это шум в EPK вход.

### 5.3 ⚠️ `source_credibility.score_documents()` — pass-through
Задокументировано как "reserved". Все pgvector-результаты проходят без фильтрации по credibility. При этом `filter_results()` для SerpAPI работает активно. Асимметрия: поиск фильтруется, память — нет.

### 5.4 ⚠️ Retrieval полностью skipped если `supabase is None or redis is None`
```python
if supabase is not None and redis is not None:
    # retrieval
```
При недоступности Redis (не Supabase, а именно Redis) — retrieval молча не происходит. Нет предупреждения в ответе, нет флага в `OrchestratorResult`. STRICT intents могут получить пустой контекст и вернуть "retrieval limitation" — но причина (Redis недоступен) не различима от "документов просто нет".

---

## 6. TIER INFLATION

### 6.1 🔴 EPK всегда оценивает по `Tier.GENERAL`, независимо от intent
```python
estimated_output = estimate_output_tokens(
    request.input_tokens,
    request.complexity,
    Tier.GENERAL,   # ← hardcoded
)
estimated = estimate_cost(
    ...
    tier=Tier.GENERAL,  # ← hardcoded
)
```
FAST-запрос (короткий вопрос) оценивается по GENERAL rates ($0.59/$0.79 vs $0.05/$0.08). Это в ~10x завышает estimated_cost → EPK получает завышенный вход → больше запросов попадают в DEGRADED_MODE, чем должны. Документация этого не описывает как намеренное.

### 6.2 ✅ decision_matrix — ascending order исправлен
`0.0005 < 0.003` — корректно. Прежний баг (GENERAL unreachable) устранён.

### 6.3 ⚠️ `_build_messages()` применяет GENERAL strategy для FAST-запросов
Тяжёлый `instruction_prefix` (например для MATH: "Before solving: list ALL constraints...") применяется даже когда агент будет `fast_agent` с `llama-3.1-8b-instant`. Модель получает инструкцию для тяжёлого мышления, но выполнять её не может в 512 токенов.

---

## 7. FAKE BOUNDED CONTEXTS

### 7.1 ⚠️ `UsageEntry` содержит поля, которые никогда не заполняются в webhook
`UsageEntry` объявляет `intent`, `audio_seconds`, `tts_characters`, `tool_calls`. В `webhook.py`:
```python
await meter.record(UsageEntry(
    ...
    model=result.model,
    lang=result.lang,
    # intent — не передаётся
    # audio_seconds — не передаётся  
    # tts_characters — не передаётся
    # tool_calls — не передаётся
))
```
`intent` — поле с default `""` — никогда не заполняется, хотя `result.intent` доступен. Speech billing поля задекларированы в `UsageEntry`, но данные не передаются из `update_handler` в `webhook` в результирующем объекте.

### 7.2 ⚠️ `OrchestratorResult` не несёт `audio_seconds` / `tts_characters`
TTS synthesis происходит в `update_handler`, `tts_result.char_count` логируется, но не попадает в `OrchestratorResult` и не доходит до billing в webhook. Bounded context `OrchestratorResult` неполный — speech cost существует, но невидим для billing pipeline.

### 7.3 ⚠️ `observability/metrics.py` — in-memory sink без экспорта
```python
_counters: dict[str, int] = defaultdict(int)
_gauges: dict[str, float] = {}
```
Данные накапливаются в памяти процесса. Нет экспорта в Prometheus, StatsD, Datadog. `snapshot()` есть, но нигде не вызывается кроме потенциального health check. Метрики не переживают перезапуск.

---

## 8. RUNTIME/DOCS DIVERGENCE

### 8.1 🔴 Safety Gate: docs говорят DENY, runtime говорит PASS
Описано выше в §2.1. Это самое серьёзное расхождение. Документ является SOT по условию архитектуры ("If runtime behavior contradicts this document — the runtime must be corrected"). Корректировать нужно либо документ (признать что Gate = observability), либо runtime (восстановить blocking behavior).

### 8.2 ⚠️ `architecture.md §4` lifecycle vs реальный порядок в `update_handler`
Документ:
```
User Input → Safety Gate (Pass 1 + Pass 2) → Feature Extraction → Multilingual Normalization → EPK
```
Runtime:
```
Safety Gate Pass 1 → Feature Extraction (_classify_complexity) → Multilingual Normalization → Safety Gate Pass 2 → History → Retrieval → Web Search → EPK (внутри orchestrator)
```
Feature Extraction в документе — отдельный explicit шаг. В коде это `_classify_complexity()` — встроенная функция без логирования факта "Feature Extraction completed". Порядок в целом совпадает, но граница между шагами размыта.

### 8.3 ⚠️ `models1.md §11` — `analysis.py` описан как "pre-reasoning DAG step (automatic)"
Нет вызова. Нет механизма "automatic". Либо документация опережает реализацию, либо модуль мёртвый.

---

## 9. HIDDEN AUTHORITY PATHS

### 9.1 🔴 `fallback_handler` — скрытый tier downgrade без уведомления EPK
Разобран в §3.4. Добавление: при cascade HEAVY → GENERAL → FAST:
- Billing tier в `UsageRecord` остаётся тот, что вернул `coordination.model` — это модель реального вызова, но `tier` в `UsageRecord` устанавливается в orchestrator до cascade, не после.
- Пользователь может получить FAST-качество ответа при HEAVY-оценке баланса.

### 9.2 ⚠️ `update_handler` — web search без EPK approval
```python
# в update_handler, до вызова orchestrator:
web_result = await run_tool("search", params={"query": text, "lang": lang})
```
Web search запускается до EPK. Стоимость поиска (SerpAPI call) не входит в EPK оценку. EPK не знает, что поиск уже произошёл.

### 9.3 ⚠️ Vision fast-path полностью обходит EPK
```python
if not vision_result.needs_pipeline:
    return OrchestratorResult(
        ...
        cost_usd=0.001,  # ← hardcoded estimate
        epk_decision=EPKDecision.ALLOW,  # ← assumed
    )
```
Vision fast-path: hardcoded cost `0.001`, EPK не вызывается, баланс не проверяется. Пользователь с нулевым балансом может получить vision-ответ. Это задокументировано в архитектуре ("OUTSIDE EPK DAG by design") — но экономический side effect не описан.

---

## 10. OBSERVABILITY COLLAPSE

### 10.1 ⚠️ `metrics.py` — данные нигде не экспортируются
Описано в §7.3. Конкретнее: `increment()` и `gauge()` нигде не вызываются в production коде. Grep по codebase: вызовов нет. Это не просто in-memory — это мёртвый API.

### 10.2 ⚠️ `tracing.py` — context manager `trace()` существует, но не используется
```python
@contextmanager
def trace(name: str, **tags) -> Generator:
    ...
    logger.info("trace", extra={"span": name, "elapsed_ms": ...})
```
Нет вызовов в orchestrator, coordinator, retrieval. Latency по pipeline шагам не измеряется. Единственная наблюдаемость — stdout логи без структурированного span ID.

### 10.3 ⚠️ Safety Gate signals не достигают monitoring
Pass 2 логирует `WARNING` при UNSAFE сигнале — но в `check_pass2()` вызов `_classify_with_model()` обёрнут в try/except, и при exception → `return True` (safe). UNSAFE сигнал может быть потерян молча при API ошибке модели.

### 10.4 ⚠️ Нет span correlation между `update_handler` → `orchestrator` → `coordinator`
Каждый компонент логирует независимо. Нет `request_id` или `trace_id`, который проходил бы через весь pipeline. Невозможно связать лог "Orchestrator crashed" с конкретным Telegram update или пользователем без ручной корреляции по времени.

---

## СВОДКА

| Категория | Статус | Критичность |
|---|---|---|
| Hidden nondeterminism | Частично (complexity heuristic, _build_messages tier mismatch) | Средняя |
| Governance theater | 🔴 Safety Gate — docs/runtime gap | Высокая |
| Orchestration centralization | Частично (update_handler pre-orchestration) | Средняя |
| Emergent complexity | Частично (best_candidate = longest) | Низкая |
| Retrieval instability | Частично (rerank_tokens noise, Redis silent skip) | Средняя |
| Tier inflation | 🔴 EPK всегда GENERAL estimate | Средняя |
| Fake bounded contexts | speech billing не доходит до record() | Средняя |
| Runtime/docs divergence | 🔴 Safety Gate (критично), analysis.py | Высокая |
| Hidden authority paths | fallback cascade bypasses EPK, pre-EPK search | Средняя |
| Observability collapse | metrics/tracing — мёртвый код, нет request_id | Средняя |

### Три первоочередных исправления

**1. Зафиксировать Safety Gate статус в документации**
Либо восстановить blocking (с narrow промптом, только явные атаки), либо официально переименовать в "Safety Observability Layer" и убрать из architecture.md гарантию DENY. Текущее состояние — лжёт архитектура.

**2. EPK estimate tier**
`estimate_output_tokens(..., Tier.GENERAL)` → заменить на adaptive: если `complexity == LOW` и `input_tokens < threshold` → оценивать по `Tier.FAST`. Иначе GENERAL. Это снизит ложные DEGRADED_MODE для коротких запросов.

**3. `decision_matrix` → читать из `policy_registry`**
```python
from core.kernel.policy_registry import RUNTIME
_FAST_CEILING    = RUNTIME.epk.???   # добавить поле
_GENERAL_CEILING = RUNTIME.epk.degrade_threshold
```
Иначе при изменении EPK порогов decision_matrix рассинхронизируется молча.
