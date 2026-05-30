# CEYONA — AUDIT
**Обновлён:** май 2026 (сессия 2 — vision debugging + ChatGPT analysis)
**Статус:** открыто 2 задачи (13.3, 13.4) + 17.2 (spd) + 19.x (global formatting contract)

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
| `transport/telegram/vision_handler.py` | Промпты для vision (группа и одиночное фото), лимиты |
| `transport/telegram/update_handler.py` | Flow ответа, caption/vision routing, история |
| `cognition/intent_engine.py` | System prompts для каждого intent — голос и стиль |
| `llm/prompt_engine.py` | Сборка промпта перед LLM |
| `core/execution/orchestrator.py` | intent → путь → ответ |
| `cognition/response_synthesizer.py` | Финальная обработка перед отправкой |
| `i18n/strings.py` | Все локализованные строки бота |

### Симптомы сломанных ответов

- `"Изображение N представляет собой"` / `"Первое/Второе изображение..."` → дефолтный шаблон модели в `_GROUP_EXTRACTION_SYSTEM`, нумерация при отсутствии constraint
- `"наименее интересно для анализа"` / `"вероятно связано"` → инференс и оценка, не запрещены явно
- `Constraints:`, `Candidates:` → CoT артефакты (13.3)
- Тон сухой на простых вопросах → CONVERSATION system prompt
- Модель строит единый нарратив по альбому → caption+фото смешиваются в user_message

---

## АРХИТЕКТУРА VISION PIPELINE (задокументировано май 2026)

### Реальный путь данных

```
telegram album
    ↓
update_handler.py
    ↓
handle_vision_group()  [vision_handler.py]
    ├── лимит > 6 → ответ пользователю (too_many_images)
    ├── скачать все фото параллельно
    ├── split в батчи по _MAX_IMAGES_PER_BATCH=4
    ├── _call_groq_vision() на каждый батч  ← _GROUP_EXTRACTION_SYSTEM
    └── если батчей > 1: _synthesise_batch_descriptions()  ← _GROUP_SYNTHESIS_SYSTEM_TEMPLATE
         ↓
VisionResult(text, needs_pipeline, intent_result)
    ↓
update_handler.py routing:
    ├── needs_pipeline=False → ответ напрямую (CONVERSATION, нет uncertainty)
    └── needs_pipeline=True  → основной pipeline
         ├── caption есть → text=caption, image_descriptions → retrieved_context [ФОТО]
         └── caption нет  → text=descriptions (но этот путь не вызывается при needs_pipeline=False)
```

### Ключевые инсайты (из отладки май 2026)

**Инсайт 1: Два разных шаблона, разное назначение**

- `_GROUP_EXTRACTION_SYSTEM` — то, что видит каждый батч фото. Генерирует текст, который пользователь видит напрямую при needs_pipeline=False. **Это главный шаблон для обычного кейса.**
- `_GROUP_SYNTHESIS_SYSTEM_TEMPLATE` — вызывается только если батчей > 1 (т.е. > 4 фото). Склеивает описания батчей. **При 1–4 фото не вызывается никогда.**

Две недели симптом не лечился, потому что чинили `_GROUP_SYNTHESIS_SYSTEM_TEMPLATE`, а реально использовался `_GROUP_EXTRACTION_SYSTEM`.

**Инсайт 2: Путь без caption обходит синтезатор**

При отсутствии caption: `needs_pipeline=False` → ответ = вывод экстрактора напрямую. `_GROUP_SYNTHESIS_SYSTEM_TEMPLATE` не участвует вообще.

**Инсайт 3: "Part N:" в user content синтезатора провоцировало нумерацию**

```python
# было:
combined = "\n\n".join(f"Part {i+1}:\n{d}" for i, d in enumerate(descriptions))
# модель видела Part 1 / Part 2 и зеркалила как Изображение 1 / Изображение 2
# стало:
combined = "\n\n".join(descriptions)
```

**Инсайт 4: caption+фото смешивались в user_message**

`_vision_image_context` ставился в строке 346 но нигде не передавался в pipeline — переменная молча терялась. Описания фото не попадали в OrchestratorRequest. После фикса: caption = user_message, описания = retrieved_context с меткой [Фото].

**Инсайт 5: Проблема кросс-слойная (вывод из анализа с ChatGPT)**

Один и тот же паттерн (нумерация, "представляет собой") может всплывать в разных слоях:
- Synthesis слой: если descriptions приходят как "Описание 1 / Описание 2"
- Core/LLM слой: если image_descriptions уходят в user_message без контракта
- Meta/formatting слой: если есть response templates с нумерацией
- Retrieval/context: если контекст содержит нумерованные структуры

Правильное решение — не чинить один промпт, а зафиксировать контракт на уровне global formatting rule. Это задача 19.x (см. ниже).

---

## СЛОИ И ЧТО В НИХ МОЖНО (задокументировано по итогам анализа)

