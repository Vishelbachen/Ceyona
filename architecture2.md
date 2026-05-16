# ARCHITECTURE v6.0 — Ceyona

## Layer Map

```
app/                         Bootstrap, settings, entrypoint
transport/telegram/          Ingress only — no domain logic
  webhook.py                 Auth, rate limit, billing trigger
  update_handler.py          Message routing, tool dispatch, pipeline entry
  message_router.py          Update type classification
  callback_handler.py        Inline keyboard callbacks
  vision_handler.py          Image extraction (llama-4-scout, Specialized role)
  auth_middleware.py         JWT / user verification

core/kernel/                 Policy engine
  execution_policy_kernel.py EPK — SOLE POLICY AUTHORITY
  decision_matrix.py         Tier selection from cost estimate
  cost_model.py              Cost estimation (reads token caps from model_router)
  policy_registry.py         Timeout / rate limit constants (documentation only)

core/execution/
  orchestrator.py            EPK signal execution — no policy, no routing

events/                      Append-only event bus (no execution influence)

cognition/
  intent_engine.py           Stateless prompt construction + intent classification
  intent_examples.py         BGE training examples + Supabase seed function
  reasoning_engine.py        Reasoning strategy selection (ALLOW / HEAVY only)
  multi_agent_coordinator.py Agent orchestration (calls agents on behalf of orchestrator)
  response_synthesizer.py    FINAL OUTPUT AUTHORITY

agents/
  fast_agent.py              groq/compound-mini
  deep_agent.py              groq/compound
  creative_agent.py          llama-3.3-70b-versatile (GENERAL tier)
  safety_agent.py            Post-reasoning semantic validation (ALLOW / HEAVY only)
  consensus_engine.py        openai/gpt-oss-120b arbiter (ALLOW only, mutex with HEAVY)

payments/                    TON billing, balance, usage metering
memory/                      Supabase storage only — no retrieval logic
llm/                         Inference fabric (groq_client, model_router, prompt_engine, etc.)
external/                    weather, maps, search, web_tools
i18n/                        strings.py (all user-facing text), t.py (API)
notifications/               Async side-effects only
security/                    Auth, encryption, rate limiter, origin guard
observability/               Infrastructure telemetry (logger, metrics, tracing, sentry)
infra/                       Config loader, env validator, healthcheck

retrieval/                   ALL access via retrieval_engine.py only
  dense/, sparse/, fusion/   BGE + BM25 + RRF
  reranker/                  cross_encoder (bge-reranker-large)
  cache/                     embedding, query, rerank caches + TTL policy
  source_credibility.py      SerpAPI result filtering

context/                     Deterministic context assembly — no LLM
contracts/                   DTO boundaries only (shared_types, retrieval, context)

meta/                        Observation / diagnostics — NEVER controls execution
  analysis.py                Pre-reasoning structural hints (non-binding)
  reflection.py              Post-execution quality report (side-channel)
  correction.py              Output cleanup — owned by meta, called by synthesizer
  output_normalizer.py       Strip retrieval contamination artifacts
  memory_audit.py            Read-only memory diagnostics (side-channel)
```

---

## Key Invariants

### EPK (Execution Policy Kernel)
Sole policy authority. Outputs one of four signals:

| Signal | Path |
|---|---|
| `ALLOW` | Full DAG: Fast → General → Agents → safety_agent → Consensus |
| `DENY` | Immediate exit — nothing downstream fires |
| `DEGRADED_MODE` | Fast Tier only → Response Synthesizer directly |
| `HEAVY_REQUIRED` | Skip Fast/General → heavy_input_shaper → Heavy Tier → safety_agent → Synthesizer (no Consensus) |

### Contracts — single source of truth
`Intent`, `Tier`, `TruthMode`, `EPKDecision`, `Complexity` all live in `contracts/shared_types.py`.
Every layer imports from there. `cognition/` does not own `Intent`.

