🥇 FINAL ARCHITECTURE v5.5 (FULLY SYNCED WITH SSoT v6.3)

📁 APP LAYER
app/
├── main.py
├── bootstrap.py
├── settings.py

🌐 TRANSPORT LAYER (INGRESS ONLY)
transport/telegram/
├── webhook.py
├── update_handler.py
├── message_router.py
├── callback_handler.py
└── auth_middleware.py
✔ ingestion only / no domain logic / no routing decisions

⚙️ EXECUTION CORE
core/kernel/
├── execution_policy_kernel.py   # EPK — SOLE POLICY AUTHORITY
├── decision_matrix.py
├── cost_model.py
├── policy_registry.py

core/execution/
├── orchestrator.py              # EPK signal execution only

✔ EPK OUTPUT: ALLOW | DENY | DEGRADED_MODE | HEAVY_REQUIRED

  ALLOW →
    полный DAG ✅

  DENY →
    immediate exit ❌
    NO downstream ❌

  DEGRADED_MODE →
    Memory / Embedding / Reranker ✅
    analysis.py (lightweight) ✅
    Intent Engine ✅
    Fast Tier only ✅
    skip Reasoning / Coordinator / General / Agents ❌
    skip safety_agent / heavy_input_shaper / Heavy / Consensus ❌
    Response Synthesizer напрямую ✅
    META lightweight ✅

  HEAVY_REQUIRED →
    [SKIP FAST TIER] ❌
    [SKIP GENERAL TIER] ❌
    analysis.py (full) ✅
    Reasoning Engine ACTIVE ✅
    heavy_input_shaper ALWAYS CALLED (self-gated) ✅
    Heavy Tier mandatory ✅
    safety_agent mandatory ✅
    Consensus SKIP (mutex) ❌
    Response Synthesizer агрегирует напрямую ✅
    META full ✅

✔ Orchestrator = EPK signal execution only
✔ NO policy generation ❌
✔ NO routing decisions ❌
✔ NO Heavy Tier self-activation ❌

🔁 EVENT SYSTEM
events/
├── event_bus.py
├── event_store.py
├── event_types.py
├── event_dispatcher.py
└── event_replay.py
✔ append-only / no execution influence
✔ Event Store ∥ Memory Write: параллельно / independent failure domains

🧠 COGNITION LAYER
cognition/
├── intent_engine.py
├── reasoning_engine.py
├── multi_agent_coordinator.py
└── response_synthesizer.py

✔ intent_engine.py
  stateless prompt construction
  NO policy ❌ NO routing ❌

✔ reasoning_engine.py
  строит reasoning_plan
  ACTIVE on ALLOW / HEAVY_REQUIRED ✅
  skip on DENY / DEGRADED ❌
  control-plane (архитектор) ✅
  Heavy Tier = data-plane (исполнитель) ✅
  NO model routing ❌ NO agent execution ❌ NO policy ❌

✔ multi_agent_coordinator.py
  вызывается ТОЛЬКО orchestrator'ом ✅
  строит agent_execution_plan
  возвращает ТОЛЬКО orchestrator'у ✅
  skip on DENY / DEGRADED ❌
  NO прямой вызов агентов ❌
  NO pipeline control ❌
  NO model selection ❌

✔ response_synthesizer.py
  FINAL OUTPUT AUTHORITY

  INTERNAL PIPELINE:
    1. assemble_response
    2. structure_output
    3. apply_formatting
    4. apply_correction  ← meta/correction.py
    5. finalize_output

  агрегирует Heavy Tier output при HEAVY_REQUIRED ✅
  correction НЕ имеет authority ❌
  location: meta/ | authority: synthesizer ✅
  NO policy ❌ NO agent selection ❌ NO routing ❌

🧠 META LAYER (OBSERVATION / DIAGNOSTICS ONLY)
meta/
├── analysis.py      ← PRE-REASONING (шаг DAG до intent_engine)
├── reflection.py    ← POST-EXECUTION side-channel
├── correction.py    ← INLINE (owned: meta / executed: synthesizer)
└── memory_audit.py  ← OFFLINE DIAGNOSTICS side-channel

✔ КЛЮЧЕВОЙ ИНВАРИАНТ:
  observes system ✅
  NEVER controls system ❌
  NEVER participates in execution decisions ❌
  NEVER affects EPK ❌
  NEVER escalates tier ❌

✔ META ≠ COGNITION (наблюдает vs думает)
✔ META ≠ OBSERVABILITY (смысл vs система)

