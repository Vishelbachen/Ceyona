# Аудит: economic.md + models.md vs код
Дата: 25 июня 2026  
Файлы: economic.md v5.5, models.md v9.0, cost_model.py, policy_registry.py, decision_matrix.py, execution_policy_kernel.py, pricing_engine.py, usage_meter.py, orchestrator.py

---

## 🔴 КРИТИЧЕСКИЕ БАГИ (revenue leak / неверный биллинг)

---

### BUG-01 — Vision billing: устаревшие ставки llama-4-scout

**Файл:** `payments/pricing_engine.py`, строки 71–73  
**Статус:** АКТИВНЫЙ, деньги считаются неверно

Vision модель сменилась с `llama-4-scout` ($0.11/$0.34) на `qwen/qwen3.6-27b` ($0.60/$3.00), но `_VISION_RATES` не обновлены.

```python
# СЕЙЧАС (неверно):
# llama-4-scout vision extraction rates (Groq, May 2026)
# $0.11 input / $0.34 output per 1M tokens.
_VISION_RATES: dict[str, float] = {"input": 0.11, "output": 0.34}
```

```python
# ДОЛЖНО БЫТЬ:
# qwen/qwen3.6-27b vision extraction rates (Groq, Jun 2026)
# $0.60 input / $3.00 output per 1M tokens.
_VISION_RATES: dict[str, float] = {"input": 0.60, "output": 3.00}
```

**Эффект:** vision запросы занижают стоимость в ~8.8x по output. Пользователь платит за `qwen3.6-27b` по тарифу `llama-4-scout`.  
**Комментарий в коде и docstring** тоже надо обновить — сейчас написано "Compute raw cost for a llama-4-scout vision extraction call" — это уже неправда.

---

### BUG-02 — `_run_allow` и `_run_degraded`: Safety Gate токены не входят в `actual_cost()`

**Файл:** `core/execution/orchestrator.py`, строки ~472 и ~567

В `_run_allow` и `_run_degraded` вызов `actual_cost()` идёт без `safety_pass1_tokens` / `safety_pass2_tokens` / `safety_safeguard_tokens`. Это значит Safety Gate на этих путях **не биллится**.

```python
# СЕЙЧАС (оба пути — неверно):
cost = actual_cost(
    input_tokens=coordination.input_tokens,
    output_tokens=coordination.output_tokens,
    embedding_tokens=request.embedding_tokens,
    rerank_tokens=request.rerank_tokens,
    tier=_billing_tier,
    embedding_type=request.embedding_type,
    # safety токены НЕ переданы
)
```

В `_run_heavy` это сделано правильно (строка ~776). В двух других путях — нет.

**Эффект:** Safety Gate (все три модели) не оплачивается на ALLOW и DEGRADED_MODE путях. По economic.md §2 это запрещено: "Every model call that produces a response MUST be billed."

**Фикс:** добавить в оба вызова:
```python
safety_pass1_tokens=gate_result.tokens_used,
safety_pass2_tokens=gate_result.pass2_tokens,
safety_safeguard_tokens=gate_result.safeguard_tokens_used,
```

---

### BUG-03 — `actual_cost()` не имеет параметра `safety_safeguard_output_tokens`

**Файл:** `core/kernel/cost_model.py`, строка 152

`actual_safety_cost()` принимает `safeguard_output_tokens`, но `actual_cost()` его **не пробрасывает**. `gpt-oss-safeguard-20b` стоит $0.30/1M output — это не копейки.

```python
# actual_cost() сейчас:
def actual_cost(
    ...
    safety_safeguard_tokens: int = 0,
    # safety_safeguard_output_tokens — ОТСУТСТВУЕТ
) -> float:
    ...
    return ... + actual_safety_cost(
        pass1_tokens=safety_pass1_tokens,
        pass2_tokens=safety_pass2_tokens,
        safeguard_tokens=safety_safeguard_tokens,
        # safeguard_output_tokens=??? — не передаётся
    )
```

**Эффект:** output-токены `gpt-oss-safeguard-20b` ($0.30/1M) никогда не биллятся через `actual_cost()`.

---