### Token caps — single source of truth
`llm/model_router._MAX_TOKENS` is the SSoT for max output tokens.
`cost_model.py` reads from it dynamically. `policy_registry.py` mirrors it for documentation.
**Never define token caps in multiple places independently.**

### Vision handler
`transport/telegram/vision_handler.py` uses `llama-4-scout` in its **Specialized extraction role**
(image content extraction), not as Heavy Tier. This call is outside the EPK DAG by design.
It routes through `llm/groq_client.py` for truncation protection and shared logging.

### Routing: directions queries
Two paths for navigation/route queries:
1. **Public transport keywords** (`маршрут`, `как добраться`, `by bus`, …) → `Intent.SEARCH` (pre-signal, bypasses BGE)
2. **Driving point-to-point** (no transport keywords, BGE classifies) → `Intent.MAPS_ROUTE` (Mapbox Directions)

### Meta layer
Observes only. Never controls execution, never escalates tier, never affects EPK.

| File | When | Output |
|---|---|---|
| `analysis.py` | Pre-reasoning (auto step) | Non-binding hints |
| `reflection.py` | Post-output (async) | Quality report → observability |
| `correction.py` | Inside synthesizer step 4 | Cleaned text |
| `output_normalizer.py` | Inside synthesizer step 6 | Decontaminated text |
| `memory_audit.py` | Post-output (async) | Read-only diagnostic report |

`correction.py` and `output_normalizer.py` are excluded from the META side-channel DAG —
they are owned by meta but executed exclusively by `response_synthesizer`.

### Multi-agent coordinator
`multi_agent_coordinator.py` is called by the orchestrator and executes agents on its behalf.
Architecturally it is the agent execution fabric — it plans and runs agents, then returns
results to the orchestrator. It does not have policy or routing authority.

### Parallel writes
After output: `Event Store ∥ Memory Write` run in independent failure domains.

---

## Execution DAG

```
INPUT
↓ Safety Gate Pass 1 (22m) — unavailable → DENY
↓ Feature Extraction
↓ Safety Gate Pass 2 (86m + safeguard-20b) — unavailable → DENY
↓ Auth / Rate Limit / Event Log
↓ Multilingual Normalization (allam-2-7b → Arabic / llama-3.3-70b → others)
↓ EPK [SOLE POLICY AUTHORITY]
    DENY           → EXIT
    ALLOW          ↓
    DEGRADED_MODE  ↓
    HEAVY_REQUIRED ↓
↓ Memory + Embedding Retrieval + Reranker  [skip on DENY]
↓ analysis.py (full on ALLOW/HEAVY, lightweight on DEGRADED)  [skip on DENY]
↓ Intent Engine  [skip on DENY]
↓ Reasoning Engine  [ALLOW / HEAVY only]
↓ Multi-Agent Coordinator  [ALLOW / HEAVY only]
↓ Orchestrator (execution only)
    ALLOW          → Fast → General → Agents → safety_agent → Consensus
    HEAVY_REQUIRED → heavy_input_shaper → Heavy Tier → safety_agent (no Consensus)
    DEGRADED_MODE  → Fast Tier only
↓ Response Synthesizer (assemble → structure → format → correction → normalizer → finalize)
↓ Speech Output (orpheus) [voice only]
↓ Event Store ∥ Memory Write [parallel]
↓ META side-channel: reflection + memory_audit  [skip on DENY]
↓ OUTPUT
```

---

## Environment Variables

| Group | Variables |
|---|---|
| Core | `BOT_TOKEN`, `JWT_SECRET`, `ENCRYPTION_KEY` |
| LLM | `GROQ_API_KEY`, `HF_TOKEN` |
| Storage | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `REDIS_URL` |
| External | `BREVO_API_KEY`, `MAPBOX_TOKEN`, `OPENWEATHER_API_KEY`, `SERPAPI_KEY`, `SENTRY_DSN` |
| Deploy | `TON_WALLET`, `WEBHOOK_URL`, `ALLOWED_ORIGINS` |