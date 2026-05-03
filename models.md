🧠 🥇 SINGLE SOURCE OF TRUTH (FINAL v6.3 — META LAYER SEALED)

⚙️ 5. LLM LAYER (GROQ + HF — ROLE-ISOLATED FABRIC v6.3)

🛡 SAFETY LAYER (deterministic cascade — FIRST GATE)

prompt-guard-2-22m    → FAST REJECTION FILTER (first pass)
prompt-guard-2-86m    → DEEP CLASSIFICATION FILTER (second pass)
gpt-oss-safeguard-20b → FINAL ENFORCEMENT MODEL (hard gate)

✔ ROLE:
  constraint evaluation only
  NO generation role
  NO reasoning synthesis role
  22m EXECUTES BEFORE FEATURE EXTRACTION
  86m + safeguard-20b EXECUTE AFTER FEATURE EXTRACTION

✔ UNAVAILABILITY RULE:
  Safety models unavailable → DENY by default
  NO fallback to ALLOW ❌
  NO partial execution ❌

✔ CRITICAL DISTINCTION:
  Safety Layer → firewall на входе
                 детерминированный
                 блокирует очевидно вредный input
  safety_agent → семантический валидатор
                 после reasoning
                 ловит unsafe emergent content
  НЕ дублирование ✅

✔ MODEL NOTES:
  prompt-guard-2-22m / 86m → специализированы Meta
                              для детекции вредоносных промптов
                              роль совпадает с назначением точно
  gpt-oss-safeguard-20b    → safeguard модель
                              роль совпадает с назначением точно

🟢 FAST TIER (inference — ALLOW / DEGRADED only)

llama-3.1-8b-instant → STRUCTURAL SIGNAL COMPRESSION / SHALLOW INFERENCE
allam-2-7b           → MULTILINGUAL NLP NORMALIZATION (Arabic anchor)

✔ ROLE:
  primary inference при ALLOW / DEGRADED
  pre-EPK signal shaping
  low-cost transformation
  multilingual input normalization
  NO reasoning authority
  NO intent generation authority
  SKIP при HEAVY_REQUIRED ❌
  SKIP при DENY ❌

✔ MODEL NOTES:
  llama-3.1-8b-instant → самая лёгкая и быстрая модель в списке
                          роль соответствует точно
                          при HEAVY_REQUIRED →
                          используется ТОЛЬКО в heavy_input_shaper.py
                          НЕ как Fast Tier ❌

  allam-2-7b           → создана Saudi Aramco
                          специализация: арабский язык
                          одна модель, один вызов на входе pipeline
                          используется в трёх контекстах:
                            Fast Tier → preprocessing
                            Specialized Layer → TTS pipeline
                            Multilingual Normalization → Arabic routing
                          НЕ три отдельных инстанса ✅
                          НЕ оптимизирована для других языков ⚠️
                          остальные языки → llama-3.3-70b-versatile

🔵 GENERAL TIER (primary reasoning fabric)

llama-3.3-70b-versatile → PRIMARY REASONING CORE + CREATIVE ENGINE
qwen/qwen3-32b          → STRUCTURED LOGIC / FORMATTING ENGINE
openai/gpt-oss-20b      → CONSTRAINT-AWARE GENERAL INFERENCE

✔ ROLE:
  unified reasoning space
  multi-model reasoning diversity
  creative synthesis (70b)
  structured output formatting (qwen)
  NO control authority
  NO policy influence
  SKIP при HEAVY_REQUIRED ❌
  SKIP при DEGRADED_MODE ❌
  SKIP при DENY ❌

✔ NOTE:
  FAST / GENERAL / HEAVY = тиры мощности моделей
  часть LLM Layer + EPK cost model
  НЕ слои логики ❌
  НЕ когнитивные слои ❌

✔ MODEL NOTES:
  llama-3.3-70b-versatile → лучшая общая модель в списке
                             роль соответствует точно
                             fallback для не-арабских языков ✅

  qwen/qwen3-32b          → reasoning модель с thinking mode
                             используется для форматирования
                             thinking mode ДОЛЖЕН быть отключён явно:
                             "thinking": False ⚠️

  openai/gpt-oss-20b      → OpenAI open-source модель на Groq
                             специализация публично не задокументирована
                             роль подобрана по размеру (средний слой)
                             риск низкий, осознанный выбор ⚠️

