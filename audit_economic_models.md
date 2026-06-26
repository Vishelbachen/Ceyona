# Аудит: economic.md v5.7 + models.md v9.1 vs код
Дата: 26 июня 2026  
Базовый аудит: audit_economic_models.md (25 июня 2026, v5.5/v9.0)  
Текущие версии: economic.md v5.7, models.md v9.1  
Файлы кода: cost_model.py, policy_registry.py, decision_matrix.py, execution_policy_kernel.py, pricing_engine.py, usage_meter.py, orchestrator.py, model_router.py, webhook.py, update_handler.py, vision_handler.py

---

## ИТОГ: Что было закрыто (v5.5→v5.6 / v9.0→v9.1)

| # | Баг из прошлого аудита | Статус |
|---|---|---|
| BUG-01 | Vision billing: ставки llama-4-scout вместо qwen3.6-27b | ✅ ЗАКРЫТ |
| BUG-02 | Safety Gate не биллится в _run_allow / _run_degraded | ✅ ЗАКРЫТ (webhook) |
| BUG-03 | actual_cost() не пробрасывал safeguard_output_tokens | ✅ ЗАКРЫТ |
| MISMATCH-01 | economic.md §5/6/11 — пороги устарели | ✅ ЗАКРЫТ |
| MISMATCH-02 | economic.md §5/6 — примеры по старым тарифам | ✅ ЗАКРЫТ |
| MISMATCH-03 | economic.md §1.1 — устаревший блок MODEL_RATES | ✅ ЗАКРЫТ |
| MISMATCH-04 | models.md §27.5 — Pass1 заявлен no-op | ✅ ЗАКРЫТ |
| MISMATCH-05 | economic.md §3 — ссылка на policy_registry отсутствует | ✅ ЗАКРЫТ |
| DEBT-01 | multilingual billing отсутствует на ALLOW/DEGRADED путях | ✅ ЗАКРЫТ (webhook) |
| DEBT-02 | vision_actual_cost() deprecated wrapper | ✅ ЗАКРЫТ |
| DEBT-03 | Safety Gate cost = revenue leak при DENY | ✅ ЗАКРЫТ |
| DEBT-04 | gpt-oss-20b reasoning_effort на HEAVY fallback пути | ✅ ЗАКРЫТ |
| DEBT-05 | qwen3-32b в QWEN_THINKING_DISABLED_MODELS | ✅ ЗАКРЫТ |
| DEBT-06 | economic.md §12: open item Jul 17 не закрыт | ✅ ЗАКРЫТ |
| DEBT-07 | estimate_safety_cost() vs Pass1 no-op | ✅ ЗАКРЫТ (через MISMATCH-04) |

**Из 15 позиций прошлого аудита все 15 закрыты.** Ниже — новые находки при проверке текущего кода.

---

## 🔴 АКТИВНЫЕ БАГИ

---

### BUG-A1 — Safety Gate стоимость не входит в `result.usage.cost_usd` на ALLOW/DEGRADED путях

**Файлы:** `core/execution/orchestrator.py` (строки ~473, ~568)  
**Приоритет:** Средний (функциональный, не revenue leak)

**Суть:** `_run_allow()` и `_run_degraded()` вычисляют `cost_usd` без safety-токенов:

```python
cost = actual_cost(
    input_tokens=coordination.input_tokens,
    output_tokens=coordination.output_tokens,
    embedding_tokens=request.embedding_tokens,
    rerank_tokens=request.rerank_tokens,
    tier=_billing_tier,
    embedding_type=request.embedding_type,
    # safety_pass1_tokens, safety_pass2_tokens — НЕ ПЕРЕДАНЫ
)
```

Фактически пользователь с Safety Gate правильно биллится через `webhook.py`, где `safety_cost = actual_safety_cost(...)` добавляется к `result.usage.cost_usd` отдельно. Это **намеренная архитектура** (безопасность выполняется до EPK, вне контекста оркестратора). Но тогда:

