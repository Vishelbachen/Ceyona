# CEYONA — MODEL REGISTRY
Version: 9.0 — Post-Deprecation Migration Edition
Status: Active Source of Truth
Supersedes: v8.0 and all previous versions

## DEPRECATION NOTICE (June 17, 2026 — Groq announcement)

Four models deprecated and REMOVED from active assignments:

| Model | Deadline | Replaced by | Role |
|---|---|---|---|
| `qwen/qwen3-32b` | Jul 17, 2026 | `openai/gpt-oss-120b` | GENERAL structured → HEAVY |
| `meta-llama/llama-4-scout-17b-16e-instruct` | Jul 17, 2026 | `qwen/qwen3.6-27b` | VISION + LONG_CONTEXT |
| `llama-3.1-8b-instant` | Aug 16, 2026 | `openai/gpt-oss-20b` | FAST |
| `llama-3.3-70b-versatile` | Aug 16, 2026 | `qwen/qwen3.6-27b` | GENERAL + MULTILINGUAL |

All four models preserved in §28 (DEPRECATED REGISTRY) for historical reference only.
Do NOT assign deprecated models to any new role.

This document defines ONLY:
- approved models and their roles
- tier assignments and eligibility
- activation rules and constraints
- per-model behavioral characteristics (§27) — basis for persona design and prompt sizing
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
openai/gpt-oss-20b  → PRIMARY: fast inference, shallow reasoning, DEGRADED_MODE fallback
allam-2-7b          → MULTILINGUAL: Arabic normalization (one call, three contexts)
```

**Migration note:** `llama-3.1-8b-instant` deprecated Aug 16, 2026 → replaced by `openai/gpt-oss-20b`.

**Activation:** ALLOW or DEGRADED_MODE signals from EPK.
**Skip on:** HEAVY_REQUIRED, DENY.

**gpt-oss-20b characteristics (FAST role):**
- MoE, 21B total / 3.6B active per forward pass
- ~967 TPS on Groq, TTFT 0.83s
- reasoning_effort="low" REQUIRED at all FAST call sites
- Tool use ✅, JSON ✅, structured output ✅
- Multilingual: strong RU/AR, weak CJK (<45% on Chinese) — acceptable for Ceyona audience
- Prompt capacity: ~20 sentences before instruction degradation

**allam-2-7b contexts (NOT three instances):**
1. Fast Tier preprocessing
2. Specialized Layer (TTS pipeline)
3. Multilingual normalization (Arabic routing)
One model, one call per request where needed.

**gpt-oss-20b as SHAPER_MODEL:**
When EPK = HEAVY_REQUIRED, gpt-oss-20b is used ONLY in heavy_input_shaper.py
and web_tools.py (route/POI extraction). It is NOT acting as Fast Tier in those contexts.

---

## 3. GENERAL TIER (ALLOW only)

**Provider: Groq**
*Prices: economic.md §1.1*

```
qwen/qwen3.6-27b      → PRIMARY: universal reasoning, multilingual, vision-capable
openai/gpt-oss-120b   → FALLBACK: if qwen3.6-27b unavailable
```

**Migration note:** `llama-3.3-70b-versatile` and `qwen/qwen3-32b` deprecated → replaced by `qwen/qwen3.6-27b`.

**Activation:** ALLOW signal from EPK only.
**Skip on:** HEAVY_REQUIRED, DEGRADED_MODE, DENY.

**qwen/qwen3.6-27b characteristics (GENERAL role):**
- Dense, 27B parameters (all active per forward pass)
- IFEval score 95.0 — best instruction-following in class
- 201 languages — covers RU, AR, EN and all other Ceyona user languages
- Native context 262K tokens (Groq limit: 131K)
- Vision: image + text input ✅
- Tool use ✅, JSON ✅, structured output ✅
- Persona drift: 11% at turn 7 (best measured in class)
- Prompt capacity: ~30 sentences comfortable

**CRITICAL — thinking mode:**
`reasoning_effort="none"` MUST be passed at every call site.
Default thinking mode produces CoT output in responses — unacceptable for production.
Non-thinking params: `temperature=0.7, top_p=0.80, top_k=20, presence_penalty=1.5`

**CRITICAL — vision hallucination:**
qwen3.6-27b hallucinates image content without warning when image is not accessible.
VQ-03 test (low-quality images) is mandatory before VISION role certification.

**Model specialization within GENERAL tier (architecture.md §45):**
Intent-based preferred_model hint is set in RoutingProfile by _resolve_routing().
model_router uses hint to select within _TIER_MODELS[GENERAL]. Primary is fallback.

| Intent group | Preferred model | Reason |
|---|---|---|
| CONVERSATION, EMOTIONAL, CREATIVE | qwen/qwen3.6-27b | multilingual expressiveness, tone |
| QUESTION, INSTRUCTION, ANALYSIS | qwen/qwen3.6-27b | reasoning, explanation |
| CODE, MATH, EXAM | qwen/qwen3.6-27b | SWE-bench 77.2%, structured output |
| SEARCH, RECOMMENDATION | qwen/qwen3.6-27b | synthesis, multilingual grounding |
| WEATHER, MAPS, MAPS_POI, MAPS_ROUTE | verbatim (no LLM) | structured data — bypasses model |

---

## 4. HEAVY TIER (HEAVY_REQUIRED only)

**Provider: Groq**
*Prices: economic.md §1.1*

```
openai/gpt-oss-120b  → PRIMARY: deep multi-step reasoning
                       SECONDARY: Consensus arbiter (mutex — see §8)