✔ analysis.py
  POSITION: DAG шаг ДО intent_engine
  НЕ вызывается Orchestrator'ом ❌
  автоматический шаг pipeline ✅
  ACTIVE on ALLOW / HEAVY (full) ✅
  ACTIVE on DEGRADED (lightweight) ✅
  SKIP on DENY ❌
  OUTPUT: hints (non-binding, zero authority)
  NO policy ❌ NO routing ❌ NO reasoning ❌

✔ reflection.py
  POSITION: POST-EXECUTION side-channel
  ACTIVE on ALLOW / HEAVY (full) ✅
  ACTIVE on DEGRADED (lightweight) ✅
  SKIP on DENY ❌
  OUTPUT: reflection_report
    → observability (logs / traces) ✅
    → optional: memory_audit input ✅
  NO pipeline feedback ❌
  NO response modification ❌
  NO current request influence ❌

✔ correction.py
  OWNERSHIP: meta/
  EXECUTION: ONLY via response_synthesizer (step 4)
  EXCLUDED FROM: META side-channel DAG ❌
  NO authority ❌
  NO independent execution ❌
  CANNOT override synthesizer intent ❌

✔ memory_audit.py
  POSITION: OFFLINE side-channel
  ACTIVE on ALLOW / HEAVY / DEGRADED ✅
  SKIP on DENY ❌
  OUTPUT: audit_report (read-only)
  optional input → reflection.py ✅
  NO memory write ❌
  NO conflict resolution ❌
  NO execution trigger ❌

✔ META в DEGRADED_MODE:
  STATUS: ENABLED (lightweight)
  analysis / reflection / memory_audit → lightweight ✅
  correction → вызывается synthesizer'ом как обычно ✅
  meta NEVER affects EPK ❌
  meta NEVER escalates tier ❌

✔ META side-channel DAG INCLUDES:
  analysis.py ✅
  reflection.py ✅
  memory_audit.py ✅
  EXCLUDES correction.py ❌

🤖 AGENTS LAYER
agents/
├── fast_agent.py           # groq/compound-mini
├── deep_agent.py           # groq/compound
├── creative_agent.py       # llama-3.3-70b-versatile
├── safety_agent.py         # POST-REASONING SEMANTIC VALIDATION
└── consensus_engine.py     # openai/gpt-oss-120b (mutex)

✔ safety_agent.py
  ACTIVE on ALLOW / HEAVY_REQUIRED ✅
  skip on DEGRADED / DENY ❌
  LAST in Agent Layer before Consensus ✅
  валидирует reasoning_plan и draft_response
  выдаёт: allow / revise / block
  NO input-level filtering ❌
  НЕ дублирует Safety Layer ✅

✔ consensus_engine.py
  ACTIVE on ALLOW only ✅
  SKIP при HEAVY_REQUIRED (mutex) ❌
  Response Synthesizer агрегирует напрямую при HEAVY ✅

✔ model placement → see SSoT v6.3

💳 ECONOMIC LAYER (TON)
payments/
├── ton_client.py
├── pricing_engine.py
├── access_controller.py
├── usage_meter.py
└── wallet_manager.py

🧠 MEMORY LAYER (STORAGE ONLY)
memory/
├── supabase_store.py
├── vector_memory.py
└── conversation_history.py
✔ storage only / no retrieval logic
✔ Memory Write = independent failure domain
✔ parallel with Event Store
✔ skip on EPK = DENY ❌

🧠 LLM LAYER (INFERENCE ONLY)

✔ LLM TIER CLARIFICATION:
  FAST / GENERAL / HEAVY = тиры мощности, НЕ слои логики ❌
  heavy_input_shaper = self-gated utility, НЕ тир ❌

llm/
├── groq_client.py
├── hf_client.py
├── model_router.py
├── prompt_engine.py           # qwen → thinking: False
├── fallback_handler.py
└── heavy_input_shaper.py
    # self-gated utility
    # ONLY on HEAVY_REQUIRED
    # ALWAYS CALLED, internal NO-OP if not needed
    # SKIP on ALLOW / DEGRADED / DENY
    # decision: context_size / structure / tokens / format
    # uses llama-3.1-8b-instant (NOT as Fast Tier)
    # реализация гибкая: compression / chunking / summarization

🌍 EXTERNAL TOOLS
external/
├── weather.py
├── maps.py
├── search.py
└── web_tools.py