1. `result.usage.cost_usd` отражает только LLM-стоимость — не полную стоимость запроса
2. Поле семантически неполно: `UsageRecord.cost_usd` ≠ `total_cost_usd` в webhook

**Риск:** Если кто-то читает `result.usage.cost_usd` напрямую (логирование, метрики) — видит заниженную стоимость. `billed_cost_usd` в Supabase правильный (через webhook), но промежуточное поле вводит в заблуждение.

**Рекомендация:** добавить комментарий в `UsageRecord` или переименовать в `llm_cost_usd`, либо явно передавать safety_tokens в `_run_allow`/`_run_degraded` и включать в `cost_usd`.

---

### BUG-A2 — `_run_allow()`: multilingual cost не включён в `result.usage.cost_usd`

**Файлы:** `core/execution/orchestrator.py` (~473), `transport/telegram/webhook.py` (~471)  
**Приоритет:** Низкий (revenue не теряется, но учёт неполный)

На ALLOW/DEGRADED путях `_ml_cost` добавляется в `total_cost_usd` только в `webhook.py`:

```python
total_cost_usd = result.usage.cost_usd + safety_cost + _ml_cost
```

В `_run_heavy()` multilingual cost бакается в `cost_usd` напрямую. Различие поведения между путями: на HEAVY `cost_usd` включает multilingual, на ALLOW — нет.

**Риск:** аналогично BUG-A1 — поле `cost_usd` семантически разное в зависимости от пути. Billing в Supabase корректен. Но при анализе cost_usd по записям в usage_log ALLOW и HEAVY записи будут несравнимы без учёта этого.

---

## 🟠 НЕСОСТЫКОВКИ ДОКУМЕНТАЦИИ С КОДОМ

---

### MISMATCH-A1 — `vision_handler.py`: docstring ссылается на устаревший llama-4-scout

**Файл:** `transport/telegram/vision_handler.py`, строка 334  
**Тип:** stale comment

Функция `process_single_image()` имеет docstring:
```python
"""
Step 1 — llama-4-scout extracts image content (text or description).
...
"""
```

Реальная модель в коде: `_VISION_MODEL = "qwen/qwen3.6-27b"` (строка 17).  
llama-4-scout удалён, qwen3.6-27b используется. Docstring не обновлён.

**Фикс:** заменить "llama-4-scout" на "qwen/qwen3.6-27b" в docstring.

---

### MISMATCH-A2 — economic.md §7: поле `resolved_model` не включено в таблицу обязательных полей usage_meter

**Документ:** `economic.md`, §7 (USAGE METER — MANDATORY FIELDS)  
**Файл:** `payments/usage_meter.py`

В §7 таблица обязательных полей `usage`:
```python
usage = {
    "input_tokens":     int,
    "output_tokens":    int,
    "tier":             str,
    "embedding_tokens": int,
    "embedding_type":   str,
    "rerank_tokens":    int,
    "audio_seconds":    float,
    "tts_characters":   int,
    "tool_calls":       int,
}
```

В реальном `UsageEntry` есть дополнительные поля, которые отсутствуют в §7:
- `resolved_model` — требуется models.md §25.3 (per-model billing readiness)
- `safety_pass1_tokens`, `safety_pass2_tokens`, `safety_safeguard_tokens`, `safety_safeguard_output_tokens`
- `safety_agent_input_tokens`, `safety_agent_output_tokens`
- `multilingual_input_tokens`, `multilingual_output_tokens`, `multilingual_model`
- `lc_transformer_input_tokens`, `lc_transformer_output_tokens`

Документ описывает базовый MVP, а код реализует расширенный вариант. При добавлении новых полей §7 не обновлялся.

**Фикс:** обновить §7 economic.md, добавив все поля UsageEntry.

---

### MISMATCH-A3 — economic.md §4.2: `actual_cost()` описан без параметров safety

**Документ:** `economic.md`, §4.2

