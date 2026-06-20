# CEYONA — MODEL REGISTRY
Version: 7.3 — Anti-Drift Edition
Status: Active Source of Truth
Supersedes: models1.md, models2.md (all previous versions)

This document defines ONLY:
- approved models and their roles
- tier assignments and eligibility
- activation rules and constraints
- execution DAG

This document MUST NOT define: orchestration, execution policy, pricing, billing.
Pricing and token economics → economic.md

---

## INFRASTRUCTURE SPLIT — READ FIRST

Models in this registry run on two separate providers:

**Groq (api.groq.com)** — primary inference provider
API key: `GROQ_API_KEY`
Billing: Groq account
Models: all LLM tiers, Safety Layer, Agent Layer, Speech Layer, allam-2-7b

**HuggingFace Serverless (api-inference.huggingface.co)** — embedding + reranking only
API key: `HF_TOKEN`
Billing: HuggingFace account (separate from Groq)
Models: BAAI/bge-large-en-v1.5, BAAI/bge-small-en-v1.5, BAAI/bge-reranker-large

These are independent cost streams. Failure of one does NOT imply failure of the other.
Quota exhaustion on HF does NOT trigger Groq fallback — it degrades retrieval quality.

---

## 1. SAFETY LAYER (input observability — NON-BLOCKING)

**Provider: Groq**
*Prices: economic.md §1.2*

```
meta-llama/llama-prompt-guard-2-22m    → SIGNAL LOGGER (Pass 1)
meta-llama/llama-prompt-guard-2-86m    → SIGNAL LOGGER (Pass 2)
openai/gpt-oss-safeguard-20b           → SIGNAL LOGGER (Pass 2, observability)
```

**Role:** input signal logging only. NO generation. NO reasoning synthesis. NO blocking.

**Execution order:**
- 22m: BEFORE Feature Extraction
- 86m + safeguard-20b: AFTER Feature Extraction, BEFORE EPK

**Blocking policy: NON-BLOCKING.**
Both passes always return PASS. Suspicious signals are logged for monitoring only.

**Rationale:** prompt-guard models and gpt-oss-safeguard-20b produce unacceptable
false-positive rates on Russian, Arabic, and short casual messages — blocking at
input level causes full outage for legitimate users without meaningful safety gain.

**Unavailability rule:** Safety model unavailable → pass-through. Observability
degrades, execution continues. No DENY on model unavailability.

**Sole blocking authority: safety_agent** (post-reasoning, semantic, full context).

**Critical distinction:**
- Safety Layer → input signal observability (non-blocking)
- safety_agent → post-reasoning semantic validator, BLOCKING authority
- These are NOT duplicates. Both are required.

---

## 2. FAST TIER (ALLOW / DEGRADED_MODE only)

**Provider: Groq**
*Prices: economic.md §1.1*

```
llama-3.1-8b-instant  → PRIMARY: structural signal compression, shallow inference
allam-2-7b            → MULTILINGUAL: Arabic normalization (one call, three contexts)
```

> **Note:** gemma2-9b-it removed — deprecated by Groq, August 2025. No active fallback for FAST tier TPM overflow.

**Activation:** ALLOW or DEGRADED_MODE signals from EPK.
**Skip on:** HEAVY_REQUIRED, DENY.

**allam-2-7b contexts (NOT three instances):**
1. Fast Tier preprocessing
2. Specialized Layer (TTS pipeline)
3. Multilingual normalization (Arabic routing)
One model, one call per request where needed.

**llama-3.1-8b-instant note:**
When EPK = HEAVY_REQUIRED, llama-3.1-8b-instant is used ONLY in heavy_input_shaper.py
and web_tools.py (route/POI extraction). It is NOT acting as Fast Tier in those contexts.

---

## 3. GENERAL TIER (ALLOW only)

**Provider: Groq**
*Prices: economic.md §1.1*

```
llama-3.3-70b-versatile → PRIMARY: reasoning core + creative engine + non-Arabic normalization
qwen/qwen3-32b          → structured logic / formatting engine
openai/gpt-oss-20b      → constraint-aware general inference
```

