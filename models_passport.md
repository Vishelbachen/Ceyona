# CEYONA — MODEL ENGINEERING PASSPORT
Version: 10.0 — Certification Architecture
Status: Living validation document
Supersedes: models.md §27 (per-model behavioral characteristics)

**⚠️ СТАТУС DEPRECATED МОДЕЛЕЙ (June 20, 2026):**
Актуальность информации о выводе 4 моделей подтверждена **5 раз** (последнее — Jun 20, 2026, скрин Groq API).
Модели присутствуют в `available_models` сейчас, но выводятся по расписанию:
- `qwen/qwen3-32b` → Jul 17, 2026
- `meta-llama/llama-4-scout-17b-16e-instruct` → Jul 17, 2026
- `llama-3.1-8b-instant` → Aug 16, 2026
- `llama-3.3-70b-versatile` → Aug 16, 2026

Новая модель в Groq: `qwen/qwen3.6-27b` (Preview, доступна с Apr 2026).
Статус: присутствует в `available_models`, цена на Groq не опубликована официально.

Этот документ определяет:
- контракт каждой роли и реальную нагрузку в токенах
- критерии оценки моделей с указанием источника
- профиль каждой модели (известное / требует теста)
- план тестов с измеримыми pass/fail критериями
- матрицу назначений (заполняется после тестов)

Документ НЕ определяет: оркестрацию, EPK, экономику, роутинг.
Назначение модели в роль → только после прохождения тестов этой роли.

---

## ЧАСТЬ 1 — КОНТРАКТЫ РОЛЕЙ

### ROLE: FAST

**Назначение:** минимально достаточный ответ при максимальной скорости.
Короткий разговорный вывод, DEGRADED_MODE fallback, heavy_input_shaper utility.

**Контракт:**
- Ответ ≤ 2–3 сек end-to-end
- Задачи низкой сложности только
- Никогда: глубокий анализ, тяжёлые инструменты, длинный вывод
- Работает при DEGRADED_MODE (reduced balance)
- SHAPER_MODEL использует эту же модель как утилиту (не как Fast Tier)

**Реальная нагрузка:**

| Компонент | Типично | Worst case |
|---|---|---|
| System prompt (PERSONA_RULE_FAST + FORMAT) | ~212 tokens | ~250 tokens |
| Conversation history | ~300–800 tokens | ~1500 tokens |
| Retrieved context | 0 (DEGRADED — retrieval отключён) | 0 |
| **Итого входящий контекст** | **~500–1000 tokens** | **~1750 tokens** |
| Ожидаемый output | 50–200 tokens | 500 tokens |

**Ключевые требования (по убыванию приоритета):**
1. Скорость (TPS на Groq) — 40%
2. Instruction Stability на коротком промпте (~212 tokens) — 30%
3. Базовое качество диалога, удержание персоны — 20%
4. Стоимость — 10%

---

### ROLE: GENERAL

**Назначение:** универсальная модель среднего уровня. Основная рабочая лошадка системы.
Обязана стабильно удерживать длинный системный промпт, качественно работать
с tool calling, структурированным выводом и диалогом.
Все сценарии (диалог, reasoning, код, math, поиск, JSON, мультиязычный диалог)
являются следствием этих базовых свойств, а не отдельными требованиями к модели.

**Контракт:**
- Стабильное следование ~12 условным поведенческим правилам
- Удержание персоны после tool вызовов и при большом контексте
- Tool calling: function calling, structured output, JSON
- Мультиязычный диалог (RU/EN/AR и другие)
- Никогда: глубокий многошаговый анализ (→ HEAVY), vision (→ VISION роль)

**Реальная нагрузка:**

| Компонент | Типично | Worst case |
|---|---|---|
| System prompt (PERSONA_RULE_GENERAL + все правила) | ~800 tokens | ~1000 tokens |
| Conversation history (12–15 пар) | ~1000–3000 tokens | ~5000 tokens |
| Retrieved context (поиск / инструменты) | ~500–2000 tokens | ~6000 tokens |
| **Итого входящий контекст** | **~2300–5800 tokens** | **~12000+ tokens** |
| Ожидаемый output | 100–500 tokens | 3072 tokens |

**Ключевые требования (по убыванию приоритета):**
1. Instruction Stability на длинном промпте с условной логикой — 35%
2. Качество reasoning и диалога — 25%
3. Tool calling надёжность — 20%
4. Мультиязычность — 10%
5. Скорость — 5%
6. Стоимость — 5%

---

### ROLE: HEAVY

**Назначение:** глубокий многошаговый анализ, консенсус-арбитр.
Используется только при EPK = HEAVY_REQUIRED.

**Контракт:**
- Глубокое рассуждение в несколько шагов
- Роль консенсус-арбитра (mutex с HEAVY_REQUIRED)
- Скорость не критична
- Удержание точности и ограничений при большом контексте

**Реальная нагрузка:**

| Компонент | Типично | Worst case |
|---|---|---|
| System prompt (PERSONA_RULE_HEAVY) | ~1000 tokens | ~1200 tokens |
| Conversation history | ~2000–4000 tokens | ~8000 tokens |
| Retrieved context + reasoning context | ~2000–5000 tokens | ~15000 tokens |
| **Итого входящий контекст** | **~5000–10000 tokens** | **~24000+ tokens** |
| Ожидаемый output | 500–2000 tokens | 6144 tokens |

**Ключевые требования (по убыванию приоритета):**
1. Качество reasoning — 50%
2. Instruction Stability при большом контексте — 30%
3. Стоимость — 15%
4. Скорость — 5%

---

### ROLE: VISION

**Назначение:** извлечение структурированных данных из изображений.
Независимая роль. Не разговорная.

**Контракт:**
- Реальное понимание изображений (не просто поддержка vision API)
- Структурированный вывод (JSON / текстовое извлечение)
- Короткий промпт, ограниченный output
- Вызывается вне EPK DAG (vision_handler.py) — отдельный ingress путь

**Реальная нагрузка:**

| Компонент | Типично | Worst case |
|---|---|---|
| System prompt (extraction only) | ~100–200 tokens | ~300 tokens |
| Image tokens | ~500–2000 tokens | ~5000 tokens |
| **Итого входящий контекст** | **~600–2200 tokens** | **~5300 tokens** |
| Ожидаемый output | 50–300 tokens | 1024 tokens (FAST tier limit) |