## 🟠 НЕСОСТЫКОВКИ ДОКУМЕНТАЦИИ С КОДОМ

---

### MISMATCH-01 — economic.md §5, §6, §11: значения порогов устарели

**Документ:** `economic.md`, §5 EPK, §6 Decision Matrix, §11 Sync Contracts

economic.md утверждает:
```
_DEGRADE_THRESHOLD = 0.003  ✓
_HEAVY_THRESHOLD   = 0.008  ✓
_FAST_CEILING      = 0.0005 ✓
_GENERAL_CEILING   = 0.003  ✓
```

Реальные значения в `policy_registry.py`:
```python
degrade_threshold = 0.006   # было 0.003
heavy_threshold   = 0.010   # было 0.008
fast_ceiling      = 0.001   # было 0.0005
```

`decision_matrix.py` корректно читает из `RUNTIME` (значения 0.001 / 0.006), но `economic.md` §11 ставит галочки ✓ напротив старых значений.

**Что нужно:** обновить §5, §6, §11 economic.md с актуальными цифрами из policy_registry.py. Особенно §5 — все примеры ("→ ALLOW", "→ DEGRADED_MODE") считают по старым порогам 0.003 и дают неверные выводы.

---

### MISMATCH-02 — economic.md §5, §6: примеры считают по старым тарифам

**Документ:** `economic.md`, §5 и §6

Примеры в §5 используют старые GENERAL ставки ($0.59/$0.79):
```
- A 500-token input + 600-token output at GENERAL = ~$0.00077 → ALLOW
  Реально: (500×0.60 + 600×3.00)/1M = $0.002100 → ALLOW (при degrade=0.006)
  
- A 2000-token input + 2000-token output at GENERAL = ~$0.00276 → ALLOW
  Реально: (2000×0.60 + 2000×3.00)/1M = $0.007200 → DEGRADED_MODE
```

В §6 Decision Matrix примеры используют старые FAST ставки ($0.05/$0.08) и порог $0.0005:
```
- 500 input + 300 estimated output = $0.000049 → FAST
  Реально: (500×0.075 + 300×0.30)/1M = $0.000128 → FAST (при ceiling=0.001 — верно)
```

**Что нужно:** пересчитать все примеры §5 и §6 с актуальными ценами и порогами.

---

### MISMATCH-03 — economic.md §1.1: MODEL_RATES отмечены как устаревшие, но код уже обновлён

**Документ:** `economic.md`, §1.1, блок `MODEL_RATES in cost_model.py`

В economic.md написано:
```python
# ⚠️ ОБНОВИТЬ при смене primary в model_router.py (текущие значения = устаревшие primary)
MODEL_RATES = {
    Tier.FAST:    {"input": 0.05,  "output": 0.08},   # llama-3.1-8b-instant ⚠️ deprecated
    Tier.GENERAL: {"input": 0.59,  "output": 0.79},   # llama-3.3-70b-versatile ⚠️ deprecated
    ...
}
```

В реальном `cost_model.py` MODEL_RATES **уже обновлены**:
```python
MODEL_RATES = {
    Tier.FAST:    {"input": 0.075, "output": 0.30},   # gpt-oss-20b ✅
    Tier.GENERAL: {"input": 0.60,  "output": 3.00},   # qwen3.6-27b ✅
    Tier.HEAVY:   {"input": 0.15,  "output": 0.60},   # gpt-oss-120b ✅
}
```

В §1.1 этот блок с пометкой "⚠️ ОБНОВИТЬ" — мёртвый устаревший документ внутри документа. Вводит в заблуждение.

**Что нужно:** обновить §1.1 economic.md — убрать "устаревший" блок MODEL_RATES, заменить актуальным.

---

### MISMATCH-04 — models.md §27.5: Pass 1 заявлен как no-op, но модель вызывается

**Документ:** `models.md`, §27.5, раздел llama-prompt-guard-2-22m

```
Pass 1 implementation status:
Currently no-op — model NOT called. `check_pass1()` returns `GateVerdict.PASS` immediately
with only a debug log.
```