**Activation:** ALLOW signal from EPK only.
**Skip on:** HEAVY_REQUIRED, DEGRADED_MODE, DENY.

**Critical:** FAST / GENERAL / HEAVY are tiers of model capability within the LLM layer.
They are NOT cognitive layers. They are NOT logic layers.

**Model specialization within GENERAL tier (architecture.md §45):**
Intent-based preferred_model hint is set in RoutingProfile by _resolve_routing().
model_router uses hint to select within _TIER_MODELS[GENERAL]. Primary is fallback.

| Intent group | Preferred model | Reason |
|---|---|---|
| CONVERSATION, EMOTIONAL, CREATIVE | llama-3.3-70b-versatile | expressiveness, tone |
| QUESTION, INSTRUCTION, ANALYSIS | llama-3.3-70b-versatile | reasoning, explanation |
| CODE, MATH, EXAM | qwen/qwen3-32b | structured output, instruction following |
| SEARCH, RECOMMENDATION | llama-3.3-70b-versatile | synthesis, summarization |
| WEATHER, MAPS, MAPS_POI, MAPS_ROUTE | verbatim (no LLM) | structured data — bypasses model |

**qwen/qwen3-32b:** thinking mode MUST be explicitly disabled at every call site: `"thinking": False`

---

## 4. HEAVY TIER (HEAVY_REQUIRED only)

**Provider: Groq**
*Prices: economic.md §1.1*

```
openai/gpt-oss-120b                           → PRIMARY: deep multi-step reasoning
                                                SECONDARY: Consensus arbiter (mutex — see §8)
meta-llama/llama-4-scout-17b-16e-instruct     → long-context transformation (512K context)
```

**Activation:** EPK = HEAVY_REQUIRED ONLY.
**Self-activation:** forbidden. Orchestrator executes the signal, does NOT generate it.

**Output rule:** Heavy Tier output → directly to Response Synthesizer. Consensus SKIP (mutex).

**Hard invariants:**
- each subsystem = isolated capability domain
- NO shared state
- NO hierarchical dominance
- NO cross-decision influence

---

## 5. HEAVY INPUT SHAPER (self-gated utility — NOT a tier)

**Provider: Groq (uses llama-3.1-8b-instant)**
`llm/heavy_input_shaper.py`

**Role:** prepare input for Heavy Tier execution.

**Activation:**
- ONLY when EPK = HEAVY_REQUIRED
- ALWAYS CALLED on HEAVY_REQUIRED (self-gated internally)
- Internal gating: shaping needed → execute | not needed → NO-OP (return input as-is)
- SKIP on ALLOW, DEGRADED_MODE, DENY

**Model used:** llama-3.1-8b-instant — NOT as Fast Tier

**Constraints:** NO reasoning, NO final output generation.

---

## 6. AGENT LAYER (tool-use execution fabric)

**Provider: Groq (compound models wired ✅)**
*Prices: economic.md §1.3*

```
groq/compound      → IMPLEMENTED ✅ as AgentType.COMPOUND_DEEP
                     agents/compound_agent.run_deep()
                     Tier.GENERAL path — multi-step tool use

groq/compound-mini → IMPLEMENTED ✅ as AgentType.COMPOUND_FAST
                     agents/compound_agent.run_fast()
                     Tier.FAST path — single-step tool use
```

**Agent dispatch for tool intents (SEARCH, WEATHER, MAPS, MAPS_POI, MAPS_ROUTE):**
```
Tier.FAST    → AgentType.COMPOUND_FAST  (groq/compound-mini)
Tier.GENERAL → AgentType.COMPOUND_DEEP  (groq/compound)
Fallback     → AgentType.DEEP           (llama-3.3-70b-versatile — plain text synthesis)
```

**Supported tools:** web_search, get_weather, geocode, get_route

**Agent models (май 2026):**
- FAST_AGENT_MODEL: `groq/compound-mini` — AgentType.COMPOUND_FAST
- DEEP_AGENT_MODEL: `groq/compound` — AgentType.COMPOUND_DEEP

