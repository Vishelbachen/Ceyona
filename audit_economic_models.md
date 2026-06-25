# Полный аудит биллинга: orchestrator.py + multi_agent_coordinator.py
Дата: 26 июня 2026

---

## Что реально происходит по каждому пути

### ALLOW путь (`_run_allow`)
```
coordination.input_tokens + output_tokens  → биллится ✅
embedding_tokens + rerank_tokens           → биллится ✅
safety_agent (coordination.safety_agent_*) → НЕ биллится ❌  (BUG-O1)
multilingual                               → биллится в webhook ✅
safety gate                                → биллится в webhook ✅
```

### DEGRADED путь (`_run_degraded`)
```
coordination.input_tokens + output_tokens  → биллится ✅
embedding_tokens + rerank_tokens           → биллится ✅
safety_agent                               → не вызывается (по архитектуре ✅)
multilingual                               → биллится в webhook ✅
safety gate                                → биллится в webhook ✅
```

### HEAVY путь (`_run_heavy`)
```
coordination.input_tokens + output_tokens  → биллится ✅
lc_transformer (qwen3.6-27b)              → биллится ✅
heavy_input_shaper (gpt-oss-20b)          → биллится, НО по Tier.GENERAL тарифу ❌  (BUG-O2)
safety_agent                               → биллится ✅
multilingual                               → биллится ✅ (baked in cost)
safety gate                                → биллится в webhook ✅
MATH verify + correct LLM вызовы          → НЕ биллятся нигде ❌  (BUG-O3)
```

---

## BUG-O1 — safety_agent не биллится на ALLOW пути

**Файлы:** `orchestrator.py` (~473-510), `multi_agent_coordinator.py` (~120-124)

`safety_agent` запускается на ALLOW пути при `use_consensus=True` (intents: CREATIVE, CODE/MATH/EXAM,
ANALYSIS, SEARCH/RECOMMENDATION — все с `use_consensus=True` в `plan_agents()`).

`coordination.safety_agent_input_tokens` / `coordination.safety_agent_output_tokens` приходят
из `CoordinationResult` заполненными, но в `_run_allow`:

1. В `actual_cost()` не передаются
2. В `OrchestratorResult` не прокидываются (поля остаются 0)
3. В webhook `result.safety_agent_input_tokens = 0` → не биллятся

**Модель:** `gpt-oss-safeguard-20b` ($0.075 input / $0.30 output per 1M)
**Это реальный revenue miss на всех consensus-путях.**

**Фикс в `_run_allow`:**
```python
from core.kernel.cost_model import actual_safety_cost as _actual_safety_cost
_sa_cost = _actual_safety_cost(
    pass1_tokens=0,
    pass2_tokens=0,
    safeguard_tokens=coordination.safety_agent_input_tokens,
    safeguard_output_tokens=coordination.safety_agent_output_tokens,
)
cost += _sa_cost

# В OrchestratorResult добавить:
safety_agent_input_tokens=coordination.safety_agent_input_tokens,
safety_agent_output_tokens=coordination.safety_agent_output_tokens,
```

---

## BUG-O2 — heavy_input_shaper биллится по Tier.GENERAL вместо Tier.FAST

**Файл:** `orchestrator.py` (~757-764)

Shaper использует `gpt-oss-20b` — это FAST tier ($0.075/$0.30 per 1M).
В коде:
```python
_shaper_cost = actual_cost(
    ...
    tier=Tier.GENERAL,   # ← НЕВЕРНО: $0.60/$3.00 per 1M
    ...
)
```

Это переплата пользователем ~8x на output за операцию shaping.
economic.md §5 явно: `heavy_input_shaper` использует `gpt-oss-20b` (FAST tier).

**Фикс:**
```python
_shaper_cost = actual_cost(
    ...
    tier=Tier.FAST,      # gpt-oss-20b = FAST tier
    ...
)
```

---

## BUG-O3 — MATH верификатор и корректор не биллятся нигде

**Файл:** `multi_agent_coordinator.py` (~207-290, ~398-416)

MATH путь (`domain_hint == MATH`) делает до **двух дополнительных LLM вызовов**:

1. `_verify_math_solution()` → `fast_agent.run()` — вызов gpt-oss-20b
2. `_correct_math_solution()` → `deep_agent.run()` — вызов qwen3.6-27b (GENERAL)

Оба возвращают `AgentResult` с `input_tokens` / `output_tokens`.
Эти токены **нигде не аккумулируются** в `CoordinationResult`.

