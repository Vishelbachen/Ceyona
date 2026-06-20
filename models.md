# CEYONA — MODEL REGISTRY
Version: 8.0 — Per-Model Edition
Status: Active Source of Truth
Supersedes: models1.md, models2.md, v7.x (all previous versions)

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
openai/gpt-oss-120b  → PRIMARY: deep multi-step reasoning
                       SECONDARY: Consensus arbiter (mutex — see §8)
```

**Activation:** EPK = HEAVY_REQUIRED ONLY.
**Self-activation:** forbidden. Orchestrator executes the signal, does NOT generate it.

**Output rule:** Heavy Tier output → directly to Response Synthesizer. Consensus SKIP (mutex).

**Note on llama-4-scout-17b:** this model is NOT part of the HEAVY tier EPK path.
It serves two separate, explicitly bounded roles — see §12 (Vision) and §26 (Long-Context).
It is invoked directly, outside the EPK→decision_matrix→HEAVY flow.

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
Fallback     → llama-3.3-70b-versatile (AgentType.DEEP — plain synthesis, no compound)
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
| meta-llama/llama-4-scout-17b-16e-instruct | Vision extraction + Long-context (§26) | §26 |
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

## 26. LLAMA-4-SCOUT — DUAL ROLE REGISTRY

`meta-llama/llama-4-scout-17b-16e-instruct` holds **two explicitly bounded roles**.
These are separate invocation paths with separate prompts and separate constraints.
The model is NOT part of the HEAVY tier EPK path (see §4).

### 26.1 Role A — Vision Extraction (OUTSIDE EPK DAG)

**Module:** `external/vision_handler.py`
**Activation:** image input detected by `update_handler` (forced_intent path)
**Position:** parallel ingress — runs independently of the main pipeline

```
Telegram photo → update_handler → vision_handler → llama-4-scout (direct groq_client call)
    → structured extraction result → update_handler forced_intent → normal pipeline
