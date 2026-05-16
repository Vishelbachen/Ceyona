# CEYONA — Architecture Reference
# v7.0 — 100% Synchronized with Code Reality
# Resolves all contradictions between v5.5 / v6.0 / v6.3

---

## Sync Status

| Document | Status |
|---|---|
| architecture.md (v5.5) | ❌ SUPERSEDED — multi_agent_coordinator rule wrong, 5-step pipeline, no output_normalizer |
| architecture2.md (v6.0) | ❌ SUPERSEDED — source_credibility position wrong, pipeline step count wrong |
| architecture3.md (v6.0) | ❌ SUPERSEDED — source_credibility position wrong, is_heavy heuristic not documented |
| models.md (v6.3) | ❌ SUPERSEDED — 5-step pipeline, no output_normalizer |
| models2.md (v6.4) | ✅ Token caps correct — still superseded on pipeline |
| **architecture-final.md (v7.0)** | ✅ THIS DOCUMENT — single source of truth |

**This document supersedes all previous architecture and models documents.**

---

## 1. Layer Map

```
app/
├── main.py          Entrypoint
├── bootstrap.py     Dependency wiring
└── settings.py      Pydantic settings (env vars)

transport/telegram/                    Ingress only — no domain logic
├── webhook.py          Auth, rate limit, billing trigger
├── update_handler.py   Message routing, tool dispatch, pipeline entry
├── message_router.py   Update type classification
├── callback_handler.py Inline keyboard callbacks
├── vision_handler.py   Image extraction — OUTSIDE EPK DAG (see §Vision)
└── auth_middleware.py  JWT / user verification

core/kernel/                           SOLE POLICY AUTHORITY
├── execution_policy_kernel.py   EPK — outputs ALLOW | DENY | DEGRADED | HEAVY_REQUIRED
├── decision_matrix.py           Tier selection from cost estimate
├── cost_model.py                Cost estimation — imports _MAX_TOKENS from model_router (SSoT)
└── policy_registry.py           Timeout / rate limit constants — DOCUMENTATION ONLY
                                 Contains no executable logic that any module imports.
                                 max_output_tokens values here are for human reference only.
                                 Authoritative values live in model_router._MAX_TOKENS.

core/execution/
└── orchestrator.py   EPK signal execution — no policy, no routing, no self-activation

events/              Append-only event bus — no execution influence

cognition/
├── intent_engine.py             Stateless prompt construction + intent classification
├── intent_examples.py           BGE training examples + Supabase seed function
├── reasoning_engine.py          Reasoning strategy (ALLOW / HEAVY only)
├── multi_agent_coordinator.py   Agent execution fabric (see §Coordinator)
└── response_synthesizer.py      FINAL OUTPUT AUTHORITY (see §Synthesizer Pipeline)

agents/
├── fast_agent.py        groq/compound-mini
├── deep_agent.py        groq/compound
├── creative_agent.py    llama-3.3-70b-versatile  (GENERAL tier)
├── safety_agent.py      Post-reasoning semantic validation (see §Safety Agent)
└── consensus_engine.py  openai/gpt-oss-120b arbiter (ALLOW only, mutex with HEAVY)

meta/                              OBSERVATION / DIAGNOSTICS — NEVER controls execution
├── analysis.py           Pre-reasoning structural hints (non-binding, auto DAG step)
├── reflection.py         Post-execution quality report (side-channel → observability)
├── correction.py         Output preamble/sign-off cleanup — owned meta / step 5 in synthesizer
├── output_normalizer.py  Retrieval artifact stripping — owned meta / step 6 in synthesizer
└── memory_audit.py       Read-only memory diagnostics (side-channel)

retrieval/                         ALL access via retrieval_engine.py only
├── retrieval_engine.py       ONLY ENTRY POINT for memory retrieval
├── query_preprocessor.py     Query normalization (≠ heavy_input_shaper)
├── retrieval_models.py       Data contracts
├── source_credibility.py     Domain trust scoring (see §source_credibility Placement)
├── sparse/bm25_engine.py
├── dense/bge_engine.py       bge-large (primary) / bge-small (fallback)
├── reranker/cross_encoder.py bge-reranker-large
├── fusion/hybrid_scorer.py
└── cache/                    embedding, query, rerank caches + TTL policy

external/
├── weather.py      OpenWeatherMap client
├── maps.py         Mapbox geocoding + routing client
├── search.py       SerpAPI client — calls source_credibility.filter_results()
└── web_tools.py    Tool dispatch router (weather / maps / search)

context/             Deterministic context assembly — no LLM (≠ heavy_input_shaper)
contracts/           DTO boundaries only — shared_types.py is SSoT for enums
llm/                 Inference fabric (see §Token Caps SSoT)
i18n/                All user-facing strings (50+ languages) — strings.py + t.py
memory/              Supabase storage only — no retrieval logic
payments/            TON billing, balance, usage metering
notifications/       Async side-effects only
security/            auth, encryption, rate_limiter, origin_guard
observability/       Infrastructure telemetry (≠ meta)
infra/               config_loader, env_validator, healthcheck
```