🔴 HEAVY TIER (capability decomposition — FINAL FORM)

openai/gpt-oss-120b            → DEEP MULTI-STEP REASONING ENGINE
                                  PRIMARY: Heavy Tier reasoning
                                  SECONDARY: Consensus arbiter
                                  (только если Heavy Tier не активен)
                                  mutex: никогда не активен в обеих ролях ❌
llama-4-scout-17b-16e-instruct → LONG-CONTEXT TRANSFORMATION ENGINE

✔ ACTIVATION RULE:
  активируется ТОЛЬКО по сигналу EPK = HEAVY_REQUIRED
  Orchestrator исполняет сигнал, не генерирует его
  NO self-activation ❌
  NO agent-triggered activation ❌
  NO orchestrator-initiated activation ❌

✔ OUTPUT RULE:
  Heavy Tier output → напрямую в Response Synthesizer
  Consensus SKIP (mutex)
  Response Synthesizer агрегирует Heavy Tier output ✅

✔ HARD INVARIANTS:
  each subsystem = isolated capability domain
  NO shared state
  NO hierarchical dominance
  NO cross-decision influence

✔ MODEL NOTES:
  openai/gpt-oss-120b            → самая тяжёлая модель в списке
                                    роль соответствует точно
  llama-4-scout-17b-16e-instruct → 512K контекст
                                    создана именно для long-context
                                    роль соответствует точно

🛠 HEAVY INPUT SHAPER (self-gated utility — не тир)

llm/heavy_input_shaper.py

✔ ROLE:
  подготовка входа для Heavy Tier
  self-gated utility — НЕ тир ❌
  НЕ агент ❌
  НЕ inference слой ❌

✔ ACTIVATION:
  ONLY when EPK = HEAVY_REQUIRED ✅
  SKIP on ALLOW ❌
  SKIP on DEGRADED_MODE ❌
  SKIP on DENY ❌

✔ EXECUTION MODEL:
  ALWAYS CALLED on HEAVY_REQUIRED
  internal gating:
    if shaping needed → выполняет операцию
    if shaping not needed → NO-OP (return input as-is)

✔ DECISION FACTORS (internal):
  context_size
  retrieval structure
  token limits
  format complexity

✔ OPERATIONS (реализация может меняться):
  compression / chunking / summarization
  deduplication / ranking
  → название отражает РОЛЬ, не реализацию ✅

✔ CONSTRAINTS:
  NO reasoning ❌
  NO final output generation ❌
  uses llama-3.1-8b-instant (NOT as Fast Tier) ✅

🤖 AGENT LAYER (tool-use execution fabric)

groq/compound      → DEEP AGENT
groq/compound-mini → FAST AGENT

✔ ROLE:
  compound      → deep_agent.py
  compound-mini → fast_agent.py
  tool selection authority ✅
  multi-step execution ✅
  NO policy selection authority ❌
  NO system governance ❌
  NO Heavy Tier activation ❌

⚖️ CONSENSUS LAYER

openai/gpt-oss-120b → CONSENSUS ARBITER
                      ACTIVE: только если Heavy Tier не активен
                      SKIP при HEAVY_REQUIRED (mutex) ✅
                      при HEAVY_REQUIRED →
                      Response Synthesizer агрегирует напрямую ✅

🎤 SPECIALIZED LAYER

whisper-large-v3       → PRIMARY SPEECH-TO-TEXT
whisper-large-v3-turbo → FAST SPEECH-TO-TEXT
orpheus-v1-english     → ENGLISH SPEECH SYNTHESIS
orpheus-arabic-saudi   → ARABIC SPEECH SYNTHESIS
allam-2-7b             → MULTILINGUAL NLP (Arabic anchor)

✔ ACTIVATION RULE (orpheus):
  is_voice_input = true → активируется ✅
  NO arbitrary activation ❌

