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
| `transport/telegram/update_handler.py` | Flow ответа, caption/vision routing, история, retrieval score filter |
| `transport/telegram/webhook.py` | Команды /balance, /start, /help, /clear, /reset_memory |
| `cognition/intent_engine.py` | System prompts для каждого intent — голос и стиль |
| `llm/prompt_engine.py` | Сборка промпта перед LLM |
| `core/execution/orchestrator.py` | intent → путь → ответ, STRICT truth gate |
| `cognition/response_synthesizer.py` | Финальная обработка перед отправкой |
| `memory/supabase_store.py` | Хранение и retrieval памяти, similarity scores |
| `retrieval/retrieval_engine.py` | Retrieval pipeline, score propagation |
| `retrieval/cache/query_cache.py` | User-scoped retrieval cache, delete_by_user |
| `i18n/strings.py` | Все локализованные строки бота |

### Симптомы сломанных ответов

- `«Из контекста можно сделать вывод»` → retrieval достаёт нерелевантную старую память, модель строит ответ по мусорному контексту
- `«Изображение N представляет собой»` / `«Первое/Второе изображение...»` → дефолтный шаблон модели в `_GROUP_EXTRACTION_SYSTEM`
- `Constraints:`, `Candidates:`, `Проверка каждого constraints:` → CoT артефакты (13.3)
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
         └── caption нет  → text=descriptions
```

---

## АРХИТЕКТУРА RETRIEVAL + TRUTH MODEL (задокументировано май 2026, сессия 3)

### Реальный путь данных retrieval

```
update_handler.py
    ↓
RetrievalEngine.retrieve(query, user_id)
    ↓
bge_engine.embed(query)           → dense embedding
    ↓
SupabaseStore.similarity_search() → MemoryRecord[] с реальным similarity score
    ↓
source_credibility.score_documents()  → pass-through (нет source_url пока)
    ↓
cross_encoder.rerank()            → отсортированные (content, score) пары
    ↓
RetrievalResult.documents[]       → RetrievedDocument(content, score)
    ↓
update_handler: score filter ≥ 0.75  → отбрасывает нерелевантные документы
    ↓
retrieved_context → OrchestratorRequest
    ↓
orchestrator: STRICT truth gate
    has_grounding = bool(retrieved_context) or bool(tool_output)
    если STRICT и нет grounding → DENY (no_grounded_data)
    ↓
LLM получает только релевантный контекст
```

### Ключевые инсайты (сессия 3)

**Инсайт 1: score 1.0 хардкод скрывал нерелевантность**

До фикса: `candidates = [(r.content, 1.0) for r in records]` — все memory записи получали максимальный score независимо от реальной релевантности. pgvector threshold 0.7 пропускал семантически близкие но контекстуально нерелевантные записи из старых сессий.

**Инсайт 2: similarity не доходил до RetrievedDocument**

`MemoryRecord` не содержал поле `similarity`. Score терялся на шаге `similarity_search() → MemoryRecord`. После фикса: `MemoryRecord.similarity` заполняется из `row.get("similarity", 1.0)` RPC ответа.

**Инсайт 3: TruthMode — confidence model, не бинарная верификация**

`truth_check(answer, retrieval_context) -> float` как отдельный verification step нереализуем без компромисса:
- Полный LLM-judge: семантически правильно, но x2 latency и x2 cost на каждый STRICT запрос — неприемлемо для Telegram-бота
- Cross-encoder как judge: не по назначению (он ранжирует релевантность, не верифицирует факты)

Правильная архитектурная позиция: truth — это не модуль, это **confidence function over the pipeline**. То что реализовано (retrieval scoring + threshold gating + STRICT gate) — это production-grade implicit truth proxy, 70-80% решения для Telegram-scale системы.

**Что реально отсутствует** (следующий уровень, не сейчас):
- contradiction detection
- memory-vs-context separation  
- time-awareness

---

## ЗАКРЫТЫЕ ЗАДАЧИ СЕССИИ 3 (май 2026)

### ✅ 20.1 — Memory contamination: нерелевантный контекст из старых сессий

**Симптом:** бот отвечал «Из контекста можно сделать вывод...» и описывал содержимое старых разговоров (аниме, «Госпожа Кагуя») вместо ответа на новый вопрос. При очищенном чате и новом вопросе retrieval доставал старые memory записи с высоким embedding score.

**Корень:** три связанных проблемы:
1. `MemoryRecord` не содержал поле `similarity` — score терялся, все записи получали `1.0`
2. `retrieved_context` собирался по наличию документов без проверки score
3. Команды `/clear` не существовало — пользователь не мог сбросить ни историю, ни память

**Решение — три файла:**

`memory/supabase_store.py`: добавлено поле `similarity: float = 1.0` в `MemoryRecord`, заполняется из `row.get("similarity", 1.0)` в `similarity_search()`

`retrieval/retrieval_engine.py`: `(r.content, 1.0)` → `(r.content, r.similarity)` — реальный score идёт в cross-encoder и далее в `RetrievedDocument.score`

`transport/telegram/update_handler.py`: фильтр перед сборкой контекста:
```python
_MIN_RETRIEVAL_SCORE = 0.75  # выше pgvector threshold 0.7
_relevant_docs = [d for d in retrieval_result.documents if d.content and d.score >= _MIN_RETRIEVAL_SCORE]
if _relevant_docs:
    retrieved_context = "\n\n".join(d.content for d in _relevant_docs)