---

## 2. Token Caps — Single Source of Truth

**SSoT: `llm/model_router._MAX_TOKENS`**

| Tier | Max output tokens | Primary model |
|---|---|---|
| FAST | 1 024 | llama-3.1-8b-instant |
| GENERAL | 3 072 | llama-3.3-70b-versatile |
| HEAVY | 6 144 | openai/gpt-oss-120b |

**Rules — enforced in every file:**

`model_router._MAX_TOKENS` is the ONLY place where these numbers are defined.

`cost_model.MAX_OUTPUT_CAP` MUST be derived from `model_router._MAX_TOKENS` via import.
It MUST NOT define its own hardcoded dict. Any divergence between these two is a bug.

`policy_registry.py` contains `max_output_tokens` for human documentation only.
No module imports these values. They are informational mirrors, not authority.
If policy_registry and model_router diverge, model_router wins.

**Call chain:**
```
estimate_output_tokens()              ← cost_model.py
  └── uses MAX_OUTPUT_CAP[tier]       ← imported from model_router._MAX_TOKENS
        └── passed to EPKInput        ← execution_policy_kernel.evaluate()
              └── produces EPKDecision
```

---

## 3. Multi-Agent Coordinator — Definitive Role

**This resolves the contradiction between architecture.md v5.5 / models.md v6.3 vs architecture2/3.**

`multi_agent_coordinator.py` IS the agent execution fabric.
It plans and executes agents on behalf of the orchestrator.
It does NOT have policy authority or routing authority.

Correct invariants:

```
multi_agent_coordinator
  ✅ called by orchestrator only
  ✅ receives: AgentPlan + messages + intent + lang
  ✅ dispatches to agents (fast / deep / creative) via _run_agent()
  ✅ runs safety_agent where architecturally required (see §Safety Agent Activation)
  ✅ runs consensus_engine on ALLOW path with use_consensus=True
  ✅ returns CoordinationResult to orchestrator only
  ✅ implements MATH self-verification loop (verify → correct if violations found)
  ❌ NO policy decisions
  ❌ NO routing decisions (tier, model selection)
  ❌ NO Heavy Tier self-activation
  ❌ NO pipeline control beyond agent dispatch
```

**The old invariant "NO прямой вызов агентов" in v5.5 / v6.3 was incorrect.**
Agent execution IS the coordinator's job. It is the execution fabric, not just a planner.

---

## 4. Safety Agent Activation — Definitive Rules

`safety_agent` activation is determined by the `AgentPlan` structure, not by a heuristic.

### Activation table

| EPK path | AgentPlan | safety_agent |
|---|---|---|
| ALLOW + consensus | `use_consensus=True` | ✅ runs before consensus |
| ALLOW + no consensus, DEEP primary | `use_consensus=False`, `fallback=FAST` (fallback ≠ primary) | ✅ runs (HEAVY detection) |
| HEAVY_REQUIRED | `use_consensus=False`, `fallback=FAST` (fallback ≠ primary) | ✅ runs (HEAVY detection) |
| DEGRADED | `primary=FAST`, `fallback=FAST` (fallback == primary) | ❌ skipped |
| EMOTIONAL | `primary=FAST`, `fallback=None` | ❌ must be skipped |
| default GENERAL | `primary=FAST`, `fallback=None` | ❌ must be skipped |

### The is_heavy heuristic — known fragility and correct fix

Current code uses:
```python
is_heavy = not plan.use_consensus and plan.parallel_validators == [] and plan.fallback != plan.primary
```