**✅ БАГ 13.1 ЗАКРЫТ (май 2026):** compound переведён в режим синтезатора.
Groq compound не принимает кастомные tool schemas (`tools=` → HTTP 400).
Решение: весь retrieval (search/weather/maps) выполняется orchestrator до вызова compound.
Контекст передаётся через PromptContext → user turn. Compound синтезирует, не ищет.
`tool_choice` убран. Подробности: audit.md §13.1 (закрытые задачи), architecture.md §40.
**Max tool rounds:** 3 (bounded — §2.2)
**Role:** tool selection authority, multi-step execution.
**No policy authority.** No system governance. No Heavy Tier activation.

---

## 7. SAFETY AGENT (post-reasoning semantic validation)

**Provider: internal (no external model call — rule-based + LLM via existing tier)**
`agents/safety_agent.py`

**Position:** LAST in agent execution, before Consensus (on consensus path).

**Activation rules:**

| Path | Condition | safety_agent |
|---|---|---|
| ALLOW + consensus | use_consensus=True | ✅ runs before consensus |
| ALLOW + DEEP primary, no consensus | fallback ≠ primary | ✅ runs |
| HEAVY_REQUIRED | always | ✅ mandatory |
| DEGRADED_MODE | | ❌ skipped |
| EMOTIONAL intent | primary=FAST, fallback=None | ❌ skipped |
| default GENERAL | primary=FAST, fallback=None | ❌ skipped |

**Responsibilities:** validate reasoning_plan + draft_response, detect unsafe emergent content.
**Verdict:** allow / revise / block.

**NOT responsible for:** input-level filtering, deterministic cascade, model routing.

---

## 8. CONSENSUS LAYER

**Provider: Groq**

```
openai/gpt-oss-120b → CONSENSUS ARBITER
```

**Activation:** ALLOW path with use_consensus=True ONLY.
**Mutex:** SKIP when HEAVY_REQUIRED (openai/gpt-oss-120b cannot be both simultaneously).
**On HEAVY_REQUIRED:** Response Synthesizer aggregates Heavy Tier output directly.
**Max tokens for arbitration:** route_max_tokens(Tier.GENERAL) — arbitration, not generation.

---

## 9. MULTI-AGENT COORDINATOR

`cognition/multi_agent_coordinator.py`

The coordinator IS the agent execution fabric.
It plans and executes agents on behalf of the orchestrator.
Called by orchestrator ONLY. Returns CoordinationResult to orchestrator ONLY.
No policy decisions. No tier or model selection. No self-activation of Heavy Tier.

→ Full authority boundaries and invariants: architecture.md §16.

---

## 10. RESPONSE SYNTHESIZER

`cognition/response_synthesizer.py`

**Role:** FINAL OUTPUT AUTHORITY.

**7-step pipeline (code-authoritative):**

```
1. assemble           — accept raw LLM output
2. normalize_telegram — LaTeX→Unicode, strip Markdown (NOT a meta module)
3. structure          — intent-aware shaping (identity today, reserved)
4. format             — whitespace normalization
5. correction         — meta/correction.py (preamble/sign-off stripping)
6. output_normalizer  — meta/output_normalizer.py (retrieval contamination cleanup:
                         invisible chars, source attribution tags, garbled URLs,
                         English term leaks → native language, vision meta openers)
7. finalize           — truncate to Telegram 4096 chars
```

Steps 5 and 6: owned by meta/ but executed exclusively by synthesizer, never independently.
correction + output_normalizer are EXCLUDED from META side-channel DAG.

→ Full ownership rules and ordering rationale: architecture.md §19.

---

## 11. META LAYER

```
meta/
├── analysis.py           PRE-REASONING step (auto DAG, before intent_engine) [IMPLEMENTED ✅]
├── reflection.py         POST-EXECUTION side-channel
├── correction.py         INLINE — owned meta/, executed by synthesizer step 5 ONLY
├── output_normalizer.py  INLINE — owned meta/, executed by synthesizer step 6 ONLY
└── memory_audit.py       OFFLINE DIAGNOSTICS side-channel
```