🧠 6. HF EMBEDDINGS + RETRIEVAL INTELLIGENCE LAYER (v6.3)

BAAI/bge-large-en-v1.5 → PRIMARY EMBEDDING SPACE
BAAI/bge-small-en-v1.5 → FAST EMBEDDING FALLBACK
BAAI/bge-reranker-large → CROSS-ENCODER RERANKING

🚫 STRICT SEPARATION:
  bge-large / bge-small → ONLY generate vectors
  bge-reranker-large    → ONLY reorders candidates
                          NEVER generates embeddings
                          NEVER influences EPK / agents / cognition

🧠 7. FEATURE LAYER (v6.3)

features = {
    "token_count": int,
    "char_count": int,
    "newline_density": float,
    "has_code_block": bool,
    "has_json_shape": bool,
    "has_math_symbols": bool,
    "unicode_entropy": float,
    "is_voice_input": bool
}

✔ ПОСЛЕ Safety Gate Pass 1 (22m)
✔ ДО Safety Gate Pass 2 (86m + safeguard)
✔ ДО Intent Engine
✔ ДО любого LLM слоя

📏 8. COMPLEXITY MODEL (v6.3)

LOW      → chat / short text
MEDIUM   → structured input
HIGH     → logs / code / structured blocks
CRITICAL → mixed modality / context_length > 32K tokens
           → EPK OUTPUT: HEAVY_REQUIRED

⚙️ 9. EPK (v6.3 — SOLE POLICY ENGINE)

EPK = deterministic policy function over structural state + cost constraints

OUTPUT:
  ALLOW          → normal execution path
                   полный DAG ✅

  DENY           → немедленный выход
                   NO downstream activation ❌

  DEGRADED_MODE  → reduced execution path:
                   Memory Retrieval ✅
                   Embedding Retrieval ✅
                   Reranker ✅
                   analysis.py (lightweight) ✅
                   Intent Engine ✅
                   Fast Tier (8b-instant) ✅
                   skip Reasoning Engine ❌
                   skip Multi-Agent Coordinator ❌
                   skip General Tier ❌
                   skip Agent Layer ❌
                   skip safety_agent ❌
                   skip heavy_input_shaper ❌
                   skip Heavy Tier ❌
                   skip Consensus ❌
                   Response Synthesizer напрямую ✅
                   META lightweight active ✅

  HEAVY_REQUIRED → Heavy path:
                   [SKIP FAST TIER] ❌
                   [SKIP GENERAL TIER] ❌
                   analysis.py (full) ✅
                   Reasoning Engine ACTIVE ✅
                   heavy_input_shaper ALWAYS CALLED (self-gated) ✅
                   Heavy Tier mandatory ✅
                   safety_agent mandatory ✅
                   Consensus SKIP (mutex) ❌
                   Response Synthesizer агрегирует напрямую ✅
                   META full active ✅

✔ SOLE POLICY AUTHORITY
🚫 NO ACCESS: memory / embeddings / LLM / agents / logs / metrics

🧩 10. COGNITION LAYER (v6.3 — ROLES SEALED)

intent_engine.py
✔ ROLE: stateless prompt construction / request shaping
  NO policy decision ❌
  NO routing control ❌

reasoning_engine.py
✔ ROLE: когнитивная логика системы
  строит reasoning_plan
  декомпозирует задачу
  передаёт plan → multi_agent_coordinator

✔ ACTIVATION:
  ACTIVE on ALLOW ✅
  ACTIVE on HEAVY_REQUIRED ✅
  skip on DENY ❌
  skip on DEGRADED_MODE ❌

✔ PRINCIPLE:
  reasoning_engine = control-plane (архитектор)
  Heavy Tier       = data-plane (исполнитель)
  разделение обязательно ✅

✔ HARD RULES:
  NO model routing ❌
  NO agent execution ❌
  NO policy authority ❌