**Problem:** `EMOTIONAL` plan has `fallback=None`, `primary=FAST` → `None != FAST` → `is_heavy=True` → safety_agent fires incorrectly.

**Correct behavior:** safety_agent MUST NOT run on EMOTIONAL or default-GENERAL paths.

**Architectural fix (to be applied to code):**
Add an explicit `tier: Tier` field to `AgentPlan`. The coordinator checks `plan.tier == Tier.HEAVY` directly, not a heuristic over fallback values. This removes the fragility entirely.

```python
@dataclass(frozen=True)
class AgentPlan:
    primary: AgentType
    fallback: AgentType | None
    tier: Tier                          # ← ADD THIS
    use_consensus: bool = False
    parallel_validators: list[AgentType] = field(default_factory=list)
    temperature: float = 0.7

# In coordinate():
is_heavy = (plan.tier == Tier.HEAVY)   # ← REPLACE heuristic with this
```

**Until the code fix is applied:** `fallback=None` plans (EMOTIONAL, default GENERAL)
must be placed BEFORE the is_heavy block in the execution flow.
The current code already does this — EMOTIONAL returns early via the graceful fallback path.
But this is fragile. The tier field fix is the correct long-term solution.

---

## 5. Response Synthesizer — Definitive Pipeline (7 steps)

**This resolves the contradiction: architecture2/3 documented 6 steps, models.md documented 5 steps. The code implements 7 steps. This document reflects the code.**

```
synthesize(SynthesisInput) → SynthesisResult

Step 1: assemble           _assemble()
        Accept raw LLM output. Identity function currently.
        Future: multi-source aggregation for HEAVY path.

Step 2: telegram_normalize  _normalize_for_telegram()
        Convert LaTeX math → Unicode (^{n} → ⁿ, \frac → a/b, Greek letters).
        Strip Markdown (headers, bold, italic, tables → plain text).
        Must run BEFORE structure/format so downstream sees clean text.
        Owned by: response_synthesizer (inline utility, not a meta module).

Step 3: structure          _structure()
        Intent-aware shaping. Identity function currently.
        Future: intent-specific output structuring.

Step 4: format             _format()
        Whitespace normalization. Collapse excess blank lines.

Step 5: correction         _apply_correction() → meta/correction.py
        Strip preamble filler (Конечно!, Давайте, Sure!, etc.).
        Strip sign-off phrases (Надеюсь, помогло!, Let me know if...).
        Owned by: meta/ | Executed by: synthesizer only.
        Has NO independent authority. Cannot override synthesizer intent.
        EXCLUDED from META side-channel DAG.

Step 6: output_normalizer  _apply_normalizer() → meta/output_normalizer.py
        Strip retrieval contamination artifacts:
          - "по данным в контексте" / "according to the context" (all variants)
          - "(источник 3)" / "(source 2)" inline tags
          - garbled non-ASCII URLs
          - English transport/UI term leaks (translated to target language)
        Owned by: meta/ | Executed by: synthesizer only.
        EXCLUDED from META side-channel DAG.

Step 7: finalize           _finalize() → _truncate()
        Truncate to Telegram 4096-char limit with localised suffix.
```

**Invariants:**
- `correction` and `output_normalizer` are owned by `meta/` but have ZERO independent authority.
- They are called exclusively by `response_synthesizer`. Never called from anywhere else.
- Their position (steps 5 and 6) is fixed. Reordering breaks the cleanup chain.
- Both are excluded from the META side-channel DAG.

---

## 6. source_credibility.py — Definitive Placement

**This resolves the contradiction in architecture3.md which incorrectly placed source_credibility in the retrieval pipeline "after query_preprocessor, before reranker".**

`source_credibility.py` lives in `retrieval/` as a module but has TWO call sites with different purposes:

### Call site A — external/search.py (primary use)

```
SerpAPI organic results
  → _filter_results()  [external/search.py]
      → source_credibility.filter_results()  [retrieval/source_credibility.py]
          → BLOCKED domains: rejected entirely
          → VERY_LOW tier: rejected
          → LOW and above: passed through (max 5 results)
      → returns filtered list to SearchService.search()
  → LLM receives only trusted sources
```