**Ключевые требования (по убыванию приоритета):**
1. Качество понимания изображений — 50%
2. Точность structured output — 30%
3. Скорость — 15%
4. Стоимость — 5%

---

### ROLE: LONG_CONTEXT

**Назначение:** трансформация и обработка документов > 32K токенов.
Независимая роль. Активируется по длине контекста, не по intent.

**Контракт:**
- Стабильное поведение без галлюцинаций на большом контексте
- Instruction Stability при >32K входящем контексте
- Vision не требуется

**Реальная нагрузка:**

| Компонент | Типично | Worst case |
|---|---|---|
| System prompt | ~300–500 tokens | ~600 tokens |
| Document context | ~32000–100000 tokens | ~200000+ tokens |
| **Итого входящий контекст** | **~32300–100500 tokens** | **~200600+ tokens** |
| Ожидаемый output | 500–3000 tokens | 8000 tokens |

**Ключевые требования (по убыванию приоритета):**
1. Качество на длинном контексте без деградации — 50%
2. Instruction Stability при >32K — 30%
3. Стоимость — 15%
4. Скорость — 5%

---

### ROLE: MULTILINGUAL

**Назначение:** нормализация нелатинских языков (не арабский — это allam-2-7b).
Независимая роль, отдельный маршрут. Утилитарная задача.
Может выполняться той же моделью что GENERAL, но контракт независим.

**Контракт:**
- Качественная нормализация нелатинских скриптов
- Короткий промпт, быстрый вывод
- Не разговорная роль

**Реальная нагрузка:**

| Компонент | Типично | Worst case |
|---|---|---|
| System prompt | ~50–100 tokens | ~150 tokens |
| Input text | ~50–500 tokens | ~1000 tokens |
| **Итого** | **~100–600 tokens** | **~1150 tokens** |
| Ожидаемый output | 50–500 tokens | ~1000 tokens |

**Ключевые требования (по убыванию приоритета):**
1. Качество нелатинских языков — 60%
2. Скорость — 25%
3. Стоимость — 15%

---

## ЧАСТЬ 2 — ПРОФИЛИ МОДЕЛЕЙ

Источники данных:
- ✅ **DOC** — официальная документация Groq / OpenAI / Qwen
- ✅ **BENCH** — независимые публичные бенчмарки
- ⚠️ **TEST** — требует собственных тестов на сценариях Ceyona

---

### MODEL: openai/gpt-oss-20b

| Характеристика | Значение | Источник |
|---|---|---|
| Архитектура | MoE, 21B total / 3.6B active | ✅ DOC |
| TPS на Groq | ~1000 | ✅ DOC |
| Контекст | 131K | ✅ DOC |
| Max output | 65K | ✅ DOC |
| Vision | ❌ | ✅ DOC |
| Tool use | ✅ | ✅ DOC |
| JSON/Structured output | ✅ | ✅ DOC |
| Reasoning mode | ✅ (low/medium/high) | ✅ DOC |
| Мультиязычность | MMMLU 75.7% | ✅ BENCH |
| Coding | SWE-bench 60.7%, LiveCodeBench 77.7% | ✅ BENCH |
| Math | AIME 98.7% | ✅ BENCH |
| Стоимость input | $0.075 / 1M tokens | ✅ DOC |
| Стоимость output | $0.30 / 1M tokens | ✅ DOC |
| Статус Groq | Production ✅ | ✅ DOC |
| **Instruction Stability (короткий промпт)** | **[не измерено]** | ⚠️ TEST |
| **Instruction Stability (длинный промпт ~800 tok)** | **[не измерено]** | ⚠️ TEST |
| **Instruction Stability после tool calls** | **[не измерено]** | ⚠️ TEST |
| **Persona Retention (Ceyona prompt)** | **[не измерено]** | ⚠️ TEST |
| **Hallucination Rate при нехватке данных** | **[не измерено]** | ⚠️ TEST |
| **Multilingual quality RU/DE/PL/etc** | **[не измерено]** | ⚠️ TEST |

**Известные сильные стороны:** самая высокая скорость на Groq (1000 TPS), исключительный math (AIME 98.7%), сильный coding, дешевле gpt-oss-120b в 4x по output.
**Известные слабости:** нет vision; обучен преимущественно на английском (STEM фокус); multilingual — требует проверки на Ceyona сценариях.
**Кандидат на роли:** FAST (primary), GENERAL (кандидат), MULTILINGUAL (под вопросом).

---

### MODEL: openai/gpt-oss-120b

| Характеристика | Значение | Источник |
|---|---|---|
| Архитектура | MoE, 120B total / 5.1B active | ✅ DOC |
| TPS на Groq | ~500 | ✅ DOC |
| Контекст | 131K | ✅ DOC |
| Max output | 65K | ✅ DOC |
| Vision | ❌ | ✅ DOC |
| Tool use | ✅ | ✅ DOC |
| JSON/Structured output | ✅ | ✅ DOC |
| Reasoning mode | ✅ | ✅ DOC |
| Coding | SWE-bench ~76%, превосходит o4-mini на Codeforces | ✅ BENCH |
| Math | AIME 2024/2025 выше o4-mini | ✅ BENCH |
| General | превосходит o3-mini на MMLU и HLE | ✅ BENCH |
| Стоимость input | $0.15 / 1M tokens | ✅ DOC |
| Стоимость output | $0.60 / 1M tokens | ✅ DOC |
| Статус Groq | Production ✅ | ✅ DOC |
| **Instruction Stability (длинный промпт)** | **[не измерено]** | ⚠️ TEST |
| **Instruction Stability при >10K контексте** | **[не измерено]** | ⚠️ TEST |
| **Persona Retention на длинных ответах** | **[не измерено]** | ⚠️ TEST |
| **Качество консенсус-арбитража** | **[не измерено]** | ⚠️ TEST |

**Известные сильные стороны:** флагманский reasoning, превосходит o4-mini на coding и math, MoE — дешевле на output чем кажется по размеру.
**Известные слабости:** нет vision; медленнее gpt-oss-20b в 2x; самая высокая стоимость output в реестре ($0.60).
**Кандидат на роли:** HEAVY (primary, текущее назначение).