```

**Migration note:** `qwen/qwen3-32b` removed from GENERAL and fully retired. `llama-4-scout` removed from HEAVY secondary — replaced by `qwen/qwen3.6-27b` in LONG_CONTEXT role.

**Activation:** EPK = HEAVY_REQUIRED ONLY.
**Self-activation:** forbidden. Orchestrator executes the signal, does NOT generate it.

**gpt-oss-120b characteristics (HEAVY role):**
- MoE, 120B total / 5.1B active per forward pass
- TTFT 0.71s — best on Groq despite size
- Latency grows from 0.8s → 2.9s over 10 turns (attention scaling) — acceptable for HEAVY
- reasoning_effort="high" for deep reasoning tasks
- 81+ languages — sufficient for Ceyona (weaker than qwen3.6 on multilingual)
- Prompt capacity: 40+ sentences comfortable
- Harmony format: System → Developer → User → Assistant hierarchy

**Output rule:** Heavy Tier output → directly to Response Synthesizer. Consensus SKIP (mutex).

**Hard invariants:**
- each subsystem = isolated capability domain
- NO shared state
- NO hierarchical dominance
- NO cross-decision influence

---

## 5. HEAVY INPUT SHAPER (self-gated utility — NOT a tier)

**Provider: Groq (uses openai/gpt-oss-20b)**
`llm/heavy_input_shaper.py`

**Role:** prepare input for Heavy Tier execution.

**Migration note:** `llama-3.1-8b-instant` → `openai/gpt-oss-20b`. Use `reasoning_effort="low"`.

**Activation:**
- ONLY when EPK = HEAVY_REQUIRED
- ALWAYS CALLED on HEAVY_REQUIRED (self-gated internally)
- Internal gating: shaping needed → execute | not needed → NO-OP (return input as-is)
- SKIP on ALLOW, DEGRADED_MODE, DENY

**Model used:** openai/gpt-oss-20b — NOT as Fast Tier

**Constraints:** NO reasoning, NO final output generation.

---

## 6. AGENT LAYER (context-synthesis fabric)

**Provider: Groq**
*Prices: economic.md §1.3*

```
groq/compound      → SYNTHESIZER on Tier.GENERAL path  (agents/compound_agent.run_deep())
groq/compound-mini → SYNTHESIZER on Tier.FAST path     (agents/compound_agent.run_fast())
```

**Role:** receive fully assembled context (retrieval already done by orchestrator) and synthesize response. NOT autonomous agents — they do NOT call tools, do NOT self-search, do NOT own policy.

**Why synthesizer, not agent (architecture.md §40):**
Groq compound models do not accept custom tool schemas (`tools=` → HTTP 400, verified May 2026).
All retrieval (Tavily/SerpAPI/SearXNG/weather/maps) is performed by orchestrator BEFORE compound is called.
Context injected via `PromptContext → build_messages()`. Compound synthesizes — does not search.

**Invocation path:**
```
orchestrator → retrieval complete → PromptContext assembled
    → multi_agent_coordinator → compound_agent.run_{fast|deep}()
    → groq_client (no tools= parameter)
    → AgentResult → coordinator → orchestrator