multi_agent_coordinator.py
✔ ROLE: планировщик взаимодействия агентов
  вызывается ТОЛЬКО orchestrator'ом ✅
  принимает reasoning_plan
  строит agent_execution_plan
  определяет порядок / зависимости
  возвращает plan ТОЛЬКО orchestrator'у ✅
  skip on DENY / DEGRADED_MODE ❌

✔ HARD RULES:
  NO прямой вызов агентов ❌
  NO управление pipeline ❌
  NO выбор модели ❌
  NO финальные решения ❌

response_synthesizer.py
✔ ROLE: FINAL OUTPUT AUTHORITY

✔ INTERNAL PIPELINE:
  1. assemble_response
  2. structure_output
  3. apply_formatting
  4. apply_correction  ← вызывает meta/correction.py
  5. finalize_output

✔ AGGREGATION:
  агрегирует Heavy Tier output при HEAVY_REQUIRED ✅

✔ INVARIANTS:
  correction НЕ имеет authority ❌
  correction CANNOT override synthesizer intent ❌
  location: meta/ | authority: synthesizer ✅
  NO policy control ❌
  NO agent selection ❌
  NO routing decision ❌

🧠 11. META LAYER (v6.3 — FULLY SEALED)

meta/
├── analysis.py      ← PRE-REASONING (шаг DAG до intent_engine)
├── reflection.py    ← POST-EXECUTION (side-channel)
├── correction.py    ← INLINE (owned by meta, called by synthesizer)
└── memory_audit.py  ← OFFLINE DIAGNOSTICS (side-channel)

✔ КЛЮЧЕВОЙ ИНВАРИАНТ:
  META LAYER:
    observes system ✅
    NEVER controls system ❌
    NEVER participates in execution decisions ❌

✔ CRITICAL DISTINCTIONS:
  META ≠ COGNITION
    meta      → наблюдает и оценивает
    cognition → думает и принимает решения

  META ≠ OBSERVABILITY
    observability → техническая телеметрия
                    инфраструктурный уровень
                    system alive? latency? errors?
    meta          → семантическое качество
                    application уровень
                    ответ логичный? полный? противоречивый?

✔ SIMPLE MODEL:
  memory     → "что мы знаем"
  cognition  → "как мы думаем"
  meta       → "насколько это всё нормально работает"
  observability → "живёт ли система"

── analysis.py ────────────────────────────────────

✔ POSITION: PRE-REASONING
  шаг в DAG до intent_engine
  НЕ вызывается Orchestrator'ом явно ❌
  автоматический шаг pipeline ✅

✔ ACTIVATION:
  ACTIVE on ALLOW (full) ✅
  ACTIVE on HEAVY_REQUIRED (full) ✅
  ACTIVE on DEGRADED_MODE (lightweight) ✅
  SKIP on DENY ❌

✔ OUTPUT: hints (non-binding)
  hints MAY be ignored ✅
  hints have ZERO authority ✅
  hints are NOT policy ✅

✔ DOES:
  input decomposition
  pattern detection (non-semantic)
  complexity hints (non-binding)

✔ DOES NOT:
  NO policy decisions ❌
  NO routing ❌
  NO reasoning ❌
  NO memory interaction ❌

── reflection.py ──────────────────────────────────

✔ POSITION: POST-EXECUTION side-channel
  активируется после OUTPUT
  non-blocking, async ✅

✔ ACTIVATION:
  ACTIVE on ALLOW (full) ✅
  ACTIVE on HEAVY_REQUIRED (full) ✅
  ACTIVE on DEGRADED_MODE (lightweight) ✅
  SKIP on DENY ❌

✔ OUTPUT: reflection_report
  DESTINATION:
    → observability (logs / traces) ✅
    → optional: memory_audit input (offline) ✅
  NO pipeline feedback ❌
  NO response modification ❌
  NO execution influence ❌
  НЕ влияет на текущий request ❌
  только логирование и оффлайн анализ ✅

✔ DOES:
  сравнение intent ↔ output
  проверка полноты / согласованности
  выявление логических дыр

✔ DOES NOT:
  NO rewriting reasoning ❌
  NO regeneration ❌
  NO pipeline control ❌

── correction.py ──────────────────────────────────