This is the PRIMARY purpose of source_credibility. It guards SerpAPI results
BEFORE they reach the LLM context. It is called by `external/search.py` directly,
not through `retrieval_engine.py`. This is correct by design: SerpAPI results
are not memory documents — they do not go through the retrieval pipeline.

### Call site B — retrieval/retrieval_engine.py (secondary, future use)

```
pgvector similarity_search results (memory documents)
  → source_credibility.score_documents()  [retrieval/source_credibility.py]
      → Currently a pass-through (memory records have no source_url yet)
      → Will apply credibility weighting when MemoryRecord gains source_url field
  → cross_encoder.rerank()
```

This is a RESERVED hook. It does nothing today but is architecturally correct:
when memory records gain source metadata, credibility scoring activates without
requiring changes to retrieval_engine.py.

### Correct description for all documents:

```
source_credibility.py
  Location: retrieval/
  Role: domain trust scoring for retrieval results
  Primary call site: external/search.py → filters SerpAPI results before LLM
  Secondary call site: retrieval_engine.py → reserved hook for memory scoring
  NOT in retrieval pipeline between query_preprocessor and reranker
  NOT called by retrieval_engine for SerpAPI results
```

---

## 7. policy_registry.py — Definitive Role

`policy_registry.py` is **documentation only**. It contains no logic that any
production module imports.

**What it contains:** `PolicyRegistry` dataclass, `TierPolicy` dataclass, `ACTIVE_POLICY` instance.

**What imports it:** nothing in production.

**The hardcoded `max_output_tokens` values in policy_registry (300/1200/3000) are stale.**
They do NOT affect system behavior. The authoritative values are in `model_router._MAX_TOKENS`.

**Correct usage:**
- Human developers may read policy_registry to understand timeout and rate-limit constants.
- No code should import from policy_registry.
- If policy_registry is updated, it does NOT update system behavior — model_router must be updated.

---

## 8. EPK — Execution Policy Kernel

Sole policy authority. Every downstream component obeys its signal.
No component may self-activate.

| Signal | Path |
|---|---|
| `ALLOW` | Full DAG: Fast → General → Agents → safety_agent → Consensus |
| `DENY` | Immediate exit — nothing downstream fires |
| `DEGRADED_MODE` | Fast Tier only → Response Synthesizer directly |
| `HEAVY_REQUIRED` | Skip Fast/General → heavy_input_shaper → Heavy Tier → safety_agent (no Consensus) |

**EPK reads only:** estimated_cost + user_balance.
**EPK does NOT access:** memory, embeddings, LLM, agents, logs, metrics.

---

## 9. Execution DAG (v7.0)

```
INPUT
↓ Safety Gate Pass 1  (22m)             [unavailable → DENY]
↓ Feature Extraction  (+ is_voice_input)
↓ Safety Gate Pass 2  (86m + safeguard-20b)  [unavailable → DENY]
↓ Auth / Rate Limit / Event Log
↓ Multilingual Normalization
    allam-2-7b    → Arabic (one call, three contexts)
    llama-3.3-70b → all other languages
↓ EPK  [SOLE POLICY AUTHORITY]
    DENY            → EXIT
    ALLOW           ↓
    DEGRADED_MODE   ↓
    HEAVY_REQUIRED  ↓
↓ Memory + Embedding Retrieval + Reranker   [skip on DENY]
    source_credibility: called by external/search.py for SerpAPI results (not here)
    source_credibility.score_documents(): reserved hook for memory docs (pass-through today)
↓ analysis.py  [skip on DENY]
    ALLOW / HEAVY → full
    DEGRADED      → lightweight
    output: non-binding hints → intent_engine
↓ Intent Engine  [skip on DENY]
↓ Reasoning Engine  [ALLOW / HEAVY only]
↓ Multi-Agent Coordinator  [ALLOW / HEAVY only]
    called by orchestrator
    dispatches to agents: fast / deep / creative
    runs safety_agent where plan.tier == HEAVY or use_consensus == True
    runs consensus on ALLOW + use_consensus paths
    returns CoordinationResult to orchestrator
↓ Orchestrator  (EPK signal execution ONLY)
    ALLOW          → Fast → General → Agents → safety_agent → Consensus
    HEAVY_REQUIRED → heavy_input_shaper → Heavy Tier → safety_agent (no Consensus)
    DEGRADED_MODE  → Fast Tier only
↓ Response Synthesizer  ← FINAL OUTPUT AUTHORITY
    1. assemble
    2. telegram_normalize  (LaTeX → Unicode, strip Markdown)
    3. structure
    4. format
    5. correction          (meta/correction.py — preamble / sign-off stripping)
    6. output_normalizer   (meta/output_normalizer.py — retrieval artifact stripping)
    7. finalize            (truncate to 4096 chars)
↓ Speech Output  (orpheus)  [voice only — is_voice_input = true]
↓ Event Store  ∥  Memory Write  [parallel, independent failure domains]
↓ META side-channel  [skip on DENY]
    analysis.py   → already executed pre-reasoning (not repeated here)
    reflection.py → report → observability / memory_audit
    memory_audit  → read-only diagnostics
    ALLOW / HEAVY → full  |  DEGRADED → lightweight
    correction + output_normalizer EXCLUDED from side-channel
↓ OUTPUT
```