```

**Dispatch by tier:**
```
Tier.FAST    → groq/compound-mini  (AgentType.COMPOUND_FAST)
Tier.GENERAL → groq/compound       (AgentType.COMPOUND_DEEP)
Fallback     → qwen/qwen3.6-27b (AgentType.DEEP — plain synthesis, no compound)
```

**`max_tokens`:** always from `route_max_tokens(tier)` via model_router — never hardcoded.

**Constraints:**
- No tool schemas, no tool loop, no tool execution
- No policy authority, no model selection, no routing decisions
- No self-escalation, no self-search
- On failure: `AgentResult(success=False)` — coordinator handles fallback

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
```

**Speech activation:** `is_voice_input = True` ONLY.
→ Full ASR/TTS lifecycle: architecture.md §32, §33.

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

## 22. AVAILABLE GROQ MODELS (June 2026)

Complete list of models available on Groq API as of June 2026 (count: 17).
⚠️ Four models below marked DEPRECATED — do not assign to new roles.

```json
[
  "allam-2-7b",
  "canopylabs/orpheus-arabic-saudi",
  "canopylabs/orpheus-v1-english",
  "groq/compound",
  "groq/compound-mini",
  "llama-3.1-8b-instant",          // ⚠️ DEPRECATED — Aug 16, 2026
  "llama-3.3-70b-versatile",        // ⚠️ DEPRECATED — Aug 16, 2026
  "meta-llama/llama-4-scout-17b-16e-instruct", // ⚠️ DEPRECATED — Jul 17, 2026
  "meta-llama/llama-prompt-guard-2-22m",
  "meta-llama/llama-prompt-guard-2-86m",
  "openai/gpt-oss-120b",
  "openai/gpt-oss-20b",
  "openai/gpt-oss-safeguard-20b",
  "qwen/qwen3-32b",                 // ⚠️ DEPRECATED — Jul 17, 2026
  "qwen/qwen3.6-27b",
  "whisper-large-v3",
  "whisper-large-v3-turbo"
]
```

**Active assignment coverage (June 2026):**
| Model | Role | Section |
|---|---|---|
| openai/gpt-oss-20b | FAST tier primary | §2 |
| qwen/qwen3.6-27b | GENERAL + VISION + LONG_CONTEXT + MULTILINGUAL | §3, §26 |
| openai/gpt-oss-120b | HEAVY tier primary + Consensus | §4, §8 |
| groq/compound | Agent Layer DEEP | §6 |
| groq/compound-mini | Agent Layer FAST | §6 |
| meta-llama/llama-prompt-guard-2-22m | Safety Gate Pass 1 | §1 |
| meta-llama/llama-prompt-guard-2-86m | Safety Gate Pass 2 | §1 |
| openai/gpt-oss-safeguard-20b | Safety Gate observability | §1 |
| whisper-large-v3 | ASR primary | §12 |
| whisper-large-v3-turbo | ASR fallback | §12 |
| canopylabs/orpheus-v1-english | TTS English | §12 |
| canopylabs/orpheus-arabic-saudi | TTS Arabic | §12 |
| allam-2-7b | Arabic NLP anchor | §12 |

---

## 23. MULTILINGUAL NORMALIZATION

`llm/multilingual_preprocessor.py`