✔ OWNERSHIP: meta layer
✔ EXECUTION: ONLY via response_synthesizer (step 4)
✔ EXCLUDED FROM: META side-channel DAG ❌

✔ POSITION в synthesizer:
  AFTER assemble / structure / format
  BEFORE finalize_output

✔ DOES:
  improve readability
  fix minor inconsistencies
  normalize structure

✔ DOES NOT:
  NO full regeneration ❌
  NO reasoning override ❌
  NO new information ❌
  NO pipeline control ❌
  CANNOT override synthesizer intent ❌

✔ INVARIANT:
  location: meta/ ✅
  authority: response_synthesizer ✅
  НЕ независимый слой execution ❌

── memory_audit.py ────────────────────────────────

✔ POSITION: OFFLINE DIAGNOSTICS side-channel
  async, non-blocking ✅
  НЕ часть основного DAG ❌

✔ ACTIVATION:
  ACTIVE on ALLOW ✅
  ACTIVE on HEAVY_REQUIRED ✅
  ACTIVE on DEGRADED_MODE (lightweight) ✅
  SKIP on DENY ❌

✔ OUTPUT: audit_report (read-only)
  optional input для reflection.py ✅

✔ DOES:
  detect conflicts / duplicates
  detect inconsistencies / stale entries

✔ HARD RULES:
  NO memory write ❌
  NO memory update ❌
  NO conflict resolution ❌
  NO retrieval influence ❌
  NO execution trigger ❌
  НЕ часть memory pipeline ❌

✔ META LAYER в DEGRADED_MODE:
  STATUS: ENABLED (lightweight mode)
  analysis    → lightweight hints ✅
  reflection  → lightweight report ✅
  memory_audit → lightweight diagnostics ✅
  correction  → вызывается из synthesizer как обычно ✅
  REASON: preserve observability of degraded behavior
  INVARIANT:
    meta NEVER affects EPK decision ❌
    meta NEVER increases tier ❌

── META side-channel DAG ──────────────────────────

META side-channel INCLUDES:
  analysis.py    ← pre-reasoning step (в основном DAG)
  reflection.py  ← post-execution (после OUTPUT)
  memory_audit.py ← offline diagnostics (после OUTPUT)

META side-channel EXCLUDES:
  correction.py ❌ (owned by meta, executed by synthesizer)

🤖 12. AGENT LAYER — SAFETY AGENT (v6.3)

safety_agent.py
✔ ROLE: POST-REASONING SEMANTIC SAFETY VALIDATION

✔ ACTIVATION:
  активен при ALLOW ✅
  активен при HEAVY_REQUIRED ✅
  skip при DEGRADED_MODE ❌
  skip при DENY ❌

✔ POSITION: LAST in Agent Layer — final check before Consensus

✔ RESPONSIBILITIES:
  валидация reasoning_plan и draft_response
  детекция unsafe emergent content
  выдаёт сигнал: allow / revise / block

✔ NON-RESPONSIBILITIES:
  NO input-level filtering ❌
  NO deterministic cascade ❌
  NO model routing ❌

🔁 13. FINAL EXECUTION DAG (v6.3)

INPUT
↓
Safety Gate — PASS 1 (22m)
  unavailable → DENY by default
↓
Feature Extraction (все сигналы + is_voice_input)
↓
Safety Gate — PASS 2 (86m + safeguard-20b)
  unavailable → DENY by default
↓
Auth / Rate Limit
↓
Event Log
↓
Multilingual Normalization
  allam-2-7b    → арабский [один вызов]
  llama-3.3-70b → остальные
↓
EPK [SOLE POLICY AUTHORITY]
  DENY           → EXIT
  ALLOW          → полный DAG ↓
  DEGRADED_MODE  → limited path ↓
  HEAVY_REQUIRED → Heavy path ↓
↓
Memory Retrieval               [skip on DENY]
↓
Embedding Retrieval            [skip on DENY]
(bge-large → bge-small fallback)
↓
Reranker                       [skip on DENY]
↓
analysis.py                    [skip on DENY]
  ALLOW / HEAVY → full ✅
  DEGRADED      → lightweight ✅
  (hints non-binding → intent_engine)