После коррекции `primary_result = corrected` — в итоговый `CoordinationResult`
попадают только токены corrected-вызова. Токены `_verify_math_solution` теряются полностью.
Токены первоначального failed `primary_result` тоже теряются (заменяются corrected).

**Что теряется:**
- `_verify_math_solution`: fast_agent токены (gpt-oss-20b, $0.075/$0.30)
- `_correct_math_solution`: deep_agent токены (qwen3.6-27b, $0.60/$3.00) — биллится только если коррекция стала `primary_result`, иначе токены первого вызова теряются

**Фикс:** накапливать extra_input/output_tokens в `CoordinationResult`:
```python
# После MATH блока:
_math_extra_in  = 0
_math_extra_out = 0

result = await fast_agent.run(verify_messages, ...)   # verify
_math_extra_in  += result.input_tokens
_math_extra_out += result.output_tokens

corrected = await deep_agent.run(correction_messages, ...)  # correct
_math_extra_in  += corrected.input_tokens
_math_extra_out += corrected.output_tokens

# Передать в CoordinationResult как доп. поля или суммировать с primary_result.
```

---

## BUG-O4 — `"safety" in dir()` в coordinator — неверная проверка локальной переменной

**Файл:** `multi_agent_coordinator.py` (~375-376)

```python
_safety_in  = safety.input_tokens  if "safety" in dir() else 0
_safety_out = safety.output_tokens if "safety" in dir() else 0
```

`dir()` без аргументов возвращает имена в текущей области видимости, но это
**ненадёжный** способ проверки — поведение зависит от реализации Python и не гарантировано
для локальных переменных в async-функциях.

Аналогичный баг в `orchestrator.py` (~740-744):
```python
_lc_in_tok = lc_result.input_tokens if "lc_result" in dir() and lc_result.success else 0
```

**Правильная проверка:**
```python
_safety_in  = safety.input_tokens  if "safety" in locals() else 0
_safety_out = safety.output_tokens if "safety" in locals() else 0

_lc_in_tok = lc_result.input_tokens if "lc_result" in locals() and lc_result.success else 0
```

Риск: при определённых условиях (исключение внутри блока, async context switch)
`"safety" in dir()` может вернуть `True` когда `safety` не определена → `NameError`,
или `False` когда определена → молчаливый 0 (потеря billing).

---

## BUG-O5 — fallback агент: токены primary (failed) агента теряются

**Файл:** `multi_agent_coordinator.py` (~455-475)

Когда primary агент упал и fallback успешен:
```python
return CoordinationResult(
    input_tokens=fallback_result.input_tokens,
    output_tokens=fallback_result.output_tokens,
    ...
)
```

Токены упавшего primary агента (`primary_result.input_tokens`) **теряются**.
Агент выполнил вызов к Groq API — токены потрачены, но не биллятся.

**Масштаб:** зависит от частоты primary failures. При нормальной работе редко.
Но по economic.md §2: "Failed calls that returned no output → NOT billed."
Вопрос: если primary вернул `success=False` с пустым `text` — были ли реально
потрачены токены на вызов? Нужно проверить что возвращает Groq при ошибке.
Если Groq вернул ответ но агент его отклонил (пустой text) — токены потрачены.
Если Groq упал с network error — токены не потрачены.

---

## Сводка по оркестратору

| # | Проблема | Путь | Модель | Приоритет |
|---|---|---|---|---|
| BUG-O1 | safety_agent не биллится на ALLOW (consensus) | ALLOW | gpt-oss-safeguard-20b | 🔴 |
| BUG-O2 | shaper биллится по GENERAL вместо FAST | HEAVY | gpt-oss-20b | 🔴 |
| BUG-O3 | MATH verify + correct LLM вызовы не биллятся | ALLOW/HEAVY | gpt-oss-20b + qwen3.6-27b | 🔴 |
| BUG-O4 | `"safety" in dir()` вместо `locals()` | ALLOW/HEAVY | — | 🟠 |
| BUG-O5 | Токены failed primary агента теряются | ALLOW/DEGRADED/HEAVY | любая | 🟡 |

---

## Что действительно учтено правильно

- LLM токены основного агента (все пути) ✅
- lc_transformer на HEAVY ✅
- safety_agent на HEAVY ✅
- Safety Gate (оба пасса) через webhook ✅
- Multilingual через webhook (ALLOW/DEGRADED) + baked in (HEAVY) ✅
- embedding + rerank ✅
- resolved_model логируется ✅