```
allam-2-7b        → Arabic normalization (anchor — no replacement available)
qwen/qwen3.6-27b  → all other non-Latin languages (201 languages)
```

**Migration note:** `llama-3.3-70b-versatile` → `qwen/qwen3.6-27b` for non-Arabic multilingual.
Use `reasoning_effort="none"` for normalization calls (not a reasoning task).

**Decision tree (unchanged from architecture.md §34):**
- Latin-dominant (>90%) → passthrough, no LLM call
- Arabic script (>15%) → allam-2-7b
- Other non-Latin → qwen/qwen3.6-27b

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

## 26. QWEN3.6-27B — DUAL ROLE REGISTRY (VISION + LONG_CONTEXT)

`qwen/qwen3.6-27b` holds **two explicitly bounded roles** in addition to GENERAL and MULTILINGUAL.
These are separate invocation paths with separate prompts and separate constraints.
Replaces `meta-llama/llama-4-scout-17b-16e-instruct` (deprecated Jul 17, 2026).

### 26.1 Role A — Vision Extraction (OUTSIDE EPK DAG)

**Module:** `external/vision_handler.py`
**Activation:** image input detected by `update_handler` (forced_intent path)
**Position:** parallel ingress — runs independently of the main pipeline

```
Telegram photo → update_handler → vision_handler → qwen/qwen3.6-27b (direct groq_client call)
    → structured extraction result → update_handler forced_intent → normal pipeline
```

**`max_tokens`:** from `policy_registry.RUNTIME.tier_configs[Tier.FAST].max_output_tokens`
(extraction is bounded, low-complexity — FAST tier limit applies, architecture.md §15)

**Prompt scope:** image extraction only — structured signals, no reasoning, no synthesis.

**Constraints:**
- `reasoning_effort="none"` MANDATORY — thinking mode must be off at every vision call site
- MUST NOT be given reasoning or synthesis instructions
- MUST NOT influence EPK, routing, or TruthMode
- Never raises — returns structured result or empty on failure
- VQ-03 (low quality images) MUST be tested before certification — model hallucinates
  image content without warning when image quality is insufficient (documented failure mode)

### 26.2 Role B — Long-Context Transformation (EPK-gated, explicit activation)

**Module:** invoked by orchestrator when `complexity == CRITICAL` AND `context_length > 32K tokens`
**Activation:** explicit orchestrator decision — NOT EPK HEAVY_REQUIRED signal
**Position:** pre-synthesis transformation step on long-context requests
**Native context:** 262K tokens — replaces llama-4-scout (was 512K; 262K sufficient for LC-01/LC-02)

**Prompt scope:** long-context compression and transformation only — not general reasoning.

**Constraints:**
- `reasoning_effort="none"` MANDATORY at every long-context call site
- MUST NOT be substituted for gpt-oss-120b on reasoning tasks
- MUST NOT self-activate
- Role B invocation MUST be logged separately from Role A invocations

### 26.3 Instruction-following capacity note

`qwen/qwen3.6-27b` holds **four roles** (GENERAL, VISION, LONG_CONTEXT, MULTILINGUAL) with
**separate prompts per role**. Each role uses a distinct, scoped prompt — not a shared prompt bank.
IFEval score 95.0 confirms reliable instruction-following within comfortable capacity (~30 sentences).
Rule: if any role's prompt approaches 30 sentences, roles must be reviewed for prompt bloat.
One model, four separate scoped prompts — acceptable. Shared prompt bank across roles — not acceptable.

---

## 27. PER-MODEL CHARACTERISTICS

This section is the canonical source for:
- known behavioral tendencies of each model
- instruction-following limits (comfortable, not maximum)
- persona patch triggers (architecture.md §46)
- prompt design constraints per model

**Rule:** a PERSONA_PATCH (architecture.md §46) is added ONLY when a deviation is documented here
with a reproducible pattern. No entry here = no patch.