**Key invariant:** META LAYER observes system. NEVER controls system. NEVER participates in execution decisions.

**META ≠ COGNITION:** meta observes and evaluates. cognition thinks and decides.
**META ≠ OBSERVABILITY:** observability = infrastructure telemetry (system alive? latency? errors?).
meta = semantic quality (is the answer logical? complete? contradictory?).

### analysis.py
**Status: IMPLEMENTED ✅** (май 2026)
- Position: pre-reasoning DAG step (automatic, before intent_engine)
- Wired: `update_handler → analyse() → OrchestratorRequest.analysis_report → intent_engine.classify(analysis_hints=...)`
- Activation: ALLOW/HEAVY_REQUIRED (full), DEGRADED (lightweight), DENY (skip)
- Output: non-binding hints → intent_engine (zero authority, MAY be ignored)

### reflection.py
- Position: post-execution side-channel (async, non-blocking)
- Activation: ALLOW/HEAVY (full), DEGRADED (lightweight), DENY (skip)
- Output: reflection_report → observability (logs/traces) + optional memory_audit input

### correction.py
- Ownership: meta/ | Execution: ONLY via synthesizer step 5
- Excluded from META side-channel DAG
- Does: preamble/sign-off stripping (Конечно!, Sure!, Давайте, etc.)

### output_normalizer.py
- Ownership: meta/ | Execution: ONLY via synthesizer step 6
- Excluded from META side-channel DAG
- Does: strip invisible chars, source attribution tags (источник N / source N),
        garbled non-ASCII URLs, English transport/UI term leaks in non-English responses,
        vision meta openers (when from_vision=True)

### memory_audit.py
- Position: offline diagnostics side-channel (async, non-blocking)
- Activation: ALLOW/HEAVY/DEGRADED (active), DENY (skip)
- Output: read-only audit_report → optional input for reflection.py

---

## 12. SPECIALIZED LAYER

**Provider: Groq (all models in this section)**
*Prices: economic.md §1.4*

```
whisper-large-v3                              → PRIMARY SPEECH-TO-TEXT (ASR)
whisper-large-v3-turbo                        → FAST SPEECH-TO-TEXT (ASR)
canopylabs/orpheus-v1-english                 → ENGLISH SPEECH SYNTHESIS (TTS)
canopylabs/orpheus-arabic-saudi               → ARABIC SPEECH SYNTHESIS (TTS)
allam-2-7b                                    → MULTILINGUAL NLP (Arabic anchor, also in FAST tier)
meta-llama/llama-4-scout-17b-16e-instruct     → IMAGE EXTRACTION (vision_handler.py — OUTSIDE EPK DAG)
```

**Speech activation:** is_voice_input = true ONLY.
**Vision (meta-llama/llama-4-scout-17b-16e-instruct):** specialized extraction role, NOT Heavy Tier,
OUTSIDE EPK DAG by design, routes via groq_client, result feeds back via update_handler forced_intent.

---

## 13. HF EMBEDDINGS + RETRIEVAL

⚠️ **Provider: HuggingFace Serverless — NOT Groq**
API key: `HF_TOKEN` (separate from `GROQ_API_KEY`)
Billing: HuggingFace account (separate cost stream — see economic.md §1.5)
These models do NOT appear in the Groq available_models list. This is expected and correct.

*Prices: economic.md §1.5*

```
BAAI/bge-large-en-v1.5  → PRIMARY EMBEDDING   (HuggingFace Inference API)
BAAI/bge-small-en-v1.5  → FAST EMBEDDING FALLBACK  (HuggingFace Inference API)
BAAI/bge-reranker-large  → CROSS-ENCODER RERANKING  (HuggingFace Inference API)
```

**Strict separation:**
- bge-large / bge-small → ONLY generate vectors
- bge-reranker-large → ONLY reorders candidates, NEVER generates embeddings,
  NEVER influences EPK / agents / cognition

All access via `retrieval/retrieval_engine.py` only.

