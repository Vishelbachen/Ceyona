# CEYONA — AUDIT
**Обновлён:** май 2026
**Статус:** открыто 3 задачи (13.3, 13.4, 17.2) + текущая 18.x (vision synthesis)

---

## ПРИНЦИП — ЧИТАТЬ ПЕРВЫМ

**Пользователь видит только ответ бота. Не архитектуру, не pipeline — только ответ.**
Целевой уровень: Claude / ChatGPT — живой, прямой, без роботизации.

**Без костылей.** Каждое решение — правильное и масштабируемое с первого раза. Запрещающие строки в промпте — не решение, это whack-a-mole: уберёшь одно — вылезет синоним. Правильный подход: задать target pattern (как должен выглядеть правильный ответ), а не список запретов.

**Критерий изменения:** стал ли ответ бота лучше или хуже. Если хуже — откат, даже если изменение архитектурно красиво.

**Масштаб:** 100+ файлов. Не переписывать код без причины. Минимальное изменение с максимальным эффектом.

---

## ФАЙЛЫ, ОПРЕДЕЛЯЮЩИЕ КАЧЕСТВО ОТВЕТОВ

| Файл | Что решает |
|------|-----------|
| `transport/telegram/vision_handler.py` | Промпты для vision (группа и одиночное фото) |
| `cognition/intent_engine.py` | System prompts для каждого intent — голос и стиль |
| `transport/telegram/update_handler.py` | Flow ответа, история |
| `llm/prompt_engine.py` | Сборка промпта перед LLM |
| `core/execution/orchestrator.py` | intent → путь → ответ |
| `cognition/response_synthesizer.py` | Финальная обработка перед отправкой |

### Симптомы сломанных ответов

- `"Изображение представляет собой"` / `"The image shows"` → дефолтный шаблон модели, нужен target pattern в промпте
- `"наименее интересно для анализа"` / `"вероятно связано"` → инференс и оценка, не запрещены явно
- `Constraints:`, `Candidates:` → CoT артефакты (13.3)
- Нумерация `Изображение 1... 2... 3...` → поведение по умолчанию при 10 объектах без target pattern
- Тон сухой на простых вопросах → CONVERSATION system prompt

---

## ОТКРЫТЫЕ ЗАДАЧИ

### 🔴 18.x — Vision synthesis: модель оценивает и инферирует (ТЕКУЩАЯ)

**Симптом (продакшн, май 2026):**
- `"наименее интересно для анализа"` — оценка вместо описания
- `"вероятно имеет отношение к теме изменчивости в биологии"` — инференс по контексту альбома
- `"Изображение 3 представляет собой..."` — дефолтный шаблон + нумерация

**Корень:** `_GROUP_SYNTHESIS_SYSTEM_TEMPLATE` содержал запреты (`Do not merge`, `Do not infer`), но не задавал target pattern. Модель при 10 разнородных фото выбирала safest формат — нумерацию и шаблонные открытия. Запреты не работают системно — модель находит обходные формулировки.

**Решение (май 2026) — target pattern вместо запретов:**

```python
# vision_handler.py — _GROUP_SYNTHESIS_SYSTEM_TEMPLATE
"Describe each image independently. "
"Each description should be a short, self-contained paragraph focused only on what is directly visible. "
"Use direct, concrete language without generic introductory phrases. "
"Avoid meta-commentary, evaluation, or speculation. "
"Do not infer relationships or intent unless clearly visible in the image. "
"Use natural paragraph separation instead of rigid formatting."
```

**Что изменилось:**
- Убрано: `Synthesise them into one clear natural response` (форсировал нарратив)
- Убрано: `Do not list images separately` (запрет)
- Добавлено: позитивный контракт — каждое фото = самостоятельный абзац, прямой язык, без вводных фраз

**Файл:** `transport/telegram/vision_handler.py`

**Статус:** ⚠️ Задеплоить, наблюдать. Если `"представляет собой"` продолжает появляться — проверить `_GROUP_EXTRACTION_SYSTEM` (экстрактор тоже может генерировать шаблонные описания, которые синтезатор транслирует).

---

### 🟡 13.3 — CoT артефакты (остаточные случаи)

**Симптом:** `Constraints:`, `Candidates:`, `Verification table` в ответе.
**Причина:** `_strip_cot_artifacts()` не покрывает путь vision → MATH/ANALYSIS classification.
**Файлы:** `cognition/response_synthesizer.py`, `transport/telegram/vision_handler.py`

---

### 🟡 13.4 — Classifier теряет контекст на follow-up

**Симптом:** `"Вот, нашла"` → CONVERSATION вместо правильного intent.
**Причина:** `_llm_pre_classify` получает только `text[:500]` без истории.
**Частично закрыт:** history context добавлен для коротких сообщений (≤8 слов).
**Осталось:** asyncio stress tests.
**Файл:** `cognition/intent_engine.py` → `_llm_pre_classify`

---

### 🟡 17.2 — TruthMode как flag, не verification layer

**Симптом:** TruthMode меняет стиль промпта, но не проверяет факты.
**Правильное решение:** `truth_check(answer, retrieval_context) -> float` в `execution_policy_kernel.py`. Retrieval = кандидаты, LLM = генератор, truth_check = судья.
**Не делать:** не создавать новые модули — это замена файлов, не решение.
**Статус:** спроектировано, реализация после стабилизации vision.

---

### 🟢 13.7 — Грузинский i18n fallback

**Симптом:** вопрос на грузинском → `"уточните вопрос"` вместо `"технический сбой"`.
**Файл:** `i18n/strings.py`, ключ `search_unavailable`, lang `ka`.

---

## ЗАКРЫТЫЕ ЗАДАЧИ (краткая история)

| # | Закрыт | Суть | Ключевое решение |
|---|--------|------|-----------------|
| 13.1 | май 2026 | tool intents → "сервис недоступен" | compound = синтезатор, не агент; tool_choice убран |
| 13.5 | май 2026 | описательный запрос → поиск по сырому тексту | `_understand_query()` в `classify()` — KNOWN_ENTITY vs DESCRIPTIVE |
| 13.6 | май 2026 | бот отвечал на каждое фото альбома отдельно | Redis-backed `MediaGroupAggregator`, debounce, Lua atomicity |
| 13.6.1 | май 2026 | lock bug, смешение партий, lang хардкод | `_LUA_FLUSH` атомарный DEL, `MediaGroupItem.lang`, `input_type` в OrchestratorRequest |
| 17.1 | май 2026 | CoT infinite loop | `reasoning_engine.py`: QUESTION → mode=DIRECT |
| 17.3 | май 2026 | шаблонные ответы, "Изображения представляют собой" | history-aware variation в `prompt_engine`, `detect_repetitive_opening` в `analysis`, расширены patterns в `correction` |

---

## CI (planned)
coverage floor 75%, asyncio stress tests (13.4), integration tests compound pipeline, retrieval quality regression, mypy.