**Rule:** prompt length for any model MUST stay within its documented comfortable range.
A prompt that fits technically (no truncation) but exceeds comfortable capacity will produce
degraded instruction following — the model silently deprioritizes later rules.

**Source legend:**
- ✅ DOC — официальная документация Groq / OpenAI / Qwen / Meta
- ✅ BENCH — независимые публичные бенчмарки
- ✅ PROD — production опыт Ceyona
- ⚠️ EST — оценка, требует подтверждения в production

---

### 27.1 openai/gpt-oss-20b (FAST tier primary)

**Nature:** MoE 21B total / 3.6B active. Highest output speed on Groq (~967 t/s). Optimized
for low-latency agentic workflows. English/STEM focus.

**Comfortable prompt capacity:** ~20 sentences (~212 tokens for FAST persona — well within range). ⚠️ EST
Beyond that: constraint adherence degrades, conciseness rules may be deprioritized.

**Known behavioral tendencies:**
- Conservative, neutral tone by default — does not spontaneously add warmth ✅ DOC
- Holds negative rules ("do not do X") more reliably than positive framing ✅ DOC
- Below 45% accuracy on CJK (Chinese/Japanese/Korean) — STEM/English training bias ✅ BENCH
- RU/AR: sufficient for FAST role (short responses, tool calls) — not used for MULTILINGUAL ✅ EST
- `reasoning_effort="low"` MUST be set at every FAST call site — reduces latency and cost ✅ DOC
- Tool use and JSON structured output: reliable ✅ DOC

**Persona implications:**
- FAST persona: 1–2 sentences maximum. Brevity is the persona.
- Do not expect warmth — precision and directness are its native register.
- Gender agreement (RU): place as first rule in system prompt.

**What it does well:** fast factual replies, short conversational responses, tool calling,
JSON generation, heavy_input_shaper utility (SHAPER_MODEL role).

**API note:** use `reasoning_effort="low"` for all FAST calls. Supports low/medium/high.

---

### 27.2 qwen/qwen3.6-27b (GENERAL + VISION + LONG_CONTEXT + MULTILINGUAL)

**Nature:** Dense 27B parameters (all active per pass). Hybrid Gated DeltaNet + Gated Attention
architecture. Natively multimodal (text + image). 262K token context window. 201 languages.

**Comfortable prompt capacity:** ~30 sentences for GENERAL (~800 token system prompt). ✅ BENCH
IFEval score 95.0 — best instruction-following in its class. ✅ BENCH
Persona drift: 11% at turn 7 (vs 34% for competing models). ✅ BENCH

**Known behavioral tendencies:**
- Strong instruction-following on long prompts — rules maintained through turn 7 ✅ BENCH
- Thinking mode: MUST be disabled at EVERY call site — `reasoning_effort="none"` ✅ DOC
  (if not disabled: model enters chain-of-thought mode → latency spike + token waste)
- Non-thinking recommended params: `temperature=0.7, top_p=0.80, top_k=20, presence_penalty=1.5` ✅ DOC
- Vision hallucination: confidently describes image content when image is not accessible,
  NO warning or error emitted — documented failure mode ✅ BENCH
- Bullet/enumeration bias on structured tasks — needs explicit suppression for conversational output ⚠️ EST
- 201 languages: RU/AR/EN natively strong; replaces llama-3.3-70b-versatile for non-Arabic multilingual ✅ DOC

**Persona implications:**
- GENERAL persona: up to 6–8 sentences viable given IFEval 95.0 capacity.
- Must explicitly prohibit unsolicited advice on emotional queries (same risk as llama-3.3-70b).
- Anti-enumeration rule required for conversational intents.
- Persona rules front-loaded in system prompt.

**VISION role constraints:**
- No persona. Extraction prompt only — structured JSON output, no conversational register.
- VQ-03 test (low-quality images) MANDATORY before certification — hallucination without warning.

**LONG_CONTEXT role constraints:**
- 262K native context — replaces llama-4-scout (deprecated Jul 17, 2026).
- Minimal task framing prompt. No persona injection.
- LC-02 test (100K document) required for certification.

