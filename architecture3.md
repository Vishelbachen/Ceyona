CEYONA
Architecture Reference
v6.0 — Synced with SSoT v6.3
100% Synchronized — v5.5 + v6.0 merged

1. Layer Map
app/
app/
├── main.py          Bootstrap, entrypoint
├── bootstrap.py     Dependency wiring
└── settings.py      Pydantic settings (env vars)


transport/telegram/
Ingress only — no domain logic, no routing decisions, no policy.
transport/telegram/
├── webhook.py          Auth, rate limit, billing trigger
├── update_handler.py   Message routing, tool dispatch, pipeline entry
├── message_router.py   Update type classification
├── callback_handler.py Inline keyboard callbacks
├── vision_handler.py   Image extraction (llama-4-scout, Specialized role)
└── auth_middleware.py  JWT / user verification


⚠  vision_handler.py — OUTSIDE EPK DAG by design
Uses llama-4-scout in its Specialized extraction role (image content extraction), NOT as Heavy Tier.
Routes via llm/groq_client.py for truncation protection and shared logging.
This is a second ingress into the system that bypasses EPK by architectural intent.


core/kernel/  —  SOLE POLICY AUTHORITY
core/kernel/
├── execution_policy_kernel.py   EPK — outputs ALLOW | DENY | DEGRADED_MODE | HEAVY_REQUIRED
├── decision_matrix.py           Tier selection from cost estimate
├── cost_model.py                Cost estimation (reads token caps from model_router)
└── policy_registry.py          Timeout / rate limit constants (documentation only)


core/execution/
core/execution/
└── orchestrator.py   EPK signal execution — no policy, no routing, no self-activation


events/
Append-only event bus — no execution influence.
events/
├── event_bus.py
├── event_store.py
├── event_types.py
├── event_dispatcher.py
└── event_replay.py


cognition/
cognition/
├── intent_engine.py             Stateless prompt construction + intent classification
├── intent_examples.py           BGE training examples + Supabase seed function
├── reasoning_engine.py          Reasoning strategy (ALLOW / HEAVY only)
├── multi_agent_coordinator.py   Agent execution fabric (called by orchestrator)
└── response_synthesizer.py      FINAL OUTPUT AUTHORITY


agents/
agents/
├── fast_agent.py        groq/compound-mini
├── deep_agent.py        groq/compound
├── creative_agent.py    llama-3.3-70b-versatile  (GENERAL tier)
├── safety_agent.py      Post-reasoning semantic validation  (ALLOW / HEAVY only)
└── consensus_engine.py  openai/gpt-oss-120b arbiter  (ALLOW only, mutex with HEAVY)


meta/  —  OBSERVATION / DIAGNOSTICS ONLY
meta/
├── analysis.py           Pre-reasoning structural hints (non-binding, auto DAG step)
├── reflection.py         Post-execution quality report (side-channel → observability)
├── correction.py         Output cleanup — owned meta / executed by synthesizer step 4
├── output_normalizer.py  Strip retrieval contamination — owned meta / executed step 5
└── memory_audit.py       Read-only memory diagnostics (side-channel)


META INVARIANT: NEVER controls execution | NEVER affects EPK | NEVER escalates tier
correction.py and output_normalizer.py are EXCLUDED from META side-channel DAG.
They are owned by meta but executed exclusively by response_synthesizer.


retrieval/
ALL access via retrieval_engine.py only. Skip on EPK = DENY.
retrieval/
├── retrieval_engine.py       ONLY ENTRY POINT
├── query_preprocessor.py     Query-level only  ≠ heavy_input_shaper
├── retrieval_models.py
├── source_credibility.py     SerpAPI result trust filtering (position: after query_preprocessor, before reranker/fusion)
├── sparse/bm25_engine.py
├── dense/bge_engine.py       bge-large (primary) / bge-small (fallback)
├── reranker/cross_encoder.py bge-reranker-large
├── fusion/hybrid_scorer.py
└── cache/
    ├── query_cache.py
    ├── embedding_cache.py
    ├── rerank_cache.py
    └── ttl_policy.py


context/
Deterministic context assembly — no LLM.  ≠ heavy_input_shaper
context/
├── assembler.py
├── serializer.py
└── context_models.py


contracts/
DTO boundaries only. Single source of truth for shared types.
contracts/
├── retrieval_contracts.py
├── context_contracts.py
└── shared_types.py   ← Intent, Tier, TruthMode, EPKDecision, Complexity


llm/  —  INFERENCE FABRIC
FAST / GENERAL / HEAVY = power tiers, NOT logic layers.  heavy_input_shaper = self-gated utility, NOT a tier.
llm/
├── groq_client.py
├── hf_client.py
├── model_router.py       SSoT for max output tokens (_MAX_TOKENS)
├── prompt_engine.py      qwen → thinking: False enforced
├── fallback_handler.py
└── heavy_input_shaper.py ONLY on HEAVY_REQUIRED / ALWAYS CALLED, self-gated
                          SKIP on ALLOW / DEGRADED / DENY
                          uses llama-3.1-8b-instant (NOT Fast Tier)