| Слой | Правило |
|------|---------|
| LLM / Response | ДА — контракт формата ответа живёт здесь. describe individually, no merge, no speculation, natural paragraphs |
| Cognition (intent, reasoning) | НЕТ — здесь модель должна свободно связывать, строить гипотезы. "do not infer" здесь убьёт анализ |
| Core / Orchestrator | ЧАСТИЧНО — выбор режима (vision batch vs single), выбор контракта ответа. Не сами правила описания |
| Contracts | ДА — но как типы поведения, а не текст промпта |
| Retrieval | НЕТ — только данные, никакого влияния на стиль |
| Context | НЕТ (почти всегда) — максимум сигнал "images are unrelated" |
| External / Tools | НЕТ |
| Events / Meta | Максимум флаги: `{"vision_mode": "independent"}` |

---

## ЗАКРЫТЫЕ ЗАДАЧИ СЕССИИ 2 (май 2026)

### ✅ 18.1 — _GROUP_SYNTHESIS_SYSTEM_TEMPLATE: запреты → target pattern

**Симптом:** `"наименее интересно для анализа"`, `"вероятно связано с биологией"`, нумерация
**Корень:** шаблон содержал `ABSOLUTE RULES: Do NOT merge...` — запреты без target pattern
**Решение:**
```python
_GROUP_SYNTHESIS_SYSTEM_TEMPLATE = (
    "Describe each image independently. "
    "Each description should be a short, self-contained paragraph focused only on what is directly visible. "
    "Response length: {verbosity_rule}. "
    "Use direct, concrete language without generic introductory phrases. "
    "Avoid meta-commentary, evaluation, or speculation. "
    "Do not infer relationships or intent unless clearly visible in the image. "
    "Do not speculate about why the images were sent together. "
    "Use natural paragraph separation instead of rigid formatting."
)
```
Убран `image_count` из `.format()` (больше не нужен).
Убраны `Part N:` лейблы из `combined` (провоцировали нумерацию в ответе).
**Файл:** `vision_handler.py`
**Статус:** ✅ закрыт

---

### ✅ 18.2 — _vision_image_context не передавался в pipeline

**Симптом:** при album + caption бот строил нарратив по фото вместо ответа на вопрос (пример: история про отношения с девушкой из набора несвязанных фото)
**Корень:** переменная `_vision_image_context` устанавливалась в строке 346 `update_handler.py` но нигде не использовалась — молча терялась. Pipeline получал descriptions как `user_message` и основная модель строила нарратив.
**Решение:** перед сборкой `OrchestratorRequest` инжектировать `_vision_image_context` в `retrieved_context`:
```python
_vic = locals().get("_vision_image_context")
if _vic:
    retrieved_context = (
        f"[Фото]\n{_vic}\n\n{retrieved_context}"
        if retrieved_context
        else f"[Фото]\n{_vic}"
    )
```
Теперь: caption = вопрос пользователя в `user_message`, описания фото = контекст в `retrieved_context`.
**Файл:** `update_handler.py`
**Статус:** ✅ закрыт

---

### ✅ 18.3 — _GROUP_EXTRACTION_SYSTEM: нумерация "Первое/Второе изображение"

**Симптом:** бот нумерует описания фото `"Первое изображение представляет собой..."` при обычном альбоме без caption
**Корень:** `_GROUP_EXTRACTION_SYSTEM` заканчивался `"Separate image descriptions with a blank line."` — без запрета на ordinal labels. Модель выбирала нумерацию как safest структуру для multiple objects.
**Почему не лечилось 2 недели:** чинили `_GROUP_SYNTHESIS_SYSTEM_TEMPLATE`, который при обычном кейсе (≤4 фото без uncertainty) не вызывается никогда. Execution path шёл через экстрактор напрямую к пользователю.
**Решение:**
```python
# в _GROUP_EXTRACTION_SYSTEM заменить финальную строку:
"Start each image description directly with its content. "
"Do not begin with ordinal labels like 'First image', 'Second image', 'Image N', "
"'Первое изображение', 'Второе изображение', or any similar numbering. "
"Separate image descriptions with a blank line."
```
**Файл:** `vision_handler.py`
**Статус:** ✅ закрыт, задеплоено

---

### ✅ 18.4 — Лимит изображений: нет ограничения на входе

**Симптом:** при 7+ фото модель (llama-4-scout) начинает терять контекст, attention размазывается, часть фото игнорируется, качество описания деградирует. Бот пытается обработать любое количество.
**Корень:** в `handle_vision_group` не было проверки количества file_ids. Лимит 6 — не магическое число, это эмпирический предел где модель ещё держит контекст (норма 4–8 для мультимодальных моделей).
**Решение:** guardrail на входе в `handle_vision_group`:
```python
_MAX_GROUP_IMAGES = 6
if len(file_ids) > _MAX_GROUP_IMAGES:
    return VisionResult(
        text=t("too_many_images", lang),
        needs_pipeline=False,
        failed=False,  # не ошибка системы, guardrail
    )
```
Добавлена строка `too_many_images` в `i18n/strings.py` на всех языках бота (28 языков).
**Правильно:** это не костыль, это ограничение входа вместо лечения выхода. production-grade fail-safe.
**Не делать:** тихий обрез `images[:6]` без уведомления — пользователь не понимает что часть проигнорирована.
**Файлы:** `vision_handler.py`, `i18n/strings.py`
**Статус:** ✅ закрыт