Документальная сигнатура:
```python
def actual_cost(
    input_tokens,
    output_tokens,
    embedding_tokens,
    rerank_tokens,
    tier,
    embedding_type="large",
) -> float:
```

Реальная сигнатура в `cost_model.py`:
```python
def actual_cost(
    input_tokens: int,
    output_tokens: int,
    embedding_tokens: int,
    rerank_tokens: int,
    tier: Tier,
    embedding_type: str = "large",
    safety_pass1_tokens: int = 0,
    safety_pass2_tokens: int = 0,
    safety_safeguard_tokens: int = 0,
    safety_safeguard_output_tokens: int = 0,  # добавлен в v5.6
) -> float:
```

Четыре параметра `safety_*` не отражены в §4.2. Это делает документальный пример неверным.

**Фикс:** обновить §4.2 actual_cost() сигнатурой с safety-параметрами.

---

### MISMATCH-A4 — economic.md §8: формула `user_charge` ссылается на `access_controller.py`, но margin применяется в `usage_meter.py`

**Документ:** `economic.md`, §8

Документ:
```python
# access_controller.py
credits_usd = actual_cost * MARGIN
# deduct credits_usd from user_balance_usd
```

Реальный код: `access_controller.deduct(user_id, total_cost_usd)` принимает уже вычисленный `total_cost_usd` из webhook, без применения margin. Margin применяется в `usage_meter.compute_billed()` → `apply_margin()`. `AccessController` margin не знает.

Схема из webhook.py:
1. `total_cost_usd` = raw cost (без margin)
2. `ac.deduct(user_id, total_cost_usd)` — списывает RAW
3. `billed = meter.compute_billed(total_cost_usd)` — RAW × 1.3 = что пишем в Supabase usage_log

**Вопрос:** с баланса списывается `total_cost_usd` (raw), а в `billed_cost_usd` пишется raw × 1.3. Это означает, что баланс уменьшается на raw-стоимость, а не на "billed" (с наценкой). Либо это намеренно и документ в §8 неточен, либо в `deduct()` должен передаваться `billed`.

**Риск:** реальный вычет из баланса пользователя = raw LLM cost, не raw × 1.3. Платформа не удерживает маржу из баланса. `billed_cost_usd` в Supabase — аналитическое поле, не фактическое списание.

Если маржа должна удерживаться из пользовательского баланса — это бизнес-решение, требующее исправления в webhook.py:
```python
await ac.deduct(user_id, meter.compute_billed(total_cost_usd))  # billed, не raw
```

Если намеренно (баланс = raw, billed = аналитика) — §8 нужно обновить.

---

## 🟡 ТЕХНИЧЕСКИЙ ДОЛГ

---

### DEBT-A1 — ✅ ЗАКРЫТ (Jun 2026)

`estimate_cost()` теперь принимает `lc_transformer_input_tokens`. Orchestrator передаёт
`request.input_tokens` когда `complexity == CRITICAL and input_tokens > 32_000`.
Output оценивается консервативно в 800 токенов (GENERAL MAX_OUTPUT_CAP).
Для 40K input: overhead ≈ $0.026 — теперь включён в EPK estimate.

---

### DEBT-A2 — ✅ ЗАКРЫТ (Jun 2026)

Groq официально подтвердил passthrough pricing для compound систем. Реализовано:
- `_COMPOUND_UNDERLYING_RATES` в `cost_model.py` — точные ставки по каждой внутренней модели
- `actual_compound_cost_from_breakdown(breakdown)` — точный биллинг по `usage.usage_breakdown` из Groq API
- `groq_client.py` парсит `usage.usage_breakdown` в обоих методах (`complete()`, `complete_with_tools()`)
- `webhook.py` использует breakdown-first подход с fallback на `_COMPOUND_RATES` (dominant-model)
- `economic.md §1.3` обновлён — описывает реальную реализацию. ✅

---

### DEBT-A3 — `_run_allow()` и `_run_degraded()` не передают safety_tokens в `OrchestratorResult`

**Файл:** `core/execution/orchestrator.py`