```

**`max_tokens`:** from `policy_registry.RUNTIME.tier_configs[Tier.FAST].max_output_tokens`
(extraction is bounded, low-complexity — FAST tier limit applies, architecture.md §15)

**Prompt scope:** image extraction only — structured signals, no reasoning, no synthesis.

**Constraints:**
- MUST NOT be given reasoning or synthesis instructions
- MUST NOT influence EPK, routing, or TruthMode
- Never raises — returns structured result or empty on failure

### 26.2 Role B — Long-Context Transformation (EPK-gated, explicit activation)

**Module:** invoked by orchestrator when `complexity == CRITICAL` AND `context_length > 32K tokens`
**Activation:** explicit orchestrator decision — NOT EPK HEAVY_REQUIRED signal
**Position:** pre-synthesis transformation step on long-context requests

**Prompt scope:** long-context compression and transformation only — not general reasoning.

**Constraints:**
- MUST NOT be substituted for gpt-oss-120b on reasoning tasks
- MUST NOT self-activate
- Role B invocation MUST be logged separately from Role A invocations

### 26.3 Instruction-following capacity note

llama-4-scout-17b holds **two prompts with different scopes**.
Before assigning additional responsibilities: measure comfortable instruction-following
capacity (not maximum — comfortable, where behavior is stable).
Rule: if either role's prompt approaches that limit, the roles must be split to separate models.
One model, two prompts — acceptable. One model, two prompts + shared prompt bank — not acceptable.

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

---

### 27.1 llama-3.1-8b-instant (FAST tier primary)

**Nature:** fast, shallow, low-latency. Built for structural signal compression, not expression.

**Comfortable prompt capacity:** ~8–10 sentences in system prompt before instruction following degrades.
Beyond that: later rules are silently dropped, earlier rules dominate.

**Known behavioral tendencies:**
- Flat, terse default tone — minimal spontaneous warmth
- Holds simple, single-property tone instructions reliably
- Multi-property tone (warm + concise + direct simultaneously) degrades quickly
- On complex explanations: simplifies beyond the acceptable floor
- Gender agreement (Russian/Arabic) can drift mid-response on outputs > 3 sentences

**Persona implications:**
- Persona prompt: maximum 1–2 sentences. Warmth through brevity and directness, not elaboration.
- Do not instruct it to vary sentence openings — it will attempt to comply and produce awkward results.
- Gender agreement MUST be the first rule in system prompt (highest priority position).

**What it does well:** quick factual replies, short conversational responses, input shaping (heavy_input_shaper role), route/POI extraction (web_tools.py).

---

### 27.2 llama-3.3-70b-versatile (GENERAL tier primary)

**Nature:** expressive, reasoning-capable, spontaneously varies structure. The most "human-feeling" model in the registry.

**Comfortable prompt capacity:** ~20–25 sentences. Beyond that: instruction following on later rules degrades noticeably. Primary risk is persona rules being overridden by the model's own stylistic habits.

**Known behavioral tendencies:**
- On long explanatory responses: appends unsolicited summarizing paragraph (P3 violation)
- On emotionally-toned requests: adds unprompted advice or empathy scripts (P2, P6 violation)
- Under long system prompt pressure (>25 sentences): deprioritizes later-positioned rules
- In non-English responses: can echo English phrasing patterns mid-sentence (output_normalizer mitigates)
- Spontaneously varies sentence structure — positive for tone, negative if it produces run-on warmth markers

**Persona implications:**
- Persona prompt: up to 5–6 sentences viable. Can hold multi-property tone.
- Must explicitly prohibit summarizing paragraph at response end.
- Must explicitly prohibit unsolicited advice on emotional queries.
- Persona rules should be front-loaded (first in system prompt), not buried after long rule lists.

**What it does well:** reasoning, explanation, creative tasks, multilingual synthesis, conversational depth, recommendation synthesis.

---

### 27.3 qwen/qwen3-32b (GENERAL tier — CODE/MATH/EXAM)

**Nature:** structurally precise, strong instruction following, less expressive in conversational register.

**Comfortable prompt capacity:** ~25–30 sentences. Strong instruction following across the range — one of the most reliable models for rule adherence.

**Known behavioral tendencies:**
- Default register: formal/neutral. Does not spontaneously add warmth.
- Tends toward structured, enumerated output — needs explicit suppression of lists/headers for conversational tasks.
- Thinking mode (`thinking: True`) MUST be disabled at every call site — `"thinking": False` is mandatory, otherwise HTTP 400.
- Less natural on open-ended conversational prompts; best on tasks with clear structure.

**Persona implications:**
- Persona here competes with model's structural bias. Keep persona minimal for CODE/MATH/EXAM tasks.
- For any conversational fallback on this model: add explicit anti-enumeration rule.
- Warmth is not natural to this model — do not force it. Precision and directness are its native register; that is the persona for this role.

**What it does well:** code generation, mathematical reasoning, structured output, exam-style Q&A, instruction-following on complex rule sets.

---

### 27.4 openai/gpt-oss-20b (GENERAL tier — constraint-aware inference)

**Nature:** balanced between expressiveness and structure. Reliable on constraint-following. Less well-characterized than 70b versatile — fewer production observations as of June 2026.

**Comfortable prompt capacity:** ~20 sentences (estimate — validate in production).

**Known behavioral tendencies:**
- More conservative in tone than llama-3.3-70b — less prone to warmth inflation
- Constraint-aware: holds negative rules ("do not do X") more reliably than models that need positive framing
- Less expressive on creative/conversational tasks

**Persona implications:**
- Suited for tasks requiring strict constraint adherence with moderate expression.
- Persona prompt: same structure as llama-3.3-70b-versatile but shorter — 3–4 sentences.

**What it does well:** constraint-aware general inference, tasks requiring reliable rule adherence without the expressiveness overhead of 70b.

---

### 27.5 openai/gpt-oss-120b (HEAVY tier primary + Consensus arbiter)

**Nature:** most capable reasoning model in registry. Formal/neutral by default. Used for deep multi-step reasoning and as consensus arbiter.

**Comfortable prompt capacity:** ~40+ sentences. Handles large context well, but tone can shift mid-response on very long outputs as persona is deprioritized relative to reasoning.

**Known behavioral tendencies:**
- Default register: academic/formal — without persona instruction, produces corporate-neutral output
- On very long outputs (600+ tokens): persona may fade in later paragraphs
- As consensus arbiter: operates with arbitration-scoped prompt, NOT the full persona prompt
- MoE architecture: cheaper on output than GENERAL primary despite higher capability

**Persona implications:**
- Same persona text as llama-3.3-70b-versatile base, but test specifically on long outputs.
- If tone shift occurs mid-response on long outputs: add persona reinforcement mid-prompt (after reasoning rules, before output rules).
- Consensus arbiter role uses minimal prompt — arbitration context only, no full persona.

**What it does well:** deep multi-step reasoning, complex analysis, long-context synthesis, arbitration between agent outputs.

---

### 27.6 groq/compound + groq/compound-mini (Agent Layer — synthesizers)

**Nature:** optimized for tool-use synthesis. Structured, list-leaning output. Less natural in conversational tone. Used exclusively as synthesizers receiving pre-assembled context (§6).

**Comfortable prompt capacity:** moderate. Persona competes with tool-result formatting habits.

**Known behavioral tendencies:**
- Strong bias toward bullet lists and structured enumeration — needs explicit suppression
- Less natural warmth in conversational register than llama-3.3-70b
- `output_normalizer.py` and `correction.py` clean its output post-synthesis
- compound-mini (FAST path): shorter outputs, adequate for single-result synthesis
- compound (GENERAL path): longer, structured synthesis across multiple retrieved sources

**Persona implications:**
- Persona here is minimal — FORMAT_RULES do the heavy lifting (suppress lists, suppress headers).
- Persona patch: add explicit anti-enumeration rule if production logs show persistent bullet leakage.
- Do not attempt conversational warmth on synthesis tasks — it will be outcompeted by structural defaults.

**What it does well:** synthesizing multiple retrieved results into coherent response, structured summarization, search/weather/maps result assembly.

---

### 27.7 meta-llama/llama-4-scout-17b-16e-instruct (Vision + Long-Context — see §26)

**Nature:** multimodal-capable, long-context window (512K). Two bounded roles — NOT a general-purpose reasoning model in this system.

**Comfortable prompt capacity per role:**
- Vision extraction prompt (Role A): simple, bounded — well within capacity
- Long-context transformation prompt (Role B): moderate — validate against context size in production

**Known behavioral tendencies:**
- Vision role: reliable structured extraction on clear images; degrades on ambiguous/low-quality input
- Long-context role: performance at extreme context lengths (>200K tokens) needs production validation
- If given open-ended reasoning instructions: tends toward verbose output — keep prompts task-scoped

**Persona implications:**
- Role A (vision): no persona. Extraction prompt only — structured output, no conversational register.
- Role B (long-context): minimal task framing. No persona injection.
- If a third role is considered: measure remaining comfortable capacity first (§26.3 rule).

---

### 27.8 Safety Layer models (non-generating — no persona)

`llama-prompt-guard-2-22m`, `llama-prompt-guard-2-86m`, `openai/gpt-oss-safeguard-20b`

**Role:** classification/scoring only. No generation, no synthesis, no persona.
These models do not produce user-visible output. Persona design does not apply.
Known false-positive rates on Russian/Arabic/short casual messages are the reason
the Safety Layer is non-blocking (§1 rationale).

---

### 27.9 allam-2-7b (Arabic NLP anchor)

**Nature:** Arabic-specialized. Used for normalization, not generation. One call, three contexts.

**Comfortable prompt capacity:** narrow — normalization task is simple and bounded.

**Known behavioral tendencies:**
- Arabic normalization: reliable within scope
- Outside Arabic script: not used — llama-3.3-70b handles other non-Latin scripts
- On empty or malformed input: returns empty string → multilingual_preprocessor reverts to original

**Persona implications:**
- No persona. Normalization task only — output is processed text, not user-visible response.

---

### 27.10 Speech models (Whisper ASR + Orpheus TTS — no persona)

**whisper-large-v3 / whisper-large-v3-turbo:** transcription only. No persona applies.
**canopylabs/orpheus-v1-english:** TTS synthesis. Voice persona is implicit in voice ID selection
(diana/autumn/hannah/austin/daniel/troy) — voice choice is a persona decision, not a prompt decision.
**canopylabs/orpheus-arabic-saudi:** TTS Arabic. Same — voice ID (noura/fahad/sultan/lulwa/aisha)
is the persona carrier, not the prompt.

**Vocal directions** (`[cheerful]`, `[whisper]`): English model only. NOT supported by Arabic model.
Voice ID selection is owned by prompt_policy.py — treated as a persona constant, not a runtime decision.

---