↓
Intent Engine                  [skip on DENY]
↓
Reasoning Engine               [skip on DENY / DEGRADED]
                               [ACTIVE on ALLOW / HEAVY_REQUIRED]
↓
Multi-Agent Coordinator        [skip on DENY / DEGRADED]
↓
Orchestrator (EPK signal execution only)
  ├── HEAVY_REQUIRED
  │   → [SKIP FAST TIER] ❌
  │   → [SKIP GENERAL TIER] ❌
  │   → heavy_input_shaper (ALWAYS CALLED, self-gated)
  │       shaping needed → execute ✅
  │       not needed → NO-OP ✅
  │   → Heavy Tier (120b / scout) [mandatory]
  │   → safety_agent [mandatory] ✅
  │   → [SKIP CONSENSUS] ❌ (mutex)
  │   → Response Synthesizer (агрегирует напрямую) ✅
  ├── ALLOW
  │   → Fast Tier (8b) ✅
  │   → General Tier (70b / qwen / gpt-oss-20b) ✅
  │   → Agent Layer (compound / compound-mini) ✅
  │   → safety_agent (final check) ✅
  │   → Consensus (120b) ✅
  └── DEGRADED_MODE
      → Fast Tier only (8b) ✅
      → [skip everything else] ❌
      → Response Synthesizer напрямую ✅
↓
Response Synthesizer ← FINAL OUTPUT AUTHORITY
  1. assemble_response
  2. structure_output
  3. apply_formatting
  4. apply_correction (meta/correction.py)
  5. finalize_output
  агрегирует Heavy Tier output при HEAVY_REQUIRED ✅
↓
  ├── is_voice_input = true  → Speech Output (orpheus)
  └── is_voice_input = false → TEXT OUTPUT
↓
Event Store ──────────────┐
                          ├── ПАРАЛЛЕЛЬНО
Memory Write ─────────────┘
↓
[META side-channel — non-blocking, async]
  reflection.py   → report → observability / memory_audit
  memory_audit.py → offline diagnostics
  ALLOW / HEAVY   → full mode ✅
  DEGRADED        → lightweight mode ✅
  DENY            → SKIP ❌
↓
OUTPUT

🚫 14. SIDE-CHANNEL CLOSURE (v6.3 — SEALED)

── HARD PROHIBITIONS ──────────────────────────────

memory       → control ❌
embeddings   → routing ❌
reranker     → decision ❌
LLM          → governance ❌
optimization → system behavior ❌
meta         → execution authority ❌
meta         → policy authority ❌
meta         → routing authority ❌
meta         → EPK influence ❌
meta         → tier escalation ❌

── AUTHORITY BOUNDARIES ───────────────────────────

agents → policy selection ❌
agents → tool selection ✅

intent → policy decision ❌
intent → prompt construction ✅

reasoning_engine → plan construction ✅
reasoning_engine → ACTIVE on ALLOW / HEAVY_REQUIRED ✅
reasoning_engine → skip on DENY / DEGRADED ❌
reasoning_engine → control-plane ✅
reasoning_engine → agent execution ❌
reasoning_engine → policy authority ❌

multi_agent_coordinator → agent planning ✅
multi_agent_coordinator → called by orchestrator only ✅
multi_agent_coordinator → returns plan to orchestrator only ✅
multi_agent_coordinator → agent execution ❌
multi_agent_coordinator → pipeline control ❌
multi_agent_coordinator → model selection ❌

safety_agent → post-reasoning validation ✅
safety_agent → active on ALLOW / HEAVY_REQUIRED ✅
safety_agent → skip on DEGRADED / DENY ❌
safety_agent → input-level filtering ❌
safety_agent → deterministic cascade ❌

heavy_input_shaper → self-gated utility ✅
heavy_input_shaper → ONLY on HEAVY_REQUIRED ✅
heavy_input_shaper → ALWAYS CALLED on HEAVY_REQUIRED ✅
heavy_input_shaper → internal 