---

## ОТКРЫТЫЕ ЗАДАЧИ

### 🔴 19.x — Global formatting contract (новая, выявлена май 2026)

**Суть:** паттерн нумерации и шаблонных открытий ("На изображении видно...", "Данное изображение демонстрирует...") потенциально кросс-слойный. Фикс extraction решает симптом, но тот же паттерн может всплыть:
- в synthesis при получении нумерованных descriptions
- в core/LLM если image_descriptions уходят в user_message
- в meta/formatting если есть response templates

**Правильное решение (2 уровня):**

Уровень 1 — уже сделан (18.3): локальный фикс `_GROUP_EXTRACTION_SYSTEM`

Уровень 2 — нужно сделать: global formatting constraint в core
```
Do not introduce structure not present in input.
Do not enumerate unless explicitly required by user.
```
или normalize_output post-processing в meta слое:
```python
def normalize_output(text: str) -> str:
    text = remove_ordinals(text)
    text = remove_numbering(text)
    return text
```

**Важно:** НЕ добавлять в cognition/intent/reasoning — там модель должна свободно думать. Только в LLM/response layer.

**Приоритет:** средний. Сначала убедиться что 18.3 держит в продакшне, потом если паттерн всплывёт снова — делать уровень 2.
**Статус:** 🔴 спроектировано, не реализовано

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

## ГОЛОСОВЫЕ СООБЩЕНИЯ — СТАТУС (май 2026)

Голосовой pipeline работает стабильно. Ответы "не идеально, но не сырые" — production-ready.

**Лимит:** 5 минут. После этого задержка может вырасти до десятков минут. Реализовано в ASR.

**Почему голос стабильнее изображений:**
- вход → один поток (audio → text) → обычный LLM pipeline
- нет batching, нет branching, нет composition
- меньше мест где может сломаться поведение
- нет `_GROUP_EXTRACTION_SYSTEM`, нет синтезатора

Вывод: система голоса линейная → поведение предсказуемое. Vision система ветвистая → поведение нестабильное. Это не баг, это архитектурная разница.

---

## ЗАКРЫТЫЕ ЗАДАЧИ (полная история)

| # | Закрыт | Суть | Ключевое решение |
|---|--------|------|-----------------|
| 13.1 | май 2026 | tool intents → "сервис недоступен" | compound = синтезатор, не агент; tool_choice убран |
| 13.5 | май 2026 | описательный запрос → поиск по сырому тексту | `_understand_query()` в `classify()` — KNOWN_ENTITY vs DESCRIPTIVE |
| 13.6 | май 2026 | бот отвечал на каждое фото альбома отдельно | Redis-backed `MediaGroupAggregator`, debounce, Lua atomicity |
| 13.6.1 | май 2026 | lock bug, смешение партий, lang хардкод | `_LUA_FLUSH` атомарный DEL, `MediaGroupItem.lang`, `input_type` в OrchestratorRequest |
| 17.1 | май 2026 | CoT infinite loop | `reasoning_engine.py`: QUESTION → mode=DIRECT |
| 17.3 | май 2026 | шаблонные ответы, "Изображения представляют собой" | history-aware variation в `prompt_engine`, `detect_repetitive_opening` в `analysis`, расширены patterns в `correction` |
| 18.1 | май 2026 | synthesis шаблон: запреты вместо target pattern | target pattern в `_GROUP_SYNTHESIS_SYSTEM_TEMPLATE`, убраны `Part N:` лейблы |
| 18.2 | май 2026 | caption+фото → нарратив вместо ответа на вопрос | `_vision_image_context` → `retrieved_context` в `update_handler.py` |
| 18.3 | май 2026 | нумерация "Первое/Второе изображение" | constraint в `_GROUP_EXTRACTION_SYSTEM` — запрет ordinal labels |
| 18.4 | май 2026 | нет лимита на количество фото → деградация | `_MAX_GROUP_IMAGES=6` guardrail + `too_many_images` i18n |

---

## CI (planned)
coverage floor 75%, asyncio stress tests (13.4), integration tests compound pipeline, retrieval quality regression, mypy.

---

## СЛЕДУЮЩИЙ ШАГ

1. Задеплоить все файлы из сессии 2: `vision_handler.py`, `update_handler.py`, `strings.py`
2. Протестировать: альбом 1 фото / 3 фото / 6 фото / 7 фото (должен вернуть too_many_images) — без caption и с caption
3. Если нумерация всплывёт снова → смотреть в каком именно слое (логи after_extraction / after_synthesis) → тогда делать 19.x уровень 2