external/
external/
├── weather.py
├── maps.py
├── search.py
└── web_tools.py


i18n/
All user-facing strings. Single source of truth for UI text.
i18n/
├── strings.py   All user-facing text (50+ languages)
└── t.py         Public API: t(), lang_instruction(), ow_lang(), normalize_lang()


Remaining Layers
payments/     TON billing, balance, usage metering
memory/       Supabase storage only — no retrieval logic
notifications/ Async side-effects only — no control flow
security/     auth, encryption, rate_limiter, origin_guard
observability/ Infrastructure telemetry (logger, metrics, tracing, sentry)
              ≠ META (infra vs semantics)
infra/        config_loader, env_validator, healthcheck



2. EPK — Execution Policy Kernel
Sole policy authority. Every downstream component obeys its signal. No component may self-activate.

Signal
Path

ALLOW
Full DAG: Fast → General → Agents → safety_agent → Consensus

DENY
Immediate exit — nothing downstream fires

DEGRADED_MODE
Fast Tier only → Response Synthesizer directly

HEAVY_REQUIRED
Skip Fast/General → heavy_input_shaper → Heavy Tier → safety_agent (no Consensus)



3. Execution DAG  (v6.0)
INPUT
↓ Safety Gate Pass 1  (22m)         [unavailable → DENY]
↓ Feature Extraction  (+ is_voice_input)
↓ Safety Gate Pass 2  (86m + safeguard-20b)  [unavailable → DENY]
↓ Auth / Rate Limit / Event Log
↓ Multilingual Normalization
    allam-2-7b  → Arabic (one call, three contexts)
    llama-3.3-70b → all other languages
↓ EPK  [SOLE POLICY AUTHORITY]
    DENY            → EXIT
    ALLOW           ↓
    DEGRADED_MODE   ↓
    HEAVY_REQUIRED  ↓
↓ Memory + Embedding Retrieval + Reranker   [skip on DENY]
    source_credibility.py filters SerpAPI results
↓ analysis.py  [skip on DENY]
    ALLOW / HEAVY → full
    DEGRADED      → lightweight
    output: non-binding hints → intent_engine
↓ Intent Engine  [skip on DENY]
↓ Reasoning Engine  [ALLOW / HEAVY only]
    control-plane: builds reasoning_plan
    Heavy Tier = data-plane (executor)
↓ Multi-Agent Coordinator  [ALLOW / HEAVY only]
    called by orchestrator, returns results to orchestrator
↓ Orchestrator  (EPK signal execution ONLY)
    ALLOW          → Fast → General → Agents → safety_agent → Consensus
    HEAVY_REQUIRED → heavy_input_shaper → Heavy Tier → safety_agent  (no Consensus)
    DEGRADED_MODE  → Fast Tier only
↓ Response Synthesizer  ← FINAL OUTPUT AUTHORITY
    1. assemble_response
    2. structure_output
    3. apply_formatting
    4. apply_correction        (meta/correction.py)
    5. apply_output_normalizer (meta/output_normalizer.py)  ← NEW in v6.0
    6. finalize_output
↓ Speech Output  (orpheus)  [voice only]
↓ Event Store  ∥  Memory Write  [parallel, independent failure domains]
↓ META side-channel  [skip on DENY]
    analysis.py   → already executed pre-reasoning (not repeated)
    reflection.py → report → observability / memory_audit
    memory_audit  → read-only diagnostics
    ALLOW / HEAVY → full
    DEGRADED      → lightweight
    correction.py + output_normalizer.py EXCLUDED from side-channel DAG
↓ OUTPUT


Navigation / Route Query Routing
Trigger
Intent

Public transport keywords (маршрут, как добраться, "by bus"…)
Intent.SEARCH  (pre-signal, bypasses BGE)

Driving point-to-point (no transport keywords, BGE classifies)
Intent.MAPS_ROUTE  (Mapbox Directions)



4. Hard Rules
EPK
✔  Sole policy authority
✔  Output: ALLOW | DENY | DEGRADED_MODE | HEAVY_REQUIRED
✔  DENY → immediate exit, nothing downstream fires

Orchestrator
✔  Execution only — no policy / no routing / no self-activation
✗  NO policy generation
✗  NO routing decisions
✗  NO Heavy Tier self-activation

Safety Layer
✔  Pass 1 (22m)  → BEFORE Feature Extraction
✔  Pass 2 (86m + safeguard-20b)  → AFTER Feature Extraction
✔  unavailable → DENY by default
✔  Safety Layer ≠ safety_agent  (different stages)

safety_agent
✔  ACTIVE on ALLOW / HEAVY_REQUIRED
✔  LAST in Agent Layer before Consensus
✔  validates reasoning_plan and draft_response
✔  output: allow / revise / block
✗  skip on DEGRADED / DENY
✗  NO input-level filtering
✗  does NOT duplicate Safety Layer