Реальный `security/safety_gate.py` (строка 198): `check_pass1()` **вызывает** `_classify_with_model()` и логирует MALICIOUS/BENIGN сигналы.

Это либо документация отстала от кода, либо код опередил документацию. В любом случае — несостыковка.

`estimate_safety_cost()` считает Pass1 в оценку — это правильно в обоих сценариях. Но документ вводит в заблуждение о статусе.

**Что нужно:** обновить описание в models.md §27.5 — Pass 1 активен, model вызывается.

---

### MISMATCH-05 — economic.md §3: MAX_OUTPUT_CAP для FAST заявлен "estimation cap (actual API limit: 1024)"

**Документ:** `economic.md`, §3

```
Tier.FAST: 512,  # estimation cap (actual API limit: 1024)
```

В `policy_registry.py`:
```python
Tier.FAST: TierConfig(max_output_tokens=1_024)
```

Это верно. Но для GENERAL:
```
Tier.GENERAL: 800,  # estimation cap — lowered from 2048
               # actual API limit remains 3072 (policy_registry.py)
```

`policy_registry.py` реально: `max_output_tokens=3_072` — совпадает. ✓  
Но в примечании economic.md написано "actual API limit remains 3072" без упоминания `policy_registry.py`. Для HEAVY: `max_output_tokens=6_144` в реестре — тоже совпадает.

Фактически всё верно, но пояснение неполное — не ссылается на policy_registry как источник истины.

---

## 🟡 КОСЯКИ И ТЕХНИЧЕСКИЙ ДОЛГ

---

### DEBT-01 — `actual_cost()` не биллит multilingual и lc_transformer

**Файл:** `core/execution/orchestrator.py`

В `_run_heavy()` multilingual и lc_transformer биллятся отдельными вызовами `actual_cost()` (строки ~745, ~756). В `_run_allow()` и `_run_degraded()` — нет вообще.

В models.md/economic.md есть поля `multilingual_input_tokens` / `lc_transformer_input_tokens` в UsageEntry, они пишутся в Supabase. Но в расчёт `cost_usd` в `UsageRecord` попадают только через `_run_heavy`. На других путях multilingual-биллинг отсутствует.

Это не катастрофа (multilingual = allam-2-7b ≈ FAST tier, дёшево), но по economic.md §2 — "Every model call... MUST be billed".

---

### DEBT-02 — `vision_actual_cost()` в cost_model.py — deprecated wrapper, не удалён

**Файл:** `core/kernel/cost_model.py`, строка 176

Функция помечена DEPRECATED, перенаправляет в `pricing_engine.vision_cost()`. Существует только "для обратной совместимости". Поиск по коду показывает, что вызывающих нет — только `update_handler.py` импортирует напрямую из `pricing_engine`. Wrapper можно и нужно удалить.

---

### DEBT-03 — economic.md §10: "Safety Gate executes before EPK" противоречит описанию billing flow

**Документ:** `economic.md`, §10

Строка 7b: `[VERBATIM → exit, no LLM billing, tool cost only — §47]`  
Строка 7: `[DENY → exit, no LLM billing; Safety Gate cost not recorded on DENY]`

По architecture.md Safety Gate идёт до EPK. Если DENY — Safety Gate уже выполнилась, но биллинг на неё не идёт. Это задокументировано в §10 ("Safety Gate usage ← recorded post-confirmation"). Но формулировка "not recorded on DENY" означает revenue leak на DENY-запросах — это **намеренная политика**, но нигде не обоснована как бизнес-решение. При высоком уровне DENYs (спамеры, атаки) это реальная дыра.

---

### DEBT-04 — `gpt-oss-20b` в HEAVY fallback цепочке: reasoning_effort не определён для этого сценария

**Файл:** `llm/model_router.py`

```python
_GPT_OSS_REASONING_EFFORT = {
    "openai/gpt-oss-20b": {
        Tier.FAST:    "low",
        Tier.GENERAL: "medium",
        Tier.HEAVY:   "medium",  # cascade fallback — keep balanced
    },
}
```

Если `gpt-oss-20b` используется на HEAVY пути как fallback (чего по архитектуре быть не должно — HEAVY = только gpt-oss-120b), то reasoning_effort будет "medium" вместо "high". Это не баг биллинга, но потенциальная деградация качества без алерта.