---

### MODEL: qwen/qwen3.6-27b

| Характеристика | Значение | Источник |
|---|---|---|
| Архитектура | Dense, 27.8B | ✅ DOC |
| TPS на Groq | ~500 | ✅ DOC |
| Контекст | 262K (native), ~1M via YaRN | ✅ DOC |
| Max output | 32K | ✅ DOC |
| Vision | ✅ (text + image input) | ✅ DOC |
| Tool use | ✅ | ✅ DOC |
| JSON/Structured output | ✅ | ✅ DOC |
| Reasoning / Thinking mode | ✅ — ОБЯЗАТЕЛЬНО отключать (`thinking: False`) | ✅ DOC |
| Мультиязычность | 201 язык | ✅ DOC |
| Coding | SWE-bench Verified 77.2% — лучший в реестре | ✅ BENCH |
| Math / Reasoning | GPQA Diamond 87.8% | ✅ BENCH |
| Стоимость input | ⚠️ НЕ ОПУБЛИКОВАНА на Groq (Jun 2026). $0.60/1M — цена Qwen API напрямую, НЕ Groq. | ✅ DOC / ⚠️ OPEN ITEM |
| Стоимость output | ⚠️ НЕ ОПУБЛИКОВАНА на Groq (Jun 2026). $3.00/1M — цена Qwen API напрямую, НЕ Groq. Groq placeholder: FAST tier ($0.05/$0.08) до официального подтверждения. | ✅ DOC / ⚠️ OPEN ITEM |
| Статус Groq | Preview ✅ | ✅ DOC |
| Дата выхода | April 22, 2026 | ✅ DOC |
| **Instruction Stability (Ceyona prompt ~800 tok)** | **[не измерено]** | ⚠️ TEST |
| **Persona Retention на длинных ответах** | **[не измерено]** | ⚠️ TEST |
| **Vision accuracy на реальных Telegram фото** | **[не измерено]** | ⚠️ TEST |
| **Multilingual quality RU/DE/PL на Ceyona сценариях** | **[не измерено]** | ⚠️ TEST |
| **Поведение при thinking: False на сложных запросах** | **[не измерено]** | ⚠️ TEST |

**Известные сильные стороны:** лучший coding в реестре (SWE-bench 77.2%), vision, 201 язык, огромный контекст (262K). Единственная модель в реестре с vision кроме llama-4-scout.
**Известные слабости:** цена на Groq неизвестна (мониторить); thinking mode обязательно отключать; dense архитектура — дороже на inference чем MoE при тех же параметрах.
**Кандидат на роли:** VISION (primary кандидат), LONG_CONTEXT (кандидат), GENERAL (под вопросом — цена неизвестна).

---

### MODEL: qwen/qwen3-32b

| Характеристика | Значение | Источник |
|---|---|---|
| TPS на Groq | ~400 | ✅ DOC |
| Контекст | 131K | ✅ DOC |
| Max output | 40K | ✅ DOC |
| Vision | ❌ | ✅ DOC |
| Tool use | ✅ | ✅ DOC |
| JSON/Structured output | ✅ | ✅ DOC |
| Reasoning / Thinking mode | ✅ — ОБЯЗАТЕЛЬНО отключать (`thinking: False`) | ✅ DOC |
| Стоимость input | $0.29 / 1M tokens | ✅ DOC |
| Стоимость output | $0.59 / 1M tokens | ✅ DOC |
| Статус Groq | Preview ⚠️ deprecated Jul 17, 2026 | ✅ DOC |

**Статус: выводится из реестра Jul 17, 2026. Не назначать в новые роли.**
Данные сохранены для сравнительного анализа.

---

### MODEL: llama-3.3-70b-versatile

| Характеристика | Значение | Источник |
|---|---|---|
| TPS на Groq | ~280 | ✅ DOC |
| Контекст | 131K | ✅ DOC |
| Max output | 32K | ✅ DOC |
| Vision | ❌ | ✅ DOC |
| Tool use | ✅ | ✅ DOC |
| JSON/Structured output | ✅ | ✅ DOC |
| Стоимость input | $0.59 / 1M tokens | ✅ DOC |
| Стоимость output | $0.79 / 1M tokens | ✅ DOC |
| Статус Groq | Production ⚠️ deprecated Aug 16, 2026 | ✅ DOC |
| **Instruction Stability (Ceyona prompt)** | задокументировано в models.md §27.2 | ✅ production опыт |
| **Persona Retention** | риск: суммирующий параграф, unsolicited advice | ✅ production опыт |

**Статус: выводится Aug 16, 2026. Задокументированный production опыт сохраняется как baseline для сравнения кандидатов.**

---

### MODEL: llama-3.1-8b-instant

| Характеристика | Значение | Источник |
|---|---|---|
| TPS на Groq | ~560 | ✅ DOC |
| Контекст | 131K | ✅ DOC |
| Max output | 131K | ✅ DOC |
| Vision | ❌ | ✅ DOC |
| Tool use | ❌ | ✅ DOC |
| JSON/Structured output | ❌ | ✅ DOC |
| Стоимость input | $0.05 / 1M tokens | ✅ DOC |
| Стоимость output | $0.08 / 1M tokens | ✅ DOC |
| Статус Groq | Production ⚠️ deprecated Aug 16, 2026 | ✅ DOC |
| **Instruction Stability** | деградирует на >3 предложениях, gender drift | ✅ production опыт |

**Статус: выводится Aug 16, 2026. Задокументированный production опыт сохраняется как baseline.**

---

### MODEL: llama-4-scout-17b-16e-instruct

| Характеристика | Значение | Источник |
|---|---|---|
| Архитектура | MoE, 17B | ✅ DOC |
| TPS на Groq | ~750 | ✅ DOC |
| Контекст | 131K (Groq limit) / 10M native | ✅ DOC |
| Max output | 8K | ✅ DOC |
| Vision | ✅ | ✅ DOC |
| Tool use | ✅ | ✅ DOC |
| JSON/Structured output | ❌ | ✅ DOC |
| Стоимость input | $0.11 / 1M tokens | ✅ DOC |
| Стоимость output | $0.34 / 1M tokens | ✅ DOC |
| Статус Groq | Preview ⚠️ deprecated Jul 17, 2026 | ✅ DOC |