**MULTILINGUAL role:**
- Replaces llama-3.3-70b-versatile for all non-Arabic non-Latin normalization.
- Same model invoked with a minimal normalization prompt — not the full GENERAL persona.

**What it does well:** reasoning, multilingual synthesis, conversational depth, vision extraction,
long-context transformation, code generation (SWE-bench 77.2%), structured output.

---

### 27.3 openai/gpt-oss-120b (HEAVY tier primary + Consensus arbiter)

**Nature:** MoE 120B total / 5.1B active. Highest reasoning capability in registry.
Near-parity with o4-mini on reasoning benchmarks. TTFT 0.71s — lowest on Groq despite size.

**Comfortable prompt capacity:** ~40+ sentences. Handles large context reliably. ✅ DOC
Latency grows from 0.8s to 2.9s over 10 conversational turns (attention scaling). ✅ BENCH
For HEAVY role this is acceptable — deep reasoning tasks expect latency.

**Known behavioral tendencies:**
- Default register: academic/formal — produces corporate-neutral output without persona ✅ DOC
- On very long outputs (600+ tokens): persona may fade in later paragraphs ⚠️ EST
- Multilingual: 81+ languages — weaker than qwen3.6-27b on multilingual tasks ✅ BENCH
- Creative writing polish: below frontier proprietary models ✅ BENCH
- `reasoning_effort` (low/medium/high): use "high" for HEAVY, "medium" for Consensus ✅ DOC
- Harmony role hierarchy: System → Developer → User → Assistant — use at every call site ✅ DOC
- MoE architecture: cheaper on output tokens than apparent size suggests ✅ DOC

**Persona implications:**
- HEAVY persona: same base as GENERAL but test on long outputs specifically.
- If tone drift on long outputs: add persona reinforcement mid-prompt.
- Consensus arbiter: minimal arbitration prompt only — no full persona.

**What it does well:** deep multi-step reasoning, complex analysis, long-context synthesis,
consensus arbitration between agent outputs, math (AIME 98.7%), code (SWE-bench ~76%).

---

### 27.4 groq/compound + groq/compound-mini (Agent Layer — synthesizers)

**Nature:** Groq compound AI systems — models + built-in tools (web search, code execution).
Used in Ceyona as pure synthesizers (no tool schemas passed — HTTP 400 on custom tools). ✅ PROD

**Comfortable prompt capacity:** 128K input context. ✅ DOC
compound: up to 10 built-in tool calls per request. ✅ DOC
compound-mini: 1 built-in tool call, 3x lower latency than compound. ✅ DOC