heavy_input_shaper
✔  ONLY on HEAVY_REQUIRED
✔  ALWAYS CALLED on HEAVY_REQUIRED — self-gated (NO-OP if not needed)
✔  uses llama-3.1-8b-instant  (NOT Fast Tier model)
✗  SKIP on ALLOW / DEGRADED / DENY
✗  NOT a tier
✗  NOT an agent

Tier Rules
✔  Fast Tier    → ALLOW / DEGRADED only   (skip on HEAVY / DENY)
✔  General Tier → ALLOW only              (skip on HEAVY / DEGRADED / DENY)
✔  Heavy Tier   → HEAVY_REQUIRED only     (output → Synthesizer directly)
✔  Consensus    → ALLOW only              (mutex with HEAVY)

reasoning_engine
✔  ACTIVE on ALLOW / HEAVY_REQUIRED — control-plane
✔  Heavy Tier = data-plane (executor)
✗  skip on DENY / DEGRADED
✗  NO model routing
✗  NO agent execution
✗  NO policy

Response Synthesizer  (FINAL OUTPUT AUTHORITY)
✔  FINAL OUTPUT AUTHORITY — 6-step pipeline
✔  step 4: correction.py   (meta-owned, executed here)
✔  step 5: output_normalizer.py  (meta-owned, executed here)  ← v6.0
✔  aggregates Heavy Tier output on HEAVY_REQUIRED
✗  NO policy
✗  NO agent selection
✗  NO routing
✗  correction / normalizer have NO independent authority

META Layer
✔  analysis.py   → pre-reasoning auto DAG step  (NOT called by Orchestrator)
✔  reflection.py → post-execution report → observability / optional memory_audit
✔  correction.py → owned meta / executed synthesizer step 4
✔  output_normalizer.py → owned meta / executed synthesizer step 5  ← v6.0
✔  memory_audit  → read-only diagnostics
✔  DEGRADED → lightweight (analysis + reflection + memory_audit)
✔  DENY    → SKIP all meta
✗  NO execution authority
✗  NO policy authority
✗  NO EPK influence
✗  NO tier escalation
✗  correction + output_normalizer EXCLUDED from META side-channel DAG
✗  META ≠ COGNITION  ≠ OBSERVABILITY

Retrieval
✔  ALL access via retrieval_engine.py only
✔  source_credibility.py: SerpAPI trust filtering (after query_preprocessor, before reranker)
✔  query_preprocessor ≠ heavy_input_shaper
✔  context/assembler ≠ heavy_input_shaper
✗  skip on DENY

Multilingual Normalization
✔  allam-2-7b  → Arabic (one call, three contexts)
✔  llama-3.3-70b → all other languages
✔  executes BEFORE EPK
✗  NO policy influence

Vision Handler
✔  transport/telegram/vision_handler.py
✔  uses llama-4-scout in Specialized extraction role
✔  OUTSIDE EPK DAG by design
✔  routes via llm/groq_client.py
✗  NOT Heavy Tier
✗  NOT subject to EPK policy

SSoT Contracts
✔  Intent, Tier, TruthMode, EPKDecision, Complexity → contracts/shared_types.py
✔  Max output tokens SSoT → llm/model_router._MAX_TOKENS
✔  cost_model.py reads from model_router dynamically
✔  policy_registry.py mirrors for documentation only
✔  qwen → thinking: False enforced in prompt_engine.py
✔  Parallel write: Event Store ∥ Memory Write — independent failure domains


5. Environment Variables
Core
BOT_TOKEN, JWT_SECRET, ENCRYPTION_KEY

LLM
GROQ_API_KEY, HF_TOKEN

Storage
SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, REDIS_URL

External
BREVO_API_KEY, MAPBOX_TOKEN, OPENWEATHER_API_KEY, SERPAPI_KEY, SENTRY_DSN

Deploy
TON_WALLET, WEBHOOK_URL, ALLOWED_ORIGINS



6. Sync Status  (v5.5 → v6.0)
This document is the result of merging architecture v5.5 and v6.0. Below is the delta.

Change
v5.5
v6.0  (this doc)

output_normalizer.py in synthesizer
5-step pipeline (no normalizer)
6-step pipeline — step 5 = output_normalizer. CRITICAL: changes deterministic output order.

source_credibility.py in retrieval
Not present
After query_preprocessor, before reranker/fusion. Trust scoring for SerpAPI results.

vision_handler.py (second ingress)
Not present
OUTSIDE EPK DAG by design. llama-4-scout Specialized role. Routes via groq_client.py.

i18n layer
Strings inside cognition/
i18n/strings.py + t.py. All user-facing text. 50+ languages. Additive, non-breaking.

intent_examples.py
intent_engine stateless only
BGE training seeds + Supabase seed function. Additive, non-breaking.

cost_model coupling
Implicit
cost_model.py explicitly reads model_router._MAX_TOKENS. SSoT enforced.


✔  SYNC STATUS: 100%
Core execution model: synced  |  Pipeline order: synced  |  All subsystems: synced
v6.0 = v5.5 + 4 additive subsystems + 1 modified pipeline step (output_normalizer)