**Статус: выводится Jul 17, 2026 — через 27 дней. Критический приоритет замены для VISION и LONG_CONTEXT ролей.**

---

### MODEL: groq/compound + groq/compound-mini

| Характеристика | Значение | Источник |
|---|---|---|
| Тип | Система с встроенными инструментами | ✅ DOC |
| TPS | ~450 | ✅ DOC |
| Max output | 8K — ограничение для синтеза | ✅ DOC |
| Tool use | ✅ встроенные (НЕ принимает custom tool schemas) | ✅ DOC (май 2026) |
| JSON/Structured output | ✅ | ✅ DOC |
| Vision | ❌ | ✅ DOC |
| Статус Groq | Production ✅ | ✅ DOC |
| **Instruction Stability** | **[не измерено]** | ⚠️ TEST |
| **Persona Retention после синтеза** | структурный bias к bullet lists | ✅ production опыт |

**Роль фиксирована: AGENT SYNTHESIZER (FAST path → compound-mini, GENERAL path → compound).
Не является tier-моделью. Не получает custom tools. Синтезирует уже собранный контекст.**

---

### MODEL: allam-2-7b

| Характеристика | Значение | Источник |
|---|---|---|
| Специализация | Arabic NLP | ✅ DOC |
| Роль в системе | Нормализация арабского (один вызов, три контекста) | ✅ DOC |
| Vision | ❌ | ✅ DOC |
| Статус Groq | Production ✅ | ✅ DOC |

**Роль фиксирована: MULTILINGUAL_ARABIC. Не конкурирует с другими моделями.**

---

## ЧАСТЬ 3 — ПЛАН ТЕСТОВ

### 3.0 Методология

#### Три независимых набора

Смешивать нельзя — каждый отвечает на свой вопрос.

```
Model Certification (raw)
  Вопрос:  Пригодна ли модель для этой роли?
  Что:     Прямой вызов Groq API. Без normalizer, correction, formatter.
  Когда:   При оценке нового кандидата или после триггера инвалидации.

System Regression (pipeline)
  Вопрос:  Работает ли система после изменения?
  Что:     Полный pipeline: normalizer, correction, formatter, tool calling.
  Когда:   Перед каждым релизом.

Regression Delta (diff)
  Вопрос:  Что именно изменилось относительно предыдущей certified модели?
  Что:     Те же raw-кейсы что в Certification — на старой и новой модели
           параллельно. Сравнение числовых профилей.
  Когда:   При смене модели в model_router.py.
```

**Почему нельзя смешивать:**
`output_normalizer.py` скрывает реальные дефекты модели — language leak,
source tag artifacts, vision meta-openers. Выбор модели по pipeline-результатам
означает выбор пары «модель + компенсатор». При изменении normalizer
паспорт теряет достоверность без повторного прогона.

#### Какие тесты в каком наборе

```
Model Certification (raw):
  IS-01..05, PR-01..04, HAL-F, HAL-C, DET-01..03
  JR-01, LW-01, LT-01..04, VQ-01..03, LC-01..02, ML-01..02

System Regression (pipeline):
  LT-05   — end-to-end с поиском (pipeline overhead обязателен)
  ER-01..02 — fallback и rate limit (тестируют систему, не модель)
  CS-01..02 — compound работает только внутри pipeline

Regression Delta (diff) — минимальный набор для быстрого сравнения:
  IS-01..02, PR-01..02, HAL-F, DET-01..02, JR-01, LT-04
```

#### Инвалидация паспорта роли

Срок не используется. Только события:

```
Триггеры (паспорт → STALE):
  - смена модели в _PRIMARY или _TIER_MODELS (model_router.py)
  - изменение PERSONA_RULE_* или любого правила (prompt_policy.py)
  - изменение output_normalizer.py
  - изменение correction.py
  - изменение логики tool calling или agent layer
  - изменение build_messages() в prompt_engine.py
  - обновление Groq SDK если меняет параметры вызова

Не являются триггерами:
  - изменение retrieval / reranker
  - изменение transport layer
  - изменение billing / cost_model
  - истечение времени при отсутствии изменений выше
```

#### Порядок разработки (не менять)

```
1. Зафиксировать контракты ролей        ✓ DONE (Часть 1)
2. Пронумеровать все правила            ✓ DONE (§3.1 ниже)
3. Определить критерии Pass/Fail        ✓ DONE (тесты §3.2+)
4. Разметить raw vs pipeline            ✓ DONE (выше)
5. Написать test fixtures               ← NEXT (после фиксации критериев)
6. Запустить Model Certification        ← после fixtures
7. Заполнить паспорта ролей             ← после прогона (Часть 4)
```

Test fixtures пишутся после того как зафиксированы критерии — никогда
наоборот. Если сначала запросы, потом критерии под них — это проверка
ожиданий разработчика, а не поведения модели.

---

### 3.1 Правила — нумерованный реестр

Каждое правило имеет ID. Тесты ссылаются на ID.
Нарушение в паспорте роли фиксируется по ID: «нарушение P-06 в запросе 14».

```
Источник: prompt_policy.py + PERSONA_RULE_GENERAL / FAST / HEAVY

ГРУППА P — Persona (из PERSONA_RULE_*)
  P-01  Gender agreement: женский род во всех грамматических формах
  P-02  Formal register: Вы в RU, formal в других языках
         (исключение: пользователь первым переходит на ты)
  P-03  No enthusiasm markers: никаких «Конечно!», «Отлично!», «С удовольствием!»
  P-04  Answer-first: первое слово ответа — часть ответа, не вступление
  P-05  No unsolicited expansion: отвечать ровно на вопрос, не расширять
  P-06  No naming emotions: не называть эмоциональное состояние пользователя
  P-07  No unsolicited advice: не добавлять советы, предупреждения, выводы
  P-08  One question out: если задаёт вопрос — только один за раз
  P-09  One-sentence refusal: отказ — одно предложение, без объяснений и извинений
  P-10  Tone follows topic: тон меняется под тему, характер — нет
  P-11  No helpdesk register: не звучать как служба поддержки

ГРУППА F — Formatting (из FORMAT_RULES + VARIATION_RULE)
  F-01  No markdown tables
  F-02  No markdown headers
  F-03  No bold
  F-04  Plain text, numbered lists или dashes
  F-05  Vary sentence openings

ГРУППА H — History (из NO_CARRYOVER_RULE)
  H-01  No topic carryover: не переносить факты из несвязанной темы
  H-02  Ignore irrelevant history: нерелевантная история игнорируется,
         не смешивается с текущей темой

ГРУППА G — Grounding (из VERIFIED_FACTS_RULE + NO_CUTOFF_RULE)
  G-01  Prefer retrieved facts над памятью модели при наличии контекста
  G-02  No invented freshness: не придумывать актуальность, цены, доступность
  G-03  Admit uncertainty: если факт не подтверждён — сказать прямо

ИТОГО: 21 правило

Применимость по тирам:
  FAST:   P-01, P-02, P-03, P-04, P-09, F-01..05
  GENERAL: все (P-01..11, F-01..05, H-01..02, G-01..03)
  HEAVY:  все + H-03 (acknowledge emotional context в одном предложении перед ответом)
```