`OrchestratorResult` имеет поля `safety_pass1_tokens`, `safety_pass2_tokens`, `safety_safeguard_tokens`, `safety_safeguard_output_tokens`. На ALLOW/DEGRADED путях они не заполняются оркестратором — их устанавливает `update_handler.py` через `dataclasses.replace()`.

Это работает, но создаёт неочевидный контракт: поля `OrchestratorResult` при выходе из `_run_allow()` всегда 0, и только после прохода через `update_handler` они становятся правильными. Документирование этого контракта отсутствует.

**Рекомендация:** добавить комментарий в `OrchestratorResult` к safety-полям: "Populated by update_handler.py after gate completes — always 0 on orchestrator return."

---

### DEBT-A4 — `vision_handler.py` `process_media_group()`: второй проход использует тот же docstring с упоминанием llama-4-scout

**Файл:** `transport/telegram/vision_handler.py` (~596-605)

Та же ситуация, что MISMATCH-A1, но в функции `process_media_group()`. Обе функции обрабатывают изображения, обе используют `_VISION_MODEL = "qwen/qwen3.6-27b"`, но docstring в обоих местах не обновлены. (Связан с MISMATCH-A1 — один фикс закрывает оба.)

---

## 📋 Сводная таблица новых находок

| # | Категория | Файл | Приоритет |
|---|---|---|---|
| BUG-A1 | `result.usage.cost_usd` не включает safety cost на ALLOW/DEGRADED путях | orchestrator.py | 🟠 Средний |
| BUG-A2 | `result.usage.cost_usd` не включает multilingual cost на ALLOW/DEGRADED | orchestrator.py | 🟡 Низкий |
| MISMATCH-A1 | vision_handler.py docstring: "llama-4-scout" вместо "qwen3.6-27b" | vision_handler.py | 🟡 Низкий |
| MISMATCH-A2 | economic.md §7: таблица MANDATORY FIELDS неполная | economic.md | 🟠 Средний |
| MISMATCH-A3 | economic.md §4.2: actual_cost() сигнатура без safety-параметров | economic.md | 🟠 Средний |
| MISMATCH-A4 | economic.md §8: margin применяется в usage_meter, не access_controller | economic.md / webhook.py | 🔴 Требует решения |
| DEBT-A1 | lc_transformer cost не входит в EPK estimate_cost() для CRITICAL | cost_model.py | 🟡 Низкий |
| DEBT-A2 | compound billing — закрыт через usage_breakdown + `_COMPOUND_UNDERLYING_RATES` | cost_model.py | ✅ Закрыт |
| DEBT-A3 | safety-поля OrchestratorResult всегда 0 при выходе из оркестратора | orchestrator.py | 🟡 Низкий |
| DEBT-A4 | vision_handler.py process_media_group(): тот же stale docstring | vision_handler.py | 🟡 Низкий |

---

## Детальный разбор MISMATCH-A4 (margin vs deduct)

Это единственная находка с неопределённым бизнес-намерением. Текущий flow:

```
webhook.py:
  total_cost_usd = result.usage.cost_usd + safety_cost + _ml_cost  # raw
  await ac.deduct(user_id, total_cost_usd)                         # списываем raw
  billed = meter.compute_billed(total_cost_usd)                    # raw × 1.3
  await meter.record(UsageEntry(..., billed_cost_usd=billed))      # пишем в Supabase
```

Варианты:

**Вариант A (текущее поведение — маржа НЕ берётся с баланса):**
- Пользователь платит raw LLM cost из баланса
- `billed_cost_usd` — аналитическое поле для расчёта Revenue (что платформа "должна была" заработать)
- Бизнес-смысл: пользователь не видит наценку в списаниях, маржа = разница между платежом TON и реальным расходом Groq
- Нужно: обновить §8 economic.md, убрать упоминание `MARGIN` из формулы `deduct()`