---

## 10. Model Registry (SSoT v7.0)

### Token caps (SSoT: model_router._MAX_TOKENS)

| Tier | Max output tokens | Primary model |
|---|---|---|
| FAST | 1 024 | llama-3.1-8b-instant |
| GENERAL | 3 072 | llama-3.3-70b-versatile |
| HEAVY | 6 144 | openai/gpt-oss-120b |

### Safety Layer (firewall — before EPK)

| Model | Pass | Unavailable |
|---|---|---|
| prompt-guard-2-22m | Pass 1 — before Feature Extraction | DENY |
| prompt-guard-2-86m + gpt-oss-safeguard-20b | Pass 2 — after Feature Extraction | DENY |

Distinct from `safety_agent` (post-reasoning, agents layer).

### LLM Tiers

**FAST — ALLOW / DEGRADED_MODE only**
- llama-3.1-8b-instant — primary Fast Tier inference
- allam-2-7b — Arabic multilingual normalization (one call, three contexts)
- gemma2-9b-it — Fast Tier fallback (TPM overflow)

**GENERAL — ALLOW only**
- llama-3.3-70b-versatile — primary reasoning + creative + non-Arabic normalization
- qwen/qwen3-32b — structured logic / formatting (`thinking: False` enforced at every call site)
- openai/gpt-oss-20b — constraint-aware general inference

**HEAVY — HEAVY_REQUIRED only**
- openai/gpt-oss-120b — deep multi-step reasoning (primary); Consensus arbiter when Heavy not active (mutex)
- llama-4-scout-17b-16e-instruct — long-context transformation (512K ctx)

### Utility / Specialized Models

| Model | Role | File | Notes |
|---|---|---|---|
| llama-3.1-8b-instant | Input shaping | heavy_input_shaper.py | NOT Fast Tier |
| llama-3.1-8b-instant | Route/POI extraction | external/web_tools.py | Cheap parser, no generation |
| llama-4-scout | Image extraction | vision_handler.py | Specialized role — OUTSIDE EPK DAG |
| groq/compound-mini | Fast Agent | agents/fast_agent.py | Tool-use execution |
| groq/compound | Deep Agent | agents/deep_agent.py | Multi-step tool-use |
| openai/gpt-oss-120b | Consensus arbiter | agents/consensus_engine.py | Mutex with Heavy Tier |

### HF Embeddings

| Model | Role |
|---|---|
| BAAI/bge-large-en-v1.5 | Primary embedding |
| BAAI/bge-small-en-v1.5 | Fast embedding fallback |
| BAAI/bge-reranker-large | Cross-encoder reranking |

All access via `retrieval/retrieval_engine.py`.

### Speech Layer

| Model | Role |
|---|---|
| whisper-large-v3 | Primary STT |
| whisper-large-v3-turbo | Fast STT |
| orpheus-v1-english | English TTS |
| orpheus-arabic-saudi | Arabic TTS |

Activated only when `is_voice_input = true`.

---

## 11. Vision Handler