---

### IS — Instruction Stability

**IS-01 — Короткий промпт, базовые правила**
```
Промпт: PERSONA_RULE_FAST (~212 tokens)
Задача: 10 разнообразных коротких запросов на RU/EN
Pass: gender agreement соблюдён во всех ответах,
      нет филлеров, нет enthusiasm markers,
      формальное обращение (Вы) сохранено
Fail: хотя бы одно нарушение из перечисленных
Кандидаты: все претенденты на FAST
```

**IS-02 — Длинный промпт, условная логика**
```
Набор:  Model Certification (raw)
Промпт: PERSONA_RULE_GENERAL + все правила (~800 tokens)
Задача: 20 запросов включая эмоциональные, технические,
        многовопросные, поисковые
Правила: P-01..11, F-01..05, H-01..02, G-01..03 (21 правило)
Pass: нарушений ≤ 2 из 420 (20 запросов × 21 правило),
      ни одно правило не нарушено повторно
Fail: > 2 нарушений, или одно правило нарушено ≥ 2 раз
Фиксация: ID нарушенного правила + номер запроса
Кандидаты: все претенденты на GENERAL
```

**IS-03 — Длинный промпт + история**
```
Промпт: ~800 tokens
История: 15 пар диалога (~3000 tokens)
Задача: 10 запросов после загруженной истории
Pass: первые правила промпта (gender, формальность)
      соблюдены так же как без истории
Fail: деградация правил из первой половины промпта
Кандидаты: все претенденты на GENERAL
```

**IS-04 — Длинный промпт + tool calls**
```
Промпт: ~800 tokens
Сценарий: 5 запросов с tool вызовами (поиск, погода)
Pass: после получения tool результата персона и
      ограничения сохраняются в финальном ответе
Fail: после tool вызова модель "забывает" правила
      или переключается в другой регистр
Кандидаты: все претенденты на GENERAL
```

**IS-05 — Тест на worst case контекст**
```
Промпт: ~800 tokens
История + retrieved context: ~10000 tokens total
Задача: 5 запросов
Pass: модель не галлюцинирует, не смешивает темы,
      соблюдает NO_CARRYOVER_RULE
Fail: любое смешение тем или галлюцинация
Кандидаты: претенденты на GENERAL и HEAVY
```

---

### PR — Persona Retention

**PR-01 — Базовая персона**
```
Pass: Ceyona отвечает от женского лица во всех ответах
Fail: мужские формы глаголов или прилагательных
Кандидаты: все
```

**PR-02 — Тон под давлением**
```
Сценарий: грубые/нетерпеливые сообщения от пользователя
Pass: тон остаётся ровным, нет извинений, нет изменения
      регистра, нет submission
Fail: модель "мягчает" или переключается в helpdesk режим
Кандидаты: претенденты на GENERAL
```

**PR-03 — Длинный ответ**
```
Задача: запросы требующие ответа >500 tokens
Pass: тон и ограничения сохраняются до конца ответа
Fail: shift в academic/formal регистр во второй половине
Кандидаты: претенденты на GENERAL и HEAVY
```

---

### VQ — Vision Quality

**VQ-01 — Базовое извлечение**
```
Вход: 10 реальных Telegram фото — по 2–3 каждого типа:
      скриншот текста, карта/схема, живое фото объекта, документ, QR/штрихкод
Pass: структурированное извлечение корректно для ≥8/10 общих,
      И ≥1/2 в каждом типе (нет полного провала по классу)
Fail: < 8/10 суммарно, или 0/2 в любом из типов,
      или галлюцинация (уверенное описание несуществующего контента)
Кандидаты: претенденты на VISION
```

**VQ-02 — Структурированный JSON вывод**
```
Задача: извлечь данные из изображения в заданную JSON схему
Pass: корректный JSON без дополнительного текста в ≥9/10
Fail: < 9/10 или невалидный JSON
Кандидаты: претенденты на VISION
```

**VQ-03 — Низкокачественные изображения**
```
Вход: 5 размытых / плохо освещённых фото
Pass: модель честно сообщает о низком качестве,
      не галлюцинирует детали
Fail: галлюцинирует содержимое нечёткого изображения
Кандидаты: претенденты на VISION
```

---

### LC — Long Context

**LC-01 — Базовый длинный документ**
```
Вход: документ ~40K tokens
Задача: суммаризация + извлечение конкретных фактов
Pass: факты корректны, нет галлюцинаций,
      нет смешения с другими источниками
Fail: любая галлюцинация или ошибочный факт
Кандидаты: претенденты на LONG_CONTEXT
```

**LC-02 — Стабильность на >100K контексте**
```
Вход: документ ~100K tokens (тот же тип что LC-01, другой документ)
Задача: те же задачи что LC-01
Pass: точность извлечения фактов ≥ 90% от результата LC-01,
      нет новых галлюцинаций относительно LC-01 результата
Fail: деградация точности > 10% vs LC-01, или новые галлюцинации
Кандидаты: претенденты на LONG_CONTEXT
```

---

### ML — Multilingual Quality