```
Если после фильтра контекст пустой → STRICT gate в orchestrator вернёт `no_grounded_data` вместо галлюцинации.

**Файлы:** `memory/supabase_store.py`, `retrieval/retrieval_engine.py`, `transport/telegram/update_handler.py`
**Статус:** ✅ закрыт

---

### ✅ 20.2 — Команды /clear и /reset_memory отсутствовали

**Симптом:** пользователь очищал чат в Telegram UI, но `conversation_history` и `memory` в Supabase не трогались. Бот «помнил» всё из прошлых сессий.

**Корень:** обработчиков `/clear` и `/reset_memory` не было ни в `webhook.py`, ни в `update_handler.py`. `ConversationHistory.clear()` и `SupabaseStore.delete_by_user()` существовали, но нигде не вызывались.

**Решение — две команды с разной семантикой (архитектурно правильная модель):**

**Mode A — `/clear` (Session Reset):**
- Очищает `conversation_history` (Supabase)
- НЕ трогает долгосрочную память (`SupabaseStore`) — пользователь хочет новый диалог, но не терять персонализацию
- Кеш не трогается — он инфраструктура, не пользовательская идентичность
- Безопасная, частая операция

**Mode B — `/reset_memory confirm` (Full Memory Wipe):**
- Очищает `conversation_history` + `SupabaseStore.delete_by_user()` (долгосрочная память)
- Очищает `QueryCache` (единственный user-scoped кеш, keyed by `sha256(user_id:query)`)
- `EmbeddingCache` и `RerankCache` НЕ трогаются — они глобальная инфраструктура без user_id в ключах; их очистка = деградация latency без пользы
- Двухшаговое подтверждение: первый вызов → предупреждение, `/reset_memory confirm` → выполнение
- Irreversible, логируется

**Почему две команды, не одна:** разный intent = разная команда (architecture §2.3, No Hidden Authority). Одна команда с «режимами» — скрытый authority.

**Добавлено в `query_cache.py`:** метод `delete_by_user(user_id)` через `SCAN` (не `KEYS` — non-blocking для production Redis). Чистит все `qcache:*` ключи — обратить хеш невозможно, но TTL 10 минут делает collateral минимальным.

**Добавлено в `i18n/strings.py`:** три новых ключа на 12 языках:
- `session_cleared` — подтверждение /clear с подсказкой про /reset_memory
- `memory_reset_confirm` — предупреждение перед полным сбросом
- `memory_reset_done` — подтверждение полного сброса

**Обновлён `help_display`** для en и ru: добавлены упоминания `/clear` и `/reset_memory`.

**Файлы:** `transport/telegram/webhook.py`, `retrieval/cache/query_cache.py`, `i18n/strings.py`
**Статус:** ✅ закрыт

---

### ✅ 8.1 — Мёртвый DENY-check в update_handler (сессия 2, верифицировано сессия 3)

**Суть:** `safety_gate.py` всегда возвращает `GateVerdict.PASS`, три ветки в `update_handler.py` проверяли `gate.verdict == GateVerdict.DENY` — мёртвый код. Заменены комментарием.
**Статус:** ✅ закрыт

---

## ОТКРЫТЫЕ ЗАДАЧИ

### 🟡 17.2 — TruthMode: частично реализовано через confidence-based retrieval gating

**Исходная проблема:** TruthMode (STRICT/HYBRID) — инструкция в промпт, не enforcement layer. `truth_check(answer, retrieval_context) -> float` не существует ни в одном файле.

**Что реализовано в сессии 3 (implicit truth proxy):**
- `MemoryRecord.similarity` — реальный pgvector score вместо хардкода 1.0
- Score propagation через весь retrieval pipeline до `RetrievedDocument.score`
- Score filter `≥ 0.75` в `update_handler` перед сборкой контекста
- Pre-execution STRICT gate в orchestrator (существовал, теперь получает качественный контекст)

Это production pattern (RAG safety gating): `if retrieval weak → no grounding → no strict answer`.

**Что НЕ реализовано (следующий уровень):**
- Post-generation factual verification
- Contradiction detection (ответ противоречит контексту)
- Memory-vs-context separation (старая память vs свежий retrieval)
- Time-awareness (устаревшие факты в памяти)

**Архитектурная позиция зафиксирована:** `truth_check` как отдельный verification step нереализуем без компромисса при текущих constraints (Telegram, latency, cost). Full LLM-judge = x2 latency + x2 cost. Cross-encoder как judge = не по назначению. Правильный вывод: truth — confidence function over pipeline, не отдельный модуль.

**Статус:** 🟡 частично реализовано. Следующий уровень — contradiction detection и memory-vs-context separation — после стабилизации текущих изменений.

---

### 🟡 13.3 — CoT артефакты (остаточные случаи)

**Симптом:** `Constraints:`, `Candidates:`, `Проверка каждого constraints:`, `NO ERRORS FOUND`, `Verification table` в ответе пользователю. Наблюдалось при вопросе «Кто такой Бан из 7 смертных грехов?» в загрязнённой сессии.

**Связь с retrieval:** нерелевантный контекст из памяти провоцировал модель на избыточное reasoning → CoT вылезал наружу. После фикса retrieval (20.1) этот триггер устранён. Но механизм stripping должен ловить артефакты независимо от причины.

**Верифицировано кодом:** `_strip_cot_artifacts()` в `response_synthesizer.py` реализован. Покрывает Mode A (loop detection) и Mode B (header stripping). Путь vision + не-MATH intent + CoT не покрыт отдельными тестами.

**Файлы:** `cognition/response_synthesizer.py`, `transport/telegram/vision_handler.py`
**Статус:** 🟡 частично. Мониторить после деплоя 20.1 — вероятно основной триггер устранён.

---

### 🟡 13.4 — Classifier теряет контекст на follow-up

**Симптом:** короткое сообщение `«Вот, нашла»` → CONVERSATION вместо правильного intent.
**Частично закрыт:** history context добавлен для сообщений ≤ 8 слов (последние 4 хода, макс 150 символов на ход).
**Осталось:** asyncio stress tests — без них нет уверенности при concurrent запросах.
**Файл:** `cognition/intent_engine.py` → `_llm_pre_classify`
**Статус:** 🟡 частично закрыт

---

### 🔴 19.x — Global formatting contract

**Суть:** паттерн нумерации и шаблонных открытий потенциально кросс-слойный. Фикс 18.3 закрыл extraction. Уровень 2 — global formatting rule — нужен только если паттерн всплывёт снова.

**Правило:** реализовывать только по факту повторного появления, не превентивно.

**Статус:** 🔴 спроектировано, не реализовано. Низкий приоритет пока 18.3 держит.

---

### 🔴 21.1 — Email уведомления (Brevo) — opt-in

**Суть:** `event_notifier.py` умеет слать письма через Brevo, но email пользователя неоткуда брать —
Telegram Bot API не передаёт email даже если пользователь регистрировался через него.

**Решение (спроектировано):**
- пользователь вводит email вручную через команду (`/settings` или отдельный флоу)
- в Supabase таблица `user_notifications` с полями:
  ```
  user_id
  email
  notify_balance_exhausted: bool  (default: false)
  notify_balance_credited: bool   (default: false)
  ```
- оба флага по умолчанию выключены — строгий opt-in, не opt-out
- `event_notifier.py` проверяет флаги перед отправкой

**Что слать:**
- `notify_balance_exhausted` → письмо когда EPK вернул DENY (баланс = 0), пользователь офлайн
- `notify_balance_credited` → подтверждение пополнения (опционально, многих раздражает)

**Текст писем:** переписать в голосе Сэёны — текущие шаблоны корпоративные, диссонируют с характером бота.

**Что НЕ слать пользователю:** safety_block, system_error — это внутренние события, только в логи / Sentry.

**Файлы:** `notifications/email_service.py`, `notifications/event_notifier.py`
**Статус:** 🔴 спроектировано, не реализовано. Низкий приоритет — требует UI для сбора email.

---

### 🟢 13.7 — Грузинский i18n fallback

**Симптом:** вопрос на грузинском → `«уточните вопрос»` вместо `«технический сбой»`.
**Файл:** `i18n/strings.py`, ключ `search_unavailable`, lang `ka`.
**Статус:** 🟢 быстрое закрытие, одна строка

---

## ГОЛОСОВЫЕ СООБЩЕНИЯ — СТАТУС (май 2026)

Голосовой pipeline работает стабильно. Production-ready.
Лимит: 5 минут. Голос линейный → поведение предсказуемое. Vision ветвистая → нестабильная. Это архитектурная разница, не баг.

---

## ЗАКРЫТЫЕ ЗАДАЧИ (полная история)

| # | Закрыт | Суть | Ключевое решение |
|---|--------|------|-----------------|
| 13.1 | май 2026 | tool intents → «сервис недоступен» | compound = синтезатор, не агент; tool_choice убран |
| 13.5 | май 2026 | описательный запрос → поиск по сырому тексту | `_understand_query()` в `classify()` — KNOWN_ENTITY vs DESCRIPTIVE |
| 13.6 | май 2026 | бот отвечал на каждое фото альбома отдельно | Redis-backed `MediaGroupAggregator`, debounce, Lua atomicity |
| 13.6.1 | май 2026 | lock bug, смешение партий, lang хардкод | `_LUA_FLUSH` атомарный DEL, `MediaGroupItem.lang`, `input_type` в OrchestratorRequest |
| 17.1 | май 2026 | CoT infinite loop | `reasoning_engine.py`: QUESTION → mode=DIRECT |
| 17.3 | май 2026 | шаблонные ответы, «Изображения представляют собой» | history-aware variation в `prompt_engine`, `detect_repetitive_opening` в `analysis`, расширены patterns в `correction` |
| 18.1 | май 2026 | synthesis шаблон: запреты вместо target pattern | target pattern в `_GROUP_SYNTHESIS_SYSTEM_TEMPLATE`, убраны `Part N:` лейблы |
| 18.2 | май 2026 | caption+фото → нарратив вместо ответа на вопрос | `_vision_image_context` → `retrieved_context` в `update_handler.py` |
| 18.3 | май 2026 | нумерация «Первое/Второе изображение» | constraint в `_GROUP_EXTRACTION_SYSTEM` — запрет ordinal labels |
| 18.4 | май 2026 | нет лимита на количество фото → деградация | `_MAX_GROUP_IMAGES=6` guardrail + `too_many_images` i18n |
| 20.1 | май 2026 | memory contamination → «Из контекста можно сделать вывод» | similarity score propagation + score filter 0.75 в update_handler |
| 20.2 | май 2026 | /clear и /reset_memory отсутствовали | две команды с разной семантикой (Mode A / Mode B), двухшаговое подтверждение для Mode B |
| 8.1 | май 2026 | мёртвые DENY-check в update_handler | ветки удалены, заменены комментарием |

---

## CI (planned)

coverage floor 75%, asyncio stress tests (13.4), integration tests compound pipeline, retrieval quality regression, mypy.

---

## СЛЕДУЮЩИЙ ШАГ (сессия 4)

**Деплой сессии 3 — файлы для замены:**
1. `memory/supabase_store.py`
2. `retrieval/retrieval_engine.py`
3. `retrieval/cache/query_cache.py`
4. `transport/telegram/update_handler.py`
5. `transport/telegram/webhook.py`
6. `i18n/strings.py`

**Тестирование после деплоя:**
1. Новый вопрос в старом чате → не должно быть «Из контекста можно сделать вывод»
2. `/clear` → подтверждение, следующий вопрос без старой истории, память сохранена
3. `/reset_memory` → предупреждение, `/reset_memory confirm` → удаление, следующий вопрос без старой памяти
4. `/reset_memory` без confirm → только предупреждение, ничего не удаляется
5. Вопрос на грузинском → правильный fallback (13.7 — быстро закрыть)
6. CoT артефакты — мониторить, вероятно исчезнут после устранения retrieval триггера

**После стабилизации:**
- contradiction detection (17.2 следующий уровень)
- memory-vs-context separation (17.2 следующий уровень)
- asyncio stress tests (13.4)
- CI coverage floor 75%