**Quota management:** HF serverless has rate limits independent of Groq.
Exhaustion degrades retrieval quality — does NOT cause LLM failure.
Monitor HF usage separately from Groq usage.

---

## 14. SOURCE CREDIBILITY

**Provider: none (internal logic, no model calls)**
`retrieval/source_credibility.py`

**Primary call site:** external/search.py → filters web search results (Tavily / SerpAPI / SearXNG) BEFORE LLM exposure.
**Secondary call site:** retrieval_engine.py → reserved hook for memory document scoring (pass-through today).

NOT positioned between query_preprocessor and reranker in the retrieval pipeline.
NOT advisory only — actively blocks BLOCKED-tier domains, filters VERY_LOW-tier sources.

---

## 15. FEATURE LAYER

```python
features = {
    "token_count":      int,
    "char_count":       int,
    "newline_density":  float,
    "has_code_block":   bool,
    "has_json_shape":   bool,
    "has_math_symbols": bool,
    "unicode_entropy":  float,
    "is_voice_input":   bool,
}
```

Extracted: AFTER Safety Gate Pass 1 (22m), BEFORE Safety Gate Pass 2 (86m + safeguard).
Used for: EPK cost estimation, routing hints, is_voice_input trigger.

---

## 16. COMPLEXITY MODEL

```
LOW      → chat / short text
MEDIUM   → structured input
HIGH     → logs / code / structured blocks
CRITICAL → mixed modality / context_length > 32K tokens → EPK: HEAVY_REQUIRED
```

---

## 17. EPK SIGNALS AND PATHS

→ architecture.md §17 (canonical). Summary:
- **ALLOW:** full DAG — Fast → General → Agents → safety_agent → Consensus → Synthesizer
- **DENY:** immediate exit
- **DEGRADED_MODE:** Fast Tier only, skip Reasoning/Agents/Consensus
- **HEAVY_REQUIRED:** heavy_input_shaper → Heavy Tier → safety_agent, Consensus SKIP

---

## 18. FINAL EXECUTION DAG

→ architecture.md §4 (canonical execution lifecycle) and §18 (math/constraint cognition lifecycle).
This file defines model assignments only. DAG is owned by architecture.md.

---

## 19. AUTHORITY BOUNDARIES (SEALED)

```
EPK                  → SOLE POLICY AUTHORITY
Orchestrator         → execution control only
Response Synthesizer → FINAL OUTPUT AUTHORITY
model_router         → model routing only (tier → model name + API limits)
cost_model           → economic calculation only (prices + estimation caps)
decision_matrix      → tier selection on ALLOW path only (no policy)
multi_agent_coordinator → agent execution fabric (not policy)
safety_agent         → post-reasoning validation only
heavy_input_shaper   → self-gated input prep only
analysis.py          → non-binding hints only
reflection.py        → read-only post-execution report
correction.py        → preamble cleanup, no authority, synthesizer step 5 only
output_normalizer.py → artifact cleanup, no authority, synthesizer step 6 only
memory_audit.py      → read-only diagnostics only
source_credibility   → domain trust filtering only
```

**Hard prohibitions:**
```
memory / embeddings / reranker → no routing authority
LLM → no governance
meta → no execution authority, no policy, no EPK influence, no tier escalation
agents → no policy selection (tool selection only)
```

---

## 20. WRITE ISOLATION

Event Store + Memory Write: parallel execution, independent failure domains.
Failure of one does NOT block the other.

---

## 21. NAVIGATION ROUTING

| Trigger | Intent |
|---|---|
| Public transport keywords (маршрут, как добраться, by bus, transit...) | Intent.SEARCH (pre-signal) |
| Driving point-to-point (no transport keywords) | Intent.MAPS_ROUTE (Mapbox) |

---

## 22. AVAILABLE GROQ MODELS (May 2026)

Complete list of models available on Groq API as of May 2026.
Cross-reference with model assignments above to verify no gaps.