🔔 NOTIFICATIONS LAYER
notifications/
├── email_service.py
└── event_notifier.py
✔ async side-effects only / no control flow

🔐 SECURITY LAYER
security/
├── auth.py
├── encryption.py
├── rate_limiter.py
└── origin_guard.py

📊 OBSERVABILITY (NO FEEDBACK LOOP)
observability/
├── logger.py
├── metrics.py
├── tracing.py
└── sentry.py

✔ OBSERVABILITY ≠ META:
  observability → инфраструктура (system alive? latency?)
  meta          → семантика (ответ логичный? полный?)

🧱 INFRASTRUCTURE
infra/
├── config_loader.py
├── env_validator.py
└── healthcheck.py

🧠 FEATURE LAYER
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
✔ ПОСЛЕ Safety Pass 1 / ДО Safety Pass 2
✔ ДО Intent Engine / ДО любого LLM

🛡 SAFETY LAYER
Pass 1: prompt-guard-2-22m → BEFORE Feature Extraction
Pass 2: prompt-guard-2-86m + safeguard-20b → AFTER Feature Extraction
✔ unavailable → DENY by default
✔ Safety Layer ≠ safety_agent (разные стадии) ✅

🧠 MULTILINGUAL NORMALIZATION
allam-2-7b    → арабский [один вызов, три контекста] ✅
llama-3.3-70b → остальные языки ✅
ДО EPK / NO policy influence ❌

🔁 FINAL EXECUTION DAG (v5.5)

INPUT
↓
Safety Pass 1 (22m) [unavailable → DENY]
↓
Feature Extraction (+ is_voice_input)
↓
Safety Pass 2 (86m + safeguard) [unavailable → DENY]
↓
Auth / Rate Limit / Event Log
↓
Multilingual Normalization
↓
EPK [SOLE POLICY AUTHORITY]
  DENY → EXIT
  ALLOW / DEGRADED / HEAVY_REQUIRED → continue
↓
Memory Retrieval          [skip on DENY]
↓
Embedding Retrieval       [skip on DENY]
↓
Reranker                  [skip on DENY]
↓
analysis.py               [skip on DENY]
  ALLOW / HEAVY → full
  DEGRADED → lightweight
  hints → intent_engine (non-binding)
↓
Intent Engine             [skip on DENY]
↓
Reasoning Engine          [skip on DENY / DEGRADED]
                          [ACTIVE on ALLOW / HEAVY]
↓
Multi-Agent Coordinator   [skip on DENY / DEGRADED]
↓
Orchestrator (EPK signal execution only)
  ├── HEAVY_REQUIRED
  │   → [SKIP FAST] ❌ [SKIP GENERAL] ❌
  │   → heavy_input_shaper (ALWAYS, self-gated)
  │   → Heavy Tier (mandatory)
  │   → safety_agent (mandatory)
  │   → [SKIP CONSENSUS] ❌
  │   → Response Synthesizer (агрегирует)
  ├── ALLOW
  │   → Fast → General → Agents → safety_agent → Consensus
  └── DEGRADED
      → Fast Tier only → Response Synthesizer
↓
Response Synthesizer ← FINAL OUTPUT AUTHORITY
  1. assemble → 2. structure → 3. format
  4. correction (meta/correction.py)
  5. finalize
↓
Speech (orpheus) [voice only]
↓
Event Store ∥ Memory Write [параллельно]
↓
META side-channel [skip on DENY]
  analysis    → уже выполнен в DAG (pre-reasoning)
  reflection  → report → observability / memory_audit
  memory_audit → offline diagnostics
  ALLOW/HEAVY → full / DEGRADED → lightweight
↓
OUTPUT

🚨 RETRIEVAL CONTROL PLANE (v5.5)

retrieval/
├── retrieval_engine.py        # ONLY ENTRY POINT
├── query_preprocessor.py      # query-level ONLY ≠ heavy_input_shaper
├── retrieval_models.py
├── sparse/bm25_engine.py
├── dense/bge_engine.py        # bge-large (primary) / bge-small (fallback)
├── reranker/cross_encoder.py  # bge-reranker-large
├── fusion/hybrid_scorer.py
└── cache/
    ├── query_cache.py
    ├── embedding_cache.py
    ├── rerank_cache.py
    └── ttl_policy.py
✔ ALL access ONLY via retrieval_engine.py
✔ skip on EPK = DENY ❌