**Вариант B (маржа должна браться с баланса — economic.md §8 верен):**
- В webhook.py нужно исправить: `await ac.deduct(user_id, billed)` вместо `total_cost_usd`
- Revenue = billed - raw (правильная маржа)
- Риск: пользовательский баланс тает быстрее на 30%

Рекомендация: зафиксировать намерение и привести код и документацию к единому варианту.

---

## Что полностью соответствует документации

Для справки — проверенные аспекты, расхождений не найдено:

- `MODEL_RATES` в cost_model.py: $0.075/$0.30 (FAST), $0.60/$3.00 (GENERAL), $0.15/$0.60 (HEAVY) ✅
- `EMBEDDING_RATES`: large=0.10, small=0.02 ✅
- `RERANK_RATE`: 0.10 ✅
- `MAX_OUTPUT_CAP`: FAST=512, GENERAL=800, HEAVY=4096 ✅
- `COMPLEXITY_MULTIPLIER`: LOW=1.2, MEDIUM=1.8, HIGH=2.5, CRITICAL=3.0 ✅
- `policy_registry.RUNTIME`: degrade=0.006, heavy=0.010, fast_ceiling=0.001, deny=0.0001 ✅
- `decision_matrix` читает из RUNTIME (не хардкодит) ✅
- `execution_policy_kernel` читает из RUNTIME (не хардкодит) ✅
- Complexity.CRITICAL → HEAVY_REQUIRED в EPK ✅
- `_DEFAULT_BALANCE_USD = 0.10` (policy_registry → access_controller) ✅
- `apply_margin(usd, margin=1.3)` ✅
- `_VISION_RATES`: input=0.60, output=3.00 (qwen3.6-27b) ✅
- `_VISION_MODEL = "qwen/qwen3.6-27b"` в vision_handler ✅
- FAST primary: `openai/gpt-oss-20b` ✅
- GENERAL primary: `qwen/qwen3.6-27b`, fallback: `openai/gpt-oss-120b` ✅
- HEAVY primary: `openai/gpt-oss-120b` ✅
- CONSENSUS_MODEL: `openai/gpt-oss-120b` ✅
- FAST_AGENT_MODEL: `groq/compound-mini`, DEEP_AGENT_MODEL: `groq/compound` ✅
- MULTILINGUAL_ARABIC_MODEL: `allam-2-7b`, OTHER: `qwen/qwen3.6-27b` ✅
- LONG_CONTEXT_MODEL: `qwen/qwen3.6-27b` ✅
- SHAPER_MODEL: `openai/gpt-oss-20b` ✅
- `QWEN_THINKING_DISABLED_MODELS` — только `qwen/qwen3.6-27b` (qwen3-32b удалён) ✅
- `_MAX_TOKENS` читается из `policy_registry.RUNTIME.tier_configs` ✅
- `preferred_model` присвоен во всех 12 ненулевых ветках `_resolve_routing()` (verbatim=None) ✅
- Safety Gate: NON-BLOCKING, оба пасса всегда PASS ✅
- Pass 1 (22m): вызывается, логирует, всегда возвращает PASS ✅
- `estimate_safety_cost()`: включает все три модели ✅
- `actual_safety_cost()`: принимает safeguard_output_tokens ✅
- `actual_cost()`: принимает все safety-параметры ✅
- multilingual billing на ALLOW/DEGRADED: обрабатывается в webhook.py (с guard против double-billing на HEAVY) ✅
- `resolved_model` логируется в Supabase через UsageEntry ✅
- Deprecated models (qwen3-32b, llama-4-scout, llama-3.1-8b, llama-3.3-70b): удалены из активного routing ✅
- `lc_transformer_input/output_tokens` в UsageEntry и OrchestratorResult ✅
- `long_context_transformer.py` существует (`llm/long_context_transformer.py`) ✅
- economic.md §10: DENY path биллит Safety Gate если токены есть (webhook guard) ✅
- reasoning_effort: "low" для gpt-oss-20b/FAST, "high" для gpt-oss-120b/HEAVY ✅