**ML-01 — Нелатинские языки (не арабский)**
```
Языки: RU, UK, PL, DE, JA, KO, ZH (выборка)
Задача: нормализация 10 входных текстов на каждом языке
Pass: нормализация корректна для ≥9/10 на каждом языке
Fail: < 9/10 или смешение языков в выводе
Кандидаты: претенденты на MULTILINGUAL
```

**ML-02 — Мультиязычный диалог в GENERAL сценариях**
```
Задача: 20 диалоговых запросов на RU/EN/PL/DE
Pass: ответ на языке запроса, персона сохранена,
      нет утечки английских конструкций
Fail: утечка языка или потеря персоны
Кандидаты: претенденты на GENERAL
```

---

### JR — JSON Reliability

**JR-01 — Структурированный вывод под нагрузкой**
```
Задача: 20 запросов на генерацию JSON по заданной схеме
        при полном системном промпте (~800 tokens)
Pass: валидный JSON в ≥19/20
Fail: < 19/20 или невалидный JSON при наличии промпта
Кандидаты: претенденты на GENERAL
```

---

### LT — Latency

**Методология:**
Каждый этап измеряется отдельно. Модель не виновата в задержке поиска или сети.
Все тесты запускаются при фиксированной нагрузке — иначе сравнение между кандидатами некорректно.
Метрики: медиана по 10 последовательным запросам (не min, не max).

**LT-01 — TTFT под фиксированной нагрузкой (FAST роль)**
```
Нагрузка: PERSONA_RULE_FAST (~212 tokens system) + запрос ~50 tokens
Измерение: только время до первого токена (prefill + scheduling)
Pass: медиана TTFT < 400ms
Fail: медиана TTFT > 600ms, или любой запрос > 1000ms
Кандидаты: претенденты на FAST
Примечание: TTFT зависит от длины prefill — нагрузка должна быть идентичной
            при сравнении кандидатов
```

**LT-02 — Время генерации (FAST роль)**
```
Нагрузка: та же что LT-01, ожидаемый output ~100 tokens
Измерение: время от первого до последнего токена
Pass: 100 tokens сгенерированы за < 500ms (≥ 200 TPS эффективных)
Fail: эффективный TPS < 100 на медиане
Кандидаты: претенденты на FAST
```

**LT-03 — End-to-end (FAST роль)**
```
Нагрузка: та же что LT-01
Измерение: от получения запроса до last token (TTFT + генерация)
Pass: медиана end-to-end < 2.0s
Fail: медиана > 2.5s, или любой запрос > 3.0s
Кандидаты: претенденты на FAST
Примечание: этот тест — итоговый контрактный критерий.
            LT-01 и LT-02 диагностируют где именно проблема если LT-03 провален.
```

**LT-04 — TTFT под нагрузкой GENERAL**
```
Нагрузка: PERSONA_RULE_GENERAL (~800 tokens) + история ~2000 tokens + запрос ~100 tokens
Измерение: время до первого токена
Pass: медиана TTFT < 800ms
Fail: медиана TTFT > 1200ms
Кандидаты: претенденты на GENERAL
Примечание: длинный prefill — TTFT здесь объективно выше чем FAST.
            Важно: пользователь видит начало потока, не ждёт полного ответа.
```

**LT-05 — End-to-end с поиском (GENERAL, search intent)**
```
Нагрузка: полный pipeline — retrieval + prompt assembly + LLM + synthesizer
Измерение: от запроса до доставки ответа (включает поиск, постобработку)
Цель: не для pass/fail модели, а для baseline пайплайна
Фиксировать: TTFT_llm, generation_time, retrieval_time, postprocess_time отдельно
Pass: LLM-компонент не виновен если end-to-end > 5s при retrieval_time > 3s
Кандидаты: все претенденты на GENERAL
```

---

### HAL — Hallucination

**Принципиальное различие двух типов:**
- HAL-F: модель создаёт факт которого не существует (factual invention)
- HAL-C: модель искажает контент который существует в контексте/истории (context distortion)
Это разные механизмы — диагностируются и митигируются по-разному.

**HAL-F — Выдумывание фактов при отсутствии данных**
```
Сценарий: 10 вопросов о конкретных фактах (цены, адреса, расписания,
          имена, даты), на которые нет данных ни в истории ни в контексте
Pass: модель говорит "не знаю" / предлагает поиск в ≥9/10,
      не называет конкретных придуманных значений
Fail: конкретный придуманный факт (число, адрес, имя) в любом из 10
Кандидаты: претенденты на GENERAL и HEAVY
Примечание: "Там, вероятно, есть кафе" — не провал.
            "Кафе работает с 9:00, адрес — ул. Ленина 5" без источника — провал.
```

**HAL-C — Искажение контекста и истории диалога**
```
Сценарий A — искажение истории:
  Диалог из 10 пар, в котором пользователь упоминал конкретный факт (X).
  Затем запрос: "Ты помнишь что я говорил про X?"
  Pass: модель воспроизводит X корректно или говорит что не уверена
  Fail: модель приписывает пользователю фразу которой не было

Сценарий B — cross-contamination retrieved context:
  Retrieved context содержит два источника: A (Прага) и B (Варшава).
  Запрос касается только Праги.
  Pass: ответ содержит только данные из источника A
  Fail: в ответе про Прагу появляются факты из источника B (Варшава)

Запросов: 10 на каждый сценарий
Pass суммарно: ≤ 1 нарушение из 20
Fail: ≥ 2 нарушений, или любое нарушение типа B (cross-contamination)
Кандидаты: претенденты на GENERAL и HEAVY
```

---

### CS — Compound Synthesis

**CS-01 — Anti-enumeration под нагрузкой**
```
Промпт: FORMAT_RULES с явным запретом bullet points и headers
Retrieved context: 3–5 поисковых результата (смешанный контент)
Задача: синтезировать в связный прозаический ответ, 10 запросов
Pass: ни одного bullet, ни одного markdown header в ≥9/10 ответах
Fail: bullet или header в ≥2 ответах
Кандидаты: groq/compound, groq/compound-mini
```

**CS-02 — Языковая чистота синтеза**
```
Сценарий: retrieved context на EN, запрос на RU
Задача: 10 запросов
Pass: ответ на RU, английские термины из источников переведены
      или транслитерированы, нет raw EN фраз в середине RU текста
Fail: английские конструкции из retrieved context в RU ответе в ≥2/10
Кандидаты: groq/compound, groq/compound-mini
Примечание: output_normalizer.py частично компенсирует — тест показывает
            насколько сильно он нагружен
```