```json
[
  "whisper-large-v3",
  "meta-llama/llama-4-scout-17b-16e-instruct",
  "allam-2-7b",
  "llama-3.3-70b-versatile",
  "groq/compound-mini",
  "openai/gpt-oss-safeguard-20b",
  "meta-llama/llama-prompt-guard-2-22m",
  "meta-llama/llama-prompt-guard-2-86m",
  "canopylabs/orpheus-v1-english",
  "groq/compound",
  "whisper-large-v3-turbo",
  "qwen/qwen3-32b",
  "canopylabs/orpheus-arabic-saudi",
  "openai/gpt-oss-20b",
  "openai/gpt-oss-120b",
  "llama-3.1-8b-instant"
]
```

**Assignment coverage:**
| Model | Role | Section |
|---|---|---|
| llama-3.1-8b-instant | FAST tier primary | §2 |
| llama-3.3-70b-versatile | GENERAL tier primary | §3 |
| qwen/qwen3-32b | GENERAL tier | §3 |
| openai/gpt-oss-20b | GENERAL tier | §3 |
| openai/gpt-oss-120b | HEAVY tier primary + Consensus | §4, §8 |
| meta-llama/llama-4-scout-17b-16e-instruct | HEAVY tier secondary + Vision | §4, §12 |
| groq/compound | Agent Layer (compound_agent deep) | §6 |
| groq/compound-mini | Agent Layer (compound_agent fast) | §6 |
| meta-llama/llama-prompt-guard-2-22m | Safety Gate Pass 1 | §1 |
| meta-llama/llama-prompt-guard-2-86m | Safety Gate Pass 2 | §1 |
| openai/gpt-oss-safeguard-20b | Safety Gate Pass 2 | §1 |
| whisper-large-v3 | ASR primary | §12 |
| whisper-large-v3-turbo | ASR fast | §12 |
| canopylabs/orpheus-v1-english | TTS English | §12 |
| canopylabs/orpheus-arabic-saudi | TTS Arabic | §12 |
| allam-2-7b | Multilingual + FAST tier | §2, §12 |

---

## 23. SEARCH PROVIDERS (external — NOT Groq models)

Search providers are external services used by `external/search.py`.
They are NOT Groq models. They are NOT registered in the Groq available_models list.
They do NOT appear in §22. This is expected and correct.

**Three-tier fallback chain (architecture §28):**

```
Priority  Provider  Key/URL            Tier
1         Tavily    TAVILY_API_KEY     primary  — LLM-optimised, 1000 req/mo free
2         SerpAPI   SERPAPI_KEY        secondary — hotel pack support, 250 req/mo free
3         SearXNG   SEARXNG_URL        tertiary  — self-hosted meta-search, no rate limit
```

**Configuration:**
- All three configured via `app/settings.py` and environment variables
- SearXNG runs as Docker sidecar (`docker-compose.yml`) on `ai-network`
- SEARXNG_SECRET_KEY required in docker-compose for stable JSON API

**source_credibility** (§14) applies uniformly to results from all three providers.

**Cost tracking:** see economic.md §1.3 for provider cost breakdown.
Provider costs are operational (external), not billed to user balance.

---

## 24. HEALTHCHECK

→ architecture.md §29 (canonical rules). Not a model, tier, or agent.

---

## 25. MULTI-INTENT AND VERBATIM RETURN (architecture.md §44, §47)

### 25.1 Multi-intent model assignment

When classify() returns list[IntentResult] (§44), each sub-intent receives its own
preferred_model via _resolve_routing(). model_router resolves each independently.
Tool-intents (WEATHER, MAPS, MAPS_ROUTE, MAPS_POI) bypass model selection entirely —
they use verbatim return (§47).

### 25.2 Verbatim return — no model billing

Verbatim return path (§47): tool output returned directly, no LLM call.
Billing: 0 LLM input tokens, 0 LLM output tokens.
Only tool execution cost applies (external provider, not Groq-billed).
EPK estimated_output = 0 when all intents are tool-only.

### 25.3 Per-model billing readiness

preferred_model is now resolved per-request (§45).
usage_meter MUST log resolved_model alongside tier for each request.
This enables per-model actual_cost() billing when economic.md §12 open item is implemented.