**Known behavioral tendencies:**
- Strong bias toward bullet lists and structured enumeration — needs explicit FORMAT_RULES suppression ✅ PROD
- Less natural warmth in conversational register ✅ PROD
- Internally uses gpt-oss-120b, llama-4-scout, llama-3.3-70b — behavior reflects these models ✅ DOC
  (this is compound's internal composition — these models are not called directly by Ceyona)
- Custom tool schemas (`tools=` parameter) → HTTP 400 — confirmed May 2026 ✅ PROD
- `output_normalizer.py` and `correction.py` clean output post-synthesis ✅ PROD
- Max output: 8K tokens (synthesis limit) ✅ DOC

**Persona implications:**
- FORMAT_RULES do the heavy lifting: suppress bullets, suppress headers.
- Do not attempt conversational warmth — outcompeted by structural defaults.
- Persona patch: add anti-enumeration rule if production logs show persistent bullet leakage.

**What it does well:** synthesizing retrieved context, structured summarization,
search/weather/maps result assembly (compound-mini for single-source, compound for multi-source).

---

### 27.5 Safety Layer models (non-generating — no persona)

#### llama-prompt-guard-2-22m (Safety Pass 1)

**Nature:** DeBERTa-xsmall base (22M params). No multilingual pretraining. ✅ DOC
Context window: 512 tokens. ✅ DOC
Speed: lowest latency in safety stack — designed for fast pre-filter.

**Known limitations:**
- No multilingual pretraining → significant false positive rate on RU/AR/short casual messages ✅ DOC
- This is the architectural reason for NON-BLOCKING policy (§1 rationale)
- English-only attack detection: reliable ✅ DOC
- Non-English attacks: use llama-prompt-guard-2-86m for multilingual coverage ✅ DOC

#### llama-prompt-guard-2-86m (Safety Pass 2)

**Nature:** mDeBERTa-base (86M params). Multilingual pretraining — detects EN and non-EN attacks. ✅ DOC
Context window: 512 tokens. ✅ DOC

**Known limitations:**
- Better than 22m on non-Latin scripts, but still produces false positives on casual messages ⚠️ EST
- NON-BLOCKING remains correct for both passes ✅ PROD
- Detects: prompt injection, jailbreak attempts — NOT harmful instructions that aren't jailbreaks ✅ DOC

#### openai/gpt-oss-safeguard-20b (Safety Pass 2 — observability)

**Nature:** GPT-OSS fine-tuned for safety classification. Bring-your-own-policy reasoning model. ✅ DOC
Replaced llama-guard-4-12b in February 2026. ✅ DOC
Supports reasoning_effort: low (simple classification), high (nuanced decisions). ✅ DOC

**Policy prompt structure (optimal):**
```
# Policy Name
## INSTRUCTIONS  — what to do and how to respond
## DEFINITIONS   — key terms and context
## CRITERIA      — what violates / what is safe
## EXAMPLES      — 4–6 labeled examples
Content: {{USER_INPUT}}
Answer (JSON only):
```
Optimal policy length: 400–600 tokens. ✅ DOC

**Role in Ceyona:** non-blocking observability. Reads Ceyona's safety policy and logs reasoning.
NON-BLOCKING rule applies identically to safeguard-20b and prompt-guard models.

---

### 27.6 allam-2-7b (Arabic NLP anchor)

**Nature:** Bilingual Arabic-English. Trained from scratch: 4T English tokens → 1.2T mixed AR/EN. ✅ DOC
This two-step approach prevents catastrophic forgetting — retains English while building Arabic. ✅ DOC

**Comfortable prompt capacity:** narrow — normalization task is simple and bounded. ✅ PROD

**Known behavioral tendencies:**
- Arabic normalization: reliable within scope ✅ PROD
- Saudi-Alignment Benchmark: 81.8% — second only to GPT-4 (83.3%), above Llama-3.3-70B (81.6%) ✅ BENCH
- Domain knowledge (Arabic): strongest ALLaM-7B score category ✅ BENCH
- Outside Arabic script: not used — qwen3.6-27b handles other non-Latin scripts ✅ PROD
- On empty or malformed input: returns empty string → multilingual_preprocessor reverts to original ✅ PROD
- Works without predefined system prompt — optimized for custom prompts ✅ DOC

**Persona implications:** No persona. Normalization task only — output is processed text, not user-visible.

**What it does well:** Arabic text normalization, Arabic-English bilingual tasks, cultural alignment.

---

### 27.7 Speech models (Whisper ASR + Orpheus TTS — no persona)

#### whisper-large-v3 (ASR primary)

**Nature:** 1.55B parameters. 99 languages. Full 32-layer encoder + decoder. ✅ DOC

**Accuracy:** WER 2.7% on clean audio, 8–12% in real-world conditions. ✅ BENCH

**Known failure modes (3 documented):**
1. **Hallucination on silence:** during long pauses, invents plausible-sounding text. ✅ BENCH
   Mitigation: VAD (Voice Activity Detection) preprocessing to skip silence.
2. **Noisy audio:** WER degrades +5–15% in noisy environments. ✅ BENCH
3. **Technical vocabulary:** no custom vocab support — domain-specific terms degrade accuracy. ✅ BENCH

**Role in Ceyona:** primary ASR. `is_voice_input=True` only. Never raises — returns
`TranscriptResult(success=False)` on all errors.

#### whisper-large-v3-turbo (ASR fallback)

**Nature:** 809M parameters. Decoder pruned from 32 → 4 layers. Encoder identical to v3. ✅ DOC
Speed: ~6x faster than large-v3. WER within 1–2% of v3 on standard audio. ✅ BENCH

**Known limitations vs v3:**
- Higher hallucination rate on very short or noisy recordings — shallow decoder ✅ BENCH
- Does NOT support translation task (excluded from turbo training) ✅ DOC

**Role in Ceyona:** fast fallback. NOT primary — v3 is primary for accuracy.

#### canopylabs/orpheus-v1-english (TTS English)

**Nature:** LLM-based TTS (Llama architecture). ~200ms streaming latency. ✅ DOC
Updated April 2026 — reduced hallucinations, better handling of numbers and symbols. ✅ DOC

**Voices:** diana (default), autumn, hannah, austin, daniel, troy. ✅ DOC
**Vocal directions:** `[cheerful]`, `[whisper]` and others — English model only. ✅ DOC
**Max input:** 5000 characters per call. ✅ PROD

**TTS hallucination modes:** word repetition, word skipping — surface artifacts, not semantic.
Mitigation: `correction.py` and `output_normalizer.py` clean text before TTS receives it.

#### canopylabs/orpheus-arabic-saudi (TTS Arabic)

**Nature:** Same Orpheus architecture, Saudi Arabic specialized. ✅ DOC
Updated April 2026 — new voices Abdullah (male professional) and Aisha (female professional). ✅ DOC

**Voices:** noura, fahad, sultan, lulwa, aisha, abdullah. ✅ DOC
**Vocal directions:** NOT supported — Arabic model does not accept `[cheerful]` etc. ✅ DOC
**Max input:** 5000 characters per call. ✅ PROD

Voice ID selection owned by `prompt_policy.py` — treated as persona constant.

---

### 27.8 HF Embedding models (no persona — not Groq)

#### BAAI/bge-large-en-v1.5 (PRIMARY EMBEDDING)

**Provider:** HuggingFace Serverless. Separate billing from Groq (HF_TOKEN). ✅ DOC
**Role:** generate dense retrieval vectors. Higher quality, higher latency than bge-small.
**Constraints:** ONLY generates vectors. No ranking, no synthesis, no routing authority. ✅ DOC

#### BAAI/bge-small-en-v1.5 (FAST EMBEDDING FALLBACK)

**Provider:** HuggingFace Serverless.
**Role:** fast embedding when bge-large quota exhausted or latency critical.
Quality: slight degradation on short queries vs bge-large. For most production queries — adequate.

#### BAAI/bge-reranker-large (CROSS-ENCODER RERANKING)

**Provider:** HuggingFace Serverless.
**Role:** reorder retrieval candidates. Cross-encoder architecture — scores pairs, not individual vectors.
**Constraints:** NEVER generates embeddings. NEVER influences EPK, routing, or tier selection. ✅ DOC
HF quota exhaustion: degrades retrieval quality, does NOT cause LLM failure. ✅ DOC

---

## 28. DEPRECATED MODEL REGISTRY

Models removed from active assignments June 2026. Preserved for historical reference only.
Do NOT assign to any role. Data retained as baseline for regression delta testing.

| Model | Deprecated | Was role | Replaced by |
|---|---|---|---|
| llama-3.1-8b-instant | Aug 16, 2026 | FAST primary | openai/gpt-oss-20b |
| llama-3.3-70b-versatile | Aug 16, 2026 | GENERAL primary | qwen/qwen3.6-27b |
| llama-4-scout-17b-16e-instruct | Jul 17, 2026 | VISION + LONG_CONTEXT | qwen/qwen3.6-27b |
| qwen/qwen3-32b | Jul 17, 2026 | GENERAL CODE/MATH | openai/gpt-oss-120b |

**Baseline data retained in models_passport.md** for Regression Delta testing (§3.0).


*Deprecated content removed — see §28 for historical record.*