`transport/telegram/vision_handler.py`
- Uses `llama-4-scout` in Specialized extraction role (image content extraction)
OUTSIDE EPK DAG by design — second ingress into system
Routes via llm/groq_client.py for truncation protection and shared logging
NOT Heavy Tier. NOT subject to EPK policy signal.
Result feeds back into the normal pipeline (update_handler routes to orchestrator with forced_intent)
12. Hard Rules (v7.0)
SSoT contracts
Intent, Tier, TruthMode, EPKDecision, Complexity → contracts/shared_types.py
Max output tokens → llm/model_router._MAX_TOKENS
cost_model.MAX_OUTPUT_CAP → imported from model_router, never independently defined
policy_registry.max_output_tokens → documentation only, never imported
qwen/qwen3-32b → thinking: False enforced at every call site
Parallel write: Event Store ∥ Memory Write — independent failure domains
EPK
Sole policy authority
DENY → immediate exit, nothing downstream fires
Reads only estimated_cost + user_balance
Orchestrator
Execution only — no policy / no routing / no self-activation
Safety Layer vs safety_agent
Safety Layer (Pass 1 + Pass 2) → input firewall, deterministic, before EPK
safety_agent → post-reasoning semantic validation, inside coordinator, after reasoning
They do NOT duplicate each other
safety_agent activation
ALLOW path with consensus → runs before consensus
ALLOW path without consensus, DEEP primary (plan.tier == HEAVY or fallback != primary) → runs
HEAVY_REQUIRED → runs (mandatory)
DEGRADED → skipped
EMOTIONAL → skipped
default GENERAL (FAST primary, no fallback) → skipped
Multi-agent coordinator
IS the agent execution fabric — calls agents on behalf of orchestrator
Called by orchestrator only
Returns results to orchestrator only
NO policy, NO routing, NO model selection, NO tier escalation
Response Synthesizer
FINAL OUTPUT AUTHORITY
7-step pipeline (see §9)
Steps 5 (correction) and 6 (output_normalizer) are owned by meta/ but executed exclusively here
telegram_normalize (step 2) is an inline utility of synthesizer, not a meta module
META Layer
NEVER controls execution
NEVER affects EPK
NEVER escalates tier
analysis → pre-reasoning auto step (non-binding hints)
reflection → post-execution report to observability
correction → synthesizer step 5 only
output_normalizer → synthesizer step 6 only
memory_audit → read-only diagnostics
correction + output_normalizer EXCLUDED from META side-channel DAG
source_credibility
Called by external/search.py for SerpAPI results (primary use)
Called by retrieval_engine.py for memory docs (reserved hook, pass-through today)
NOT in retrieval pipeline between query_preprocessor and reranker
Single module, two call sites, two purposes — no duplication
heavy_input_shaper
ONLY on HEAVY_REQUIRED
ALWAYS CALLED on HEAVY_REQUIRED — self-gated (NO-OP if not needed)
SKIP on ALLOW / DEGRADED / DENY
NOT a tier, NOT an agent
Tier rules
FAST → ALLOW / DEGRADED only
GENERAL → ALLOW only
HEAVY → HEAVY_REQUIRED only (output → Synthesizer directly, no Consensus)
Consensus → ALLOW only (mutex with HEAVY)
Navigation routing
Trigger
Intent
Public transport keywords (маршрут, как добраться, by bus…)
Intent.SEARCH (pre-signal)
Driving point-to-point (no transport keywords)
Intent.MAPS_ROUTE (Mapbox)
13. What Needs Code Changes (Code Debt Log)
This section documents architectural decisions that are correct in this document
but not yet fully reflected in code. Code must be updated to match this document.
#
Issue
File
Fix
1
cost_model.MAX_OUTPUT_CAP is hardcoded (512/2048/4096), not imported from model_router
core/kernel/cost_model.py
Import _MAX_TOKENS from llm.model_router; remove hardcoded dict
2
is_heavy heuristic in coordinate() fires incorrectly for EMOTIONAL
cognition/multi_agent_coordinator.py
Add tier: Tier field to AgentPlan; replace heuristic with plan.tier == Tier.HEAVY
3
Dead code block after return in _correct_math_solution
cognition/multi_agent_coordinator.py
Delete unreachable block (old _run_agent copy-paste)
4
policy_registry.py contains live executable code (ACTIVE_POLICY) that nothing imports
core/kernel/policy_registry.py
Convert to pure comments / remove dataclasses; keep only human-readable constants
Priority order: 1 → 2 → 3 → 4
Issue #1 directly affects EPK cost estimation and tier selection in production.
Issues #2 and #3 are correctness bugs with low production impact today but high risk at scale.
Issue #4 is cleanup only.
14. Environment Variables
Group
Variables
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