context/
├── assembler.py    # детерминированная сборка ≠ heavy_input_shaper
├── serializer.py
└── context_models.py
✔ formatting only / NO LLM ❌

contracts/
├── retrieval_contracts.py
├── context_contracts.py
└── shared_types.py
✔ DTO boundary only

🔐 ENVIRONMENT VARIABLES

📌 CORE: BOT_TOKEN / JWT_SECRET / ENCRYPTION_KEY
🤖 LLM: GROQ_API_KEY / HF_TOKEN
🧠 STORAGE: SUPABASE_URL / SUPABASE_ANON_KEY /
           SUPABASE_SERVICE_ROLE_KEY / REDIS_URL
🔔 EXTERNAL: BREVO_API_KEY / MAPBOX_TOKEN /
            OPENWEATHER_API_KEY / SERPAPI_KEY / SENTRY_DSN
💳 DEPLOY: TON_WALLET / WEBHOOK_URL / ALLOWED_ORIGINS

🧠 🔒 FINAL HARD RULES (v5.5 — SYNCED WITH SSoT v6.3)

✔ EPK → SOLE POLICY AUTHORITY
  OUTPUT: ALLOW | DENY | DEGRADED_MODE | HEAVY_REQUIRED
  DENY → immediate exit

✔ Orchestrator → execution only
  NO policy / NO routing / NO self-activation

✔ Safety Layer
  Pass 1 → before Feature Extraction
  Pass 2 → after Feature Extraction
  unavailable → DENY by default
  ≠ safety_agent ✅

✔ safety_agent
  ACTIVE on ALLOW / HEAVY ✅
  skip on DEGRADED / DENY ❌
  LAST before Consensus ✅
  НЕ дублирует Safety Layer ✅

✔ heavy_input_shaper
  ONLY on HEAVY_REQUIRED ✅
  ALWAYS CALLED, self-gated ✅
  NO-OP if not needed ✅
  SKIP on ALLOW / DEGRADED / DENY ❌
  NOT a tier ❌ NOT an agent ❌

✔ Fast Tier → ALLOW / DEGRADED only
  SKIP on HEAVY / DENY ❌

✔ General Tier → ALLOW only
  SKIP on HEAVY / DEGRADED / DENY ❌

✔ reasoning_engine
  ACTIVE on ALLOW / HEAVY ✅
  skip on DENY / DEGRADED ❌
  control-plane ✅

✔ Heavy Tier
  HEAVY_REQUIRED only ✅
  output → Response Synthesizer напрямую ✅
  Consensus SKIP (mutex) ✅

✔ Response Synthesizer → FINAL OUTPUT AUTHORITY
  агрегирует Heavy при HEAVY_REQUIRED ✅
  вызывает correction.py (step 4) ✅

✔ META LAYER
  NO execution authority ❌
  NO policy authority ❌
  NO EPK influence ❌
  NO tier escalation ❌
  analysis → pre-reasoning DAG step ✅
    NOT called by Orchestrator ❌
  reflection → post-execution report only ✅
  correction → owned meta / executed synthesizer ✅
  memory_audit → read-only ✅
  DEGRADED → lightweight ✅
  DENY → SKIP ❌
  META ≠ COGNITION ≠ OBSERVABILITY ✅

✔ retrieval
  ALL access via retrieval_engine.py
  query_preprocessor ≠ heavy_input_shaper ✅
  skip on DENY ❌

✔ context/assembler ≠ heavy_input_shaper ✅

✔ Multilingual Normalization
  allam-2-7b → арабский [один вызов] ✅
  llama-3.3-70b → остальные ✅
  ДО EPK ✅

✔ Parallel Write
  Event Store ∥ Memory Write
  independent failure domains ✅

✔ Model placement → see SSoT v6.3
  qwen → thinking: False enforced

🧠 💡 FINAL STATUS (v5.5)
✔ synced with SSoT v6.3 — 100%
✔ analysis.py → pre-reasoning DAG step (не post-output)
✔ analysis.py → NOT called by Orchestrator (автоматический шаг)
✔ reflection.py → output: report → observability / memory_audit
✔ correction.py → EXCLUDED from META side-channel
✔ heavy_input_shaper → SKIP on ALLOW / DEGRADED / DENY явно
✔ META при DEGRADED → lightweight, active ✅
✔ META при DENY → SKIP ✅
✔ META ≠ COGNITION ≠ OBSERVABILITY явно
✔ no naming conflicts
✔ no duplicate responsibilities
✔ no hidden gaps
✔ system ready for implementation