---

### DEBT-05 — `qwen/qwen3-32b` в `QWEN_THINKING_DISABLED_MODELS` — deprecated модель в активном frozenset

**Файл:** `llm/model_router.py`

```python
QWEN_THINKING_DISABLED_MODELS: frozenset[str] = frozenset({
    "qwen/qwen3-32b",     # deprecated Jul 17, 2026
    "qwen/qwen3.6-27b",
})
```

Комментарий "deprecated Jul 17, kept here until removal in case of emergency fallback" — но этой модели нет в `_TIER_MODELS`. Она никогда не будет выбрана через нормальный routing. Оставлять её в frozenset означает, что `requires_thinking_disabled()` вернёт True для несуществующего пути. Чистить после Jul 17.

---

### DEBT-06 — economic.md §12 open items: "ПРИОРИТЕТ Jul 17" уже частично сделан, но не закрыт

**Документ:** `economic.md`, §12

```
- [ ] ПРИОРИТЕТ — Jul 17, 2026: заменить qwen/qwen3-32b и llama-4-scout в model_router.py
      до deprecation. Обновить MODEL_RATES если новый GENERAL primary дороже $0.59/$0.79.
```

Судя по коду: model_router уже использует `qwen3.6-27b` и `gpt-oss-120b` вместо deprecated моделей. MODEL_RATES уже обновлены. Этот пункт можно закрывать — [x].

---

### DEBT-07 — `estimate_safety_cost()` включает Pass 1 в оценку, но Pass 1 был заявлен как no-op (связан с MISMATCH-04)

**Файл:** `core/kernel/cost_model.py`

`estimate_safety_cost()` добавляет ~300 токенов Pass1 в EPK оценку. Если Pass1 реально no-op — переоценка (консервативно, допустимо). Если Pass1 активен (как показывает код) — оценка корректна. Нужно разрешить противоречие MISMATCH-04, после чего этот пункт закрывается автоматически.

---

## 📋 Сводная таблица

| # | Категория | Файл | Приоритет |
|---|---|---|---|
| BUG-01 | Vision billing: ставки llama-4-scout вместо qwen3.6-27b | pricing_engine.py | 🔴 Срочно |
| BUG-02 | Safety Gate не биллится в _run_allow / _run_degraded | orchestrator.py | 🔴 Срочно |
| BUG-03 | actual_cost() не пробрасывает safeguard_output_tokens | cost_model.py | 🔴 Срочно |
| MISMATCH-01 | economic.md §5/6/11 — пороги 0.003/0.008/0.0005 вместо актуальных | economic.md | 🟠 |
| MISMATCH-02 | economic.md §5/6 — примеры по старым тарифам | economic.md | 🟠 |
| MISMATCH-03 | economic.md §1.1 — "устаревший" блок MODEL_RATES уже не устарел | economic.md | 🟠 |
| MISMATCH-04 | models.md §27.5 — Pass1 заявлен no-op, код вызывает модель | models.md | 🟠 |
| MISMATCH-05 | economic.md §3 — ссылка на policy_registry как источник истины отсутствует | economic.md | 🟡 |
| DEBT-01 | multilingual billing отсутствует на ALLOW/DEGRADED путях | orchestrator.py | 🟡 |
| DEBT-02 | vision_actual_cost() deprecated wrapper не удалён | cost_model.py | 🟡 |
| DEBT-03 | Safety Gate cost = revenue leak при DENY | economic.md §10 | 🟡 |
| DEBT-04 | gpt-oss-20b reasoning_effort на HEAVY fallback пути | model_router.py | 🟡 |
| DEBT-05 | qwen3-32b в QWEN_THINKING_DISABLED_MODELS после deprecation | model_router.py | 🟡 |
| DEBT-06 | economic.md §12: open item Jul 17 уже выполнен, не закрыт | economic.md | 🟡 |
| DEBT-07 | estimate_safety_cost() vs Pass1 no-op — зависит от MISMATCH-04 | cost_model.py | 🟡 |