---

### ER — Error Resilience

**ER-01 — Fallback при пустом/обрезанном ответе primary**
```
Сценарий: primary возвращает пустую строку или < 10 tokens
Pass: система активирует fallback, пользователь получает валидный ответ,
      без видимой ошибки
Fail: пустой ответ или raw ошибка доходит до пользователя
Кандидаты: все пары primary/fallback после назначения
```

**ER-02 — Rate limit (429) на primary**
```
Сценарий: симуляция 429 от Groq на primary модели
Измерение: время до получения ответа от fallback
Pass: fallback отвечает в пределах + 500ms от нормального TTFT,
      пользователь получает ответ (degraded quality допустимо)
Fail: timeout > 5s, или ошибка к пользователю, или молчание
Кандидаты: все пары primary/fallback
```

---

### LW — Language Switching

**LW-01 — Переключение языка в диалоге**
```
Сценарий: 10 диалогов с mid-session сменой языка
          (EN→RU, RU→EN, RU→DE, AR→EN — по 2–3 каждого)
Pass: модель немедленно переключается на язык последнего сообщения,
      персона сохранена, нет остатка предыдущего языка в ответе
Fail: продолжает отвечать на предыдущем языке,
      или мешает языки в одном ответе, или теряет персону при переключении
Кандидаты: претенденты на GENERAL
```

---

### DET — Determinism

**Назначение:** выявить модели с нестабильным поведением под одинаковыми условиями.
При temperature=0 полная посимвольная идентичность не гарантируется
из-за параллельного floating point на GPU — это нормально.
Тест проверяет **поведенческую стабильность**, не текстовое совпадение.

**DET-01 — Стабильность JSON вывода**
```
Условие: temperature=0, один и тот же запрос на JSON генерацию,
         полный системный промпт (~800 tokens)
Запусков: 20
Проверяется:
  - структура JSON идентична во всех 20 (те же ключи, те же типы)
  - значения семантически эквивалентны (не посимвольно)
  - нет запусков с невалидным JSON
Pass: структура стабильна в ≥19/20, невалидного JSON нет
Fail: структура меняется в ≥2/20, или любой невалидный JSON
Кандидаты: претенденты на GENERAL (обязательно qwen3.6-27b —
           known risk: thinking=False иногда прорывается в CoT)
```

**DET-02 — Стабильность соблюдения правил**
```
Условие: temperature=0, один запрос активирующий условное правило
         (например: эмоциональный запрос → правило "не добавлять советы"),
         полный системный промпт
Запусков: 20
Проверяется: правило соблюдается во всех 20 запусках
Pass: ≥19/20 соблюдений правила
Fail: правило нарушено в ≥2/20 запусках
Кандидаты: все претенденты на GENERAL
Примечание: нарушение на 12-м запуске при идеальных первых 11 —
            именно то что этот тест должен поймать
```

**DET-03 — Стабильность персоны**
```
Условие: temperature=0, нейтральный запрос средней длины,
         полный системный промпт
Запусков: 20
Проверяется: gender agreement (женский род) во всех 20,
             нет enthusiasm markers ни в одном
Pass: ≥19/20 без нарушений
Fail: нарушение рода или маркер в ≥2/20
Кандидаты: все претенденты на GENERAL и FAST
```

---

### PR-04 — Тон при фамильярности пользователя

**PR-04 — Фамильярность и смена регистра пользователем**
```
Сценарий: пользователь переходит на неформальный тон —
          уменьшительные обращения, смайлики, переход на "ты"
Pass: Ceyona сохраняет свой регистр (Вы), не копирует тон пользователя,
      не становится подчёркнуто холодной или официальной в ответ
Fail: переход на "ты", копирование фамильярного тона,
      или резкое ужесточение тона (pendulum effect)
Кандидаты: претенденты на GENERAL
```

---

## ЧАСТЬ 4 — ПАСПОРТА РОЛЕЙ

Паспорт роли — первичный документ. Сертифицируется не модель,
а пригодность конкретной модели для конкретной роли.
Одна модель может пройти VISION и не пройти GENERAL — это нормально.

Статусы: `VALID` / `STALE` / `UNCERTIFIED`
`STALE` выставляется вручную при срабатывании триггера из §3.0.

---

### ROLE: FAST

```
Status: UNCERTIFIED
Certified model: —
Certification date: —

Components snapshot (заполнить при сертификации):
  prompt_policy.py:       commit —
  output_normalizer.py:   version —
  model_router.py:        commit —
  Groq SDK:               version —

Test results (Model Certification / raw):
  IS-01  Persona / short prompt:      —/10    —%
  PR-01  Gender agreement:            —/20    —%
  PR-03  Long output:                 —/10    —%    (note: —)
  PR-04  Familiarity:                 —/10    —%
  DET-03 Persona determinism:         —/20    —%
  LT-01  TTFT median:                 —ms           (pass < 400ms)
  LT-01  TTFT P95:                    —ms
  LT-02  Generation / 100tok:         —ms
  LT-03  End-to-end median:           —ms           (pass < 2000ms)
  LT-03  End-to-end P95:              —ms

Rules violated: —
Candidates evaluated:
  —: —

Certified: NO
```

---

### ROLE: GENERAL

```
Status: UNCERTIFIED
Certified model: —
Certification date: —

Components snapshot:
  prompt_policy.py:       commit —
  output_normalizer.py:   version —
  model_router.py:        commit —
  correction.py:          commit —
  Groq SDK:               version —

Test results (Model Certification / raw):
  IS-01  Persona / short prompt:      —/10    —%
  IS-02  Rules / long prompt:         —/420   —%    (violations: —)
  IS-03  Rules + history:             —/10    —%
  IS-04  Rules + tool calls:          —/5     —%
  IS-05  Worst case context:          —/5     —%
  PR-01  Gender agreement:            —/20    —%
  PR-02  Tone under pressure:         —/10    —%
  PR-03  Long output:                 —/10    —%    (note: —)
  PR-04  Familiarity:                 —/10    —%
  HAL-F  Factual invention:           —/10          (invented facts: —)
  HAL-C  Context distortion type A:   —/10
  HAL-C  Context distortion type B:   —/10          (any B = fail)
  DET-01 JSON structure:              —/20    —%    (drift at iter: —)
  DET-02 Rule compliance:             —/20    —%
  DET-03 Persona:                     —/20    —%
  JR-01  JSON reliability:            —/20    —%
  ML-02  Multilingual dialogue:       —/20    —%
  LW-01  Language switching:          —/10    —%
  LT-04  TTFT median:                 —ms           (pass < 800ms)
  LT-04  TTFT P95:                    —ms

Rules violated (ID + запрос): —

Candidates evaluated:
  —: —

Certified: NO
```

---

### ROLE: HEAVY

```
Status: UNCERTIFIED
Certified model: openai/gpt-oss-120b (текущее, подтверждается тестами)
Certification date: —

Components snapshot:
  prompt_policy.py:       commit —
  model_router.py:        commit —
  Groq SDK:               version —

Test results (Model Certification / raw):
  IS-05  Worst case context:          —/5     —%
  PR-03  Long output:                 —/10    —%    (note: —)
  HAL-F  Factual invention:           —/10
  HAL-C  Context distortion type B:   —/10
  DET-02 Rule compliance:             —/20    —%

Rules violated: —
Certified: NO
```

---

### ROLE: VISION

```
Status: UNCERTIFIED
⚠️ Дедлайн: Jul 17, 2026 (llama-4-scout уходит)
Certified model: —
Certification date: —

Components snapshot:
  model_router.py:        commit —
  Groq SDK:               version —

Test results (Model Certification / raw):
  VQ-01  Базовое извлечение:
    screenshot text:      —/2..3  —%
    map/diagram:          —/2..3  —%
    live photo:           —/2..3  —%
    document:             —/2..3  —%
    QR/barcode:           —/2..3  —%
    total:                —/10    —%
  VQ-02  JSON output:               —/10    —%
  VQ-03  Low quality images:        —/5     —%    (hallucinations: —)

Candidates evaluated:
  qwen/qwen3.6-27b: —

Certified: NO
```

---

### ROLE: LONG_CONTEXT

```
Status: UNCERTIFIED
⚠️ Дедлайн: Jul 17, 2026 (llama-4-scout уходит)
Certified model: —
Certification date: —

Components snapshot:
  model_router.py:        commit —
  Groq SDK:               version —

Test results (Model Certification / raw):
  LC-01  40K document:              —        (hallucinations: —)
  LC-02  100K document:             —%       (vs LC-01 baseline)

Candidates evaluated:
  qwen/qwen3.6-27b: —

Certified: NO
```

---

### ROLE: MULTILINGUAL

```
Status: UNCERTIFIED
Certified model: —
Certification date: —

Components snapshot:
  model_router.py:        commit —
  Groq SDK:               version —

Test results (Model Certification / raw):
  ML-01  Non-latin languages:
    RU:   —/10   DE:   —/10   JA:   —/10
    UK:   —/10   KO:   —/10   ZH:   —/10
    PL:   —/10
    total: —/70  —%

Candidates evaluated: —
Certified: NO
```

---

### ROLE: COMPOUND (FAST_AGENT + DEEP_AGENT)

```
Status: UNCERTIFIED
Certified models: groq/compound (DEEP_AGENT), groq/compound-mini (FAST_AGENT)
Certification date: —

Components snapshot:
  output_normalizer.py:   version —
  correction.py:          commit —
  model_router.py:        commit —

Test results (System Regression / pipeline):
  CS-01  Anti-enumeration:          —/10    —%    (bullet occurrences: —)
  CS-02  Language purity:           —/10    —%
  DET-01 JSON structure:            —/20    —%

Certified: NO
```

---

### Таблица статусов

| Роль | Модель | Статус | Дата |
|---|---|---|---|
| FAST | — | UNCERTIFIED | — |
| GENERAL | — | UNCERTIFIED | — |
| HEAVY | openai/gpt-oss-120b | UNCERTIFIED | — |
| VISION | — | UNCERTIFIED | — |
| LONG_CONTEXT | — | UNCERTIFIED | — |
| MULTILINGUAL | — | UNCERTIFIED | — |
| COMPOUND | groq/compound + mini | UNCERTIFIED | — |

**Приоритет первой сертификации:**
1. VISION + LONG_CONTEXT — дедлайн Jul 17, 2026
2. FAST — дедлайн Aug 16, 2026
3. GENERAL — дедлайн Aug 16, 2026 (самый критичный контракт)
4. HEAVY, COMPOUND, MULTILINGUAL — после основных ролей

---

## ЧАСТЬ 5 — КАНДИДАТЫ ПО РОЛЯМ

*Предварительно, до тестов. На основе известных характеристик.*

**FAST:**
- Primary кандидат: `openai/gpt-oss-20b` (1000 TPS, tool use, JSON)
- Альтернатива: `llama-3.1-8b-instant` пока не deprecated

**GENERAL:**
- Primary кандидат: `openai/gpt-oss-20b` или `qwen/qwen3.6-27b`
- Решается тестами IS-02..05 — это ключевой вопрос
- Главный критерий: Instruction Stability на Ceyona промпте

**HEAVY:**
- Primary: `openai/gpt-oss-120b` (текущее назначение, подтверждается тестами)

**VISION:**
- Единственный кандидат из активных: `qwen/qwen3.6-27b`
- `llama-4-scout` уходит Jul 17 — тестировать qwen3.6-27b немедленно

**LONG_CONTEXT:**
- Кандидат: `qwen/qwen3.6-27b` (262K контекст)
- `llama-4-scout` уходит Jul 17 — тестировать немедленно

**MULTILINGUAL:**
- Кандидат: победитель GENERAL роли (тот же маршрут, другой промпт)
- Если GENERAL = qwen3.6-27b → 201 язык, вероятно подходит
- Если GENERAL = gpt-oss-20b → требует отдельного ML-01 теста

---

*Паспорт обновляется после каждого прогона тестов.*
*Назначение модели = запись в model_router.py + статус VALID в паспорте роли.*
*Смена компонента из триггер-листа §3.0 = статус STALE + повторная сертификация.*