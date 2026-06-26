# CEYONA — ECONOMIC MODEL
Version: 5.7 — Full Documentation Sync (Jun 26, 2026)
Status: Active Source of Truth
Supersedes: economic.md (all previous versions)

This document defines ONLY:
- model pricing (verified from Groq, May 2026)
- cost estimation and actual billing logic
- EPK thresholds and tier selection
- retrieval / embedding / reranking costs
- margin and user billing mechanics
- initial balance and free trial policy

This document MUST NOT define: orchestration, routing policy, model roles, DAG.
Model roles and tier assignments → models.md
Architecture and DAG → architecture.md

---

## 1. MODEL PRICING — SINGLE SOURCE OF TRUTH

All rates in USD per 1M tokens. Verified from groq.com/pricing, May 2026.

### 1.1 LLM Tiers

⚠️ **DEPRECATION NOTICE (актуальность подтверждена 5 раз, последнее — June 20, 2026):**
4 модели выводятся из Groq. Они присутствуют в API сейчас, но будут удалены:
- `qwen/qwen3-32b` → deprecated Jul 17, 2026 (27 дней)
- `meta-llama/llama-4-scout-17b-16e-instruct` → deprecated Jul 17, 2026 (27 дней)
- `llama-3.1-8b-instant` → deprecated Aug 16, 2026
- `llama-3.3-70b-versatile` → deprecated Aug 16, 2026

Замена для VISION и LONG_CONTEXT ролей: `qwen/qwen3.6-27b` (добавлен в Groq Apr 2026).
Приоритет тестирования: models_passport.md Часть 4.

```
FAST tier
  openai/gpt-oss-20b            → input: $0.075  output: $0.30   (1000 TPS) ✅ primary

GENERAL / VISION / LONG_CONTEXT / MULTILINGUAL tier
  qwen/qwen3.6-27b              → input: $0.60   output: $3.00   (500 TPS)  ✅ primary (groq.com/pricing, Jun 22, 2026)
  openai/gpt-oss-120b           → input: $0.15   output: $0.60   (500 TPS)  ✅ GENERAL fallback

HEAVY tier
  openai/gpt-oss-120b           → input: $0.15   output: $0.60   (500 TPS)  ✅ primary

Note: gpt-oss-120b (HEAVY/GENERAL fallback) is cheaper than qwen3.6-27b (GENERAL) on output
due to MoE architecture — pricing follows model design, not tier rank.

Deprecated models (removed from active routing, Jun 2026):
  llama-3.1-8b-instant, llama-3.3-70b-versatile → removed Aug 16, 2026
  qwen/qwen3-32b, llama-4-scout-17b-16e-instruct → removed Jul 17, 2026
```

**MODEL_RATES in cost_model.py** uses the PRIMARY model of each tier for pre-execution estimation:

```python
# Актуальные значения (Jun 2026) — синхронизированы с model_router.py
MODEL_RATES = {
    Tier.FAST:    {"input": 0.075, "output": 0.30},   # openai/gpt-oss-20b (primary)
    Tier.GENERAL: {"input": 0.60,  "output": 3.00},   # qwen/qwen3.6-27b (primary)
    Tier.HEAVY:   {"input": 0.15,  "output": 0.60},   # openai/gpt-oss-120b (primary, stable)
}
```

EPK thresholds пересмотрены и откалиброваны под новые цены (Jun 2026) — см. §5 и §6.
При смене primary в model_router.py: обновить MODEL_RATES одновременно, затем пересчитать
MAX_OUTPUT_CAP и пример-таблицы в §5/§6.

**Why primary-only pricing for estimation:**
MODEL_RATES is used exclusively by `estimate_cost()` → EPK input (pre-execution safety gate).
EPK runs BEFORE model selection — it cannot know which GENERAL model will be chosen.
Using worst-case (primary = most expensive) is intentional: EPK must never underestimate.
This is a conservative safety bound, not a billing calculation.

`actual_cost()` uses the same MODEL_RATES but is called post-execution with real token counts.
When per-route billing is implemented (logging actual model per request), `actual_cost()`
will be updated to use per-model rates — no EPK changes required.

Note on HEAVY: gpt-oss-120b at $0.15/$0.60 is cheaper than qwen3.6-27b (GENERAL primary) on output
due to MoE architecture. This is correct and expected — HEAVY = more capable, not always more expensive.

**⚠️ ACTION REQUIRED при смене primary моделей:**
MODEL_RATES ДОЛЖЕН быть обновлён одновременно со сменой primary в model_router.py.
Если новый primary дороже текущего — обязательное обновление во избежание недооценки EPK.
Если дешевле — оценка станет избыточно консервативной (допустимо, но нежелательно).

### 1.2 Safety Layer (Groq-hosted)

```
meta-llama/llama-prompt-guard-2-22m    → input: $0.03  output: $0.03  per 1M tokens
meta-llama/llama-prompt-guard-2-86m    → input: $0.04  output: $0.04  per 1M tokens
openai/gpt-oss-safeguard-20b           → input: $0.075 output: $0.30  per 1M tokens
```

Safety models: billed per request passing through Safety Gate. No exceptions.
Both prompt-guard models are BERT classifiers — output is 1-2 tokens ("BENIGN"/"MALICIOUS"),
negligible cost. Billed conservatively at input rate for output tokens.

**EPK estimate (Variant C):** `estimate_safety_cost()` in `cost_model.py` adds a fixed
pre-execution overhead to every `estimate_cost()` call. Covers all three models:
~300 tokens × 22m rate + ~300 tokens × 86m rate + ~300 tokens × safeguard rate.
EPK sees full request cost including Safety Gate.

**Post-execution:** `actual_safety_cost(pass1_tokens, pass2_tokens, safeguard_tokens, safeguard_output_tokens)`
records real token counts from `GateResult` into `UsageEntry`:
- `pass1_tokens`              → `GateResult.tokens_used` from `check_pass1()` — billed at $0.03/1M (22m)
- `pass2_tokens`              → `GateResult.tokens_used` from `check_pass2()` — billed at $0.04/1M (86m only)
- `safeguard_tokens`          → `GateResult.safeguard_tokens_used` — billed at $0.075/1M (safeguard-20b input)
- `safeguard_output_tokens`   → `GateResult.safeguard_output_tokens_used` — billed at $0.30/1M (safeguard-20b output)

Note: `pass2_tokens` and `safeguard_tokens` are separate parameters — 86m and safeguard-20b
run concurrently in Pass 2 and are billed at different rates through different fields.
Enables estimate vs actual drift tracking per request.

### 1.3 Agent Layer (Compound — Groq-hosted)

```
groq/compound      → deep_agent.py  → passthrough pricing via underlying models
groq/compound-mini → fast_agent.py  → passthrough pricing via underlying models
```

**Compound passthrough pricing (verified Groq docs, Jun 2026):**
Groq compound systems use passthrough pricing — tokens are billed at the rates of the
underlying models that actually executed, not at a single compound-level rate.

```
compound-mini internals: Llama 3.3 70B + GPT-OSS 120B
  llama-3.3-70b-versatile          → input: $0.59  output: $0.79  per 1M
  openai/gpt-oss-120b              → input: $0.15  output: $0.60  per 1M

compound internals: Llama 4 Scout + GPT-OSS 120B
  meta-llama/llama-4-scout-17b-16e-instruct → input: $0.11  output: $0.34  per 1M
  openai/gpt-oss-120b              → input: $0.15  output: $0.60  per 1M
```

⚠️ Llama 4 Scout deprecated Jul 17, 2026 — Groq may update compound internals. Monitor compound docs.

**Billing implementation in cost_model.py:**

```python
# Per-model rates for exact passthrough billing via usage_breakdown
_COMPOUND_UNDERLYING_RATES = {
    "llama-3.3-70b-versatile":                    {"input": 0.59, "output": 0.79},
    "meta-llama/llama-4-scout-17b-16e-instruct":  {"input": 0.11, "output": 0.34},
    "openai/gpt-oss-120b":                        {"input": 0.15, "output": 0.60},
}

# Dominant-model fallback rates (used when usage_breakdown is absent)
_COMPOUND_RATES = {
    "groq/compound-mini": {"input": 0.59, "output": 0.79},  # Llama 3.3 70B dominant
    "groq/compound":      {"input": 0.15, "output": 0.60},  # GPT-OSS 120B dominant
}
```

**Billing flow (webhook.py):**
Groq API returns `usage.usage_breakdown` — a list of `{model, input_tokens, output_tokens}` per
underlying model. This enables exact per-model billing via `actual_compound_cost_from_breakdown()`.

```python
# Preferred path: exact billing from Groq API breakdown
if compound_breakdown:
    _compound_actual = actual_compound_cost_from_breakdown(compound_breakdown)
else:
    # Fallback: dominant-model approximation
    _compound_actual = actual_compound_cost(input_tokens, output_tokens, model)

# Delta vs FAST-tier proxy already baked into llm_cost_usd
_compound_cost_delta = _compound_actual - _fast_proxy
total_cost_usd += _compound_cost_delta
```

`groq_client.py` parses `usage.usage_breakdown` in both `complete()` and `complete_with_tools()`.
`LLMResponse.usage_breakdown` and `ToolCallResponse.usage_breakdown` carry the breakdown through
`AgentResult → CoordinationResult.usage_breakdown → OrchestratorResult.compound_breakdown → webhook.py`.

**Groq Built-In Tools pricing (verified groq.com/pricing, Jun 22, 2026):**
```
Basic Search       → $5.00  / 1000 requests  (web_search)
Advanced Search    → $8.00  / 1000 requests  (web_search — higher quality)
Visit Website      → $1.00  / 1000 requests  (visit_website)
Code Execution     → $0.18  / hour           (code_interpreter)
Browser Automation → $0.08  / hour           (browser_automation)
```
Ceyona использует compound как pure synthesizer (без custom tools=).
Если встроенные инструменты не вызываются — биллинг только за токены модели.
Compound tool call count (если будут использоваться) → usage_meter.py MUST record.

Compound tool calls (if any) are billed separately per call, not per token.
usage_meter.py MUST record tool call counts alongside token counts.

**Search provider costs (external, NOT Groq-billed):**
```
Tavily   (primary)   → free tier: 1000 req/mo | paid: $0.015/req above limit
SerpAPI  (secondary) → free tier: 250 searches/mo | paid plans from $50/mo
SearXNG  (tertiary)  → self-hosted: infrastructure cost only (Docker sidecar)
                       public instances: free, but unstable — not for production
```
Search provider costs are NOT deducted from user balance (external cost stream).
They are operational costs tracked separately from Groq/HF billing.
Compound tool call count (billed to user at $5.00/1000) covers the Groq API cost,
not the search provider API cost.

### 1.4 Speech Layer (Groq-hosted)

```
whisper-large-v3        → $0.111 / hour transcribed   (217x real-time)
whisper-large-v3-turbo  → $0.040 / hour transcribed   (228x real-time)

canopylabs/orpheus-v1-english    → $22.00 / 1M characters
canopylabs/orpheus-arabic-saudi  → $40.00 / 1M characters
```

Speech is billed per audio hour (ASR) and per character (TTS), NOT per token.
usage_meter.py MUST record audio seconds and TTS character counts separately.

### 1.5 Embeddings and Reranking — HuggingFace Serverless

⚠️ IMPORTANT: These models are NOT Groq-hosted.
They run on HuggingFace Inference API (serverless tier).
API key: HF_TOKEN (separate from GROQ_API_KEY).
Billing: HuggingFace account, NOT Groq account.
These costs are independent and must be tracked separately.

```
Provider: HuggingFace Serverless (hub.huggingface.co/inference-api)
Models:
  BAAI/bge-large-en-v1.5  → ~$0.10 / 1M tokens     (primary embedding)
  BAAI/bge-small-en-v1.5  → ~$0.02 / 1M tokens     (fast fallback embedding)
  BAAI/bge-reranker-large → ~$0.10 / 1M token-pairs (cross-encoder reranking)
```

HuggingFace serverless pricing is approximate — no official published rate.
These are conservative industry estimates. Actual cost may vary.
If embedding usage grows significantly, migrate to HF Inference Endpoints
(dedicated hardware with fixed, lower pricing).

```python
EMBEDDING_RATES = {
    "large": 0.10,   # BAAI/bge-large-en-v1.5 — HF serverless estimate
    "small": 0.02,   # BAAI/bge-small-en-v1.5 — HF serverless estimate
}
RERANK_RATE = 0.10  # BAAI/bge-reranker-large — per 1M token-pairs, HF serverless estimate
```

### 1.6 Multilingual Normalization (Groq-hosted)

```
allam-2-7b → Arabic normalization
           → no public pricing listed on Groq
           → treated as FAST tier equivalent: $0.075 input / $0.30 output per 1M
             (matches gpt-oss-20b FAST rates — cost_model.py _MULTILINGUAL_RATES)

qwen/qwen3.6-27b → non-Arabic multilingual normalization
                 → GENERAL tier: $0.60 input / $3.00 output per 1M
```

---

## 2. BILLING PRINCIPLE — NO FREE RIDES

**Every model call that produces a response MUST be billed.**

This applies without exception to:
- all LLM tier calls (FAST / GENERAL / HEAVY)
- Safety Layer calls (both passes)
- Consensus arbiter calls
- heavy_input_shaper calls
- Agent Layer calls (token + tool call counts)
- Speech Layer calls (audio seconds / TTS characters)
- Embedding calls — HuggingFace, tracked separately from Groq costs
- Reranker calls — HuggingFace, tracked separately from Groq costs

**Two cost streams — must be tracked independently:**
- Groq costs → GROQ_API_KEY account
- HuggingFace costs → HF_TOKEN account (embeddings + reranker)

**The only calls NOT billed to user balance:**
- Failed calls that returned no output (API error, timeout, empty response)
- Internal system calls that never reach the user (logging, observability)

---

## 3. OUTPUT ESTIMATION (PRE-EXECUTION)

Used by EPK to evaluate request before execution.

```python
COMPLEXITY_MULTIPLIER = {
    Complexity.LOW:      1.2,
    Complexity.MEDIUM:   1.8,
    Complexity.HIGH:     2.5,
    Complexity.CRITICAL: 3.0,
}

# Conservative cap for cost estimation only.
# NOT the same as model_router._MAX_TOKENS (API hard limits — different purpose).
# Intentionally lower: estimate must be a safe upper bound, not an exact prediction.
# model_router._MAX_TOKENS controls actual Groq API max_tokens parameter.
# These control EPK cost gate input. They MUST NOT be equal.
MAX_OUTPUT_CAP = {
    Tier.FAST:    512,    # estimation cap (actual API limit: 1024)
    Tier.GENERAL: 800,    # estimation cap — lowered from 2048 for qwen3.6-27b ($3.00/output per 1M).
                          # At 2048 estimated output tokens: (1000×0.60 + 2048×3.00)/1M ≈ $0.0068 → DEGRADED_MODE.
                          # At 800 estimated output tokens:  (1000×0.60 + 800×3.00)/1M  ≈ $0.003  → ALLOW boundary.
                          # actual API limit remains 3072 (policy_registry.py) — this is EPK estimation only.
    Tier.HEAVY:   4096,   # estimation cap (actual API limit: 6144)
}

def estimate_output_tokens(input_tokens, complexity, tier):
    raw = int(input_tokens * COMPLEXITY_MULTIPLIER[complexity])
    return min(raw, MAX_OUTPUT_CAP[tier])
```

**Critical distinction — two separate authorities:**

| Value | Location | Purpose | Should equal? |
|---|---|---|---|
| `MAX_OUTPUT_CAP` | cost_model.py | Conservative EPK estimation bound | NO |
| `_MAX_TOKENS` | model_router.py | Actual Groq API hard limit | NO |

These MUST NOT be identical. Different purposes, different authorities.

---

## 4. COST FUNCTIONS

Two variants — same signature except for one parameter: `estimated_output_tokens` (pre-execution, capped) vs `output_tokens` (post-execution, actual from API response).

### 4.1 Pre-execution estimate (EPK input)

```python
def estimate_cost(
    input_tokens,
    estimated_output_tokens,  # capped by MAX_OUTPUT_CAP — conservative bound
    embedding_tokens,
    rerank_tokens,
    tier,
    embedding_type="large",
) -> float:
    rates = MODEL_RATES[tier]
    return (
        input_tokens * rates["input"]
        + estimated_output_tokens * rates["output"]
        + embedding_tokens * EMBEDDING_RATES[embedding_type]
        + rerank_tokens * RERANK_RATE
    ) / 1_000_000
```

Uses primary model rates (worst-case). Conservative by design — EPK must not underestimate.

### 4.2 Post-execution actual cost (billing)

```python
def actual_cost(
    input_tokens: int,
    output_tokens: int,                    # real token counts from Groq usage response
    embedding_tokens: int,
    rerank_tokens: int,
    tier: Tier,
    embedding_type: str = "large",
    # Safety Gate tokens — optional, default 0 (not all paths call Safety Gate)
    safety_pass1_tokens: int = 0,          # llama-prompt-guard-2-22m input tokens
    safety_pass2_tokens: int = 0,          # llama-prompt-guard-2-86m input tokens
    safety_safeguard_tokens: int = 0,      # gpt-oss-safeguard-20b input tokens
    safety_safeguard_output_tokens: int = 0,  # gpt-oss-safeguard-20b output tokens (added v5.6)
) -> float:
```

Note: safety parameters exist in the function signature but Safety Gate billing is handled
separately via `actual_safety_cost()` in the orchestrator and webhook — `actual_cost()` is
called for LLM + retrieval cost only. The safety parameters are present for future unified
billing path.

Currently uses primary model rates per tier.
When per-route billing is implemented (logging actual model name per request),
update MODEL_RATES lookup to per-model rates — `actual_cost()` signature unchanged.

---

## 5. EPK — PRE-EXECUTION POLICY

EPK is the sole policy authority. It evaluates estimated cost before any execution.

```python
_DENY_THRESHOLD:    float = 0.0001  # balance ≤ 0 or effectively zero
_DEGRADE_THRESHOLD: float = 0.006   # above this → DEGRADED_MODE (raised from 0.003, calibrated to qwen3.6-27b $3.00/output)
_HEAVY_THRESHOLD:   float = 0.010   # above this → HEAVY_REQUIRED (raised from 0.008)

def evaluate(estimated_cost, user_balance) -> EPKDecision:
    """
    OUTPUT: ALLOW | DENY | DEGRADED_MODE | HEAVY_REQUIRED
    Rules evaluated in strict order — first match wins.
    """
    # 1. DENY: no balance or cost exceeds balance
    if user_balance <= 0 or estimated_cost > user_balance:
        return EPKDecision.DENY

    # 2. HEAVY_REQUIRED: large expensive request → gpt-oss-120b mandatory
    if estimated_cost > _HEAVY_THRESHOLD:
        return EPKDecision.HEAVY_REQUIRED

    # 3. DEGRADED_MODE: oversized for GENERAL → Fast Tier only
    if estimated_cost > _DEGRADE_THRESHOLD:
        return EPKDecision.DEGRADED_MODE

    # 4. ALLOW: normal execution
    return EPKDecision.ALLOW
```

**All four signals are active. Evaluation order is strictly top-down:**
DENY → HEAVY_REQUIRED → DEGRADED_MODE → ALLOW

EPK does NOT select tier. Tier selection happens in decision_matrix.py, AFTER EPK returns ALLOW.

**Multi-intent requests (architecture.md §44.5):** EPK receives summed estimated_cost
of all sub-intents. Atomicity: if sum exceeds threshold → DENY applies to entire request.
Partial execution (some sub-intents ALLOW, others DENY) is forbidden.

**⚠️ CRITICAL path overhead (lc_transformer):**
EPK routes `complexity == CRITICAL` to `HEAVY_REQUIRED` based on estimated cost only.
The long-context transformer (qwen3.6-27b, $0.60/$3.00 per 1M) is activated AFTER EPK,
inside `_run_heavy()`, when `input_tokens > 32 000`. Its cost is NOT included in the EPK
estimate — it is charged on top of the HEAVY tier cost.

For a CRITICAL request with 40K input tokens, lc_transformer adds up to:
`(40000 × 0.60 + 800 × 3.00) / 1M ≈ $0.026` on top of the HEAVY execution cost.

This means EPK may allow a request whose total real cost exceeds the user balance.
The gap is bounded by lc_transformer cost only (bounded by input size).
No fix planned — lc_transformer cannot run before EPK (circular dependency).
Mitigation: ensure free trial balance ($0.10) comfortably covers worst-case overhead.

**What these thresholds mean in practice (at GENERAL primary rates: $0.60/$3.00 per 1M):**
- 500 input + 600 estimated output at GENERAL = (500×0.60 + 600×3.00)/1M = $0.0021 → ALLOW
- 1000 input + 800 estimated output at GENERAL = (1000×0.60 + 800×3.00)/1M = $0.0030 → ALLOW
- 2000 input + 800 estimated output at GENERAL = (2000×0.60 + 800×3.00)/1M = $0.0036 → ALLOW
- 2000 input + 2000 estimated output at GENERAL = (2000×0.60 + 2000×3.00)/1M = $0.0072 → DEGRADED_MODE
- 5000 input + 4096 estimated output at GENERAL = (5000×0.60 + 4096×3.00)/1M = $0.0153 → HEAVY_REQUIRED

Note: MAX_OUTPUT_CAP[GENERAL] = 800 tokens (EPK estimation cap) — most GENERAL requests
are estimated at ≤800 output tokens and land in ALLOW. Actual responses may be longer;
EPK cap is a conservative estimation bound, not a hard output limit.

---

## 6. DECISION MATRIX — TIER SELECTION

Called ONLY after EPK returns ALLOW. HEAVY_REQUIRED and DEGRADED_MODE bypass this.

```python
# Ascending order is mandatory — enforced by design.
_FAST_CEILING:    float = 0.001   # below $0.001 → FAST (raised from 0.0005; FAST now $0.30/output gpt-oss-20b)
_GENERAL_CEILING: float = 0.006   # below $0.006 → GENERAL (= EPK _DEGRADE_THRESHOLD)
# above $0.006 → HEAVY (theoretically unreachable on ALLOW path — EPK gates at $0.010)

def select_tier(estimated_cost: float) -> Tier:
    if estimated_cost < _FAST_CEILING:
        return Tier.FAST
    if estimated_cost < _GENERAL_CEILING:
        return Tier.GENERAL
    return Tier.HEAVY
```

**What these thresholds mean in practice (at FAST rates $0.075/$0.30 per 1M):**
- 500 input + 300 estimated output  = (500×0.075 + 300×0.30)/1M = $0.000128 → FAST
- 3000 input + 512 estimated output = (3000×0.075 + 512×0.30)/1M = $0.000379 → FAST
- 5000 input + 512 estimated output = (5000×0.075 + 512×0.30)/1M = $0.000529 → GENERAL

At GENERAL rates ($0.60/$3.00 per 1M):
- 1000 input + 800 estimated output = (1000×0.60 + 800×3.00)/1M = $0.0030 → GENERAL
- 1500 input + 800 estimated output = (1500×0.60 + 800×3.00)/1M = $0.0033 → GENERAL
- 2000 input + 800 estimated output = (2000×0.60 + 800×3.00)/1M = $0.0036 → GENERAL

**Bug fixed (v5.0):**
Previously values were `_FAST_CEILING = 0.05` and `_GENERAL_CEILING = 0.003`.
Since 0.05 > 0.003, GENERAL was unreachable — every request went FAST or HEAVY.
Corrected to ascending order: 0.001 < 0.006.

**Synchronization contract:**
`_GENERAL_CEILING` MUST equal EPK `_DEGRADE_THRESHOLD` (both = 0.006).
`_FAST_CEILING` MUST equal `RUNTIME.epk.fast_ceiling` (both = 0.001).
Both values live in `policy_registry.py` as the single source of truth.
decision_matrix.py and execution_policy_kernel.py read from RUNTIME automatically.
Any change to thresholds: update policy_registry.py only.

---

## 7. USAGE METER — MANDATORY FIELDS

Every request MUST record. Full schema of `UsageEntry` in `payments/usage_meter.py`:

```python
usage = {
    # ── Core LLM tokens (Groq) ──────────────────────────────────────────────
    "input_tokens":      int,    # from Groq response.usage.prompt_tokens
    "output_tokens":     int,    # from Groq response.usage.completion_tokens
    "tier":              str,    # Tier.FAST / GENERAL / HEAVY
    "model":             str,    # agent model (final executing model from coordination.model)
    "resolved_model":    str,    # preferred_model from model_router (models.md §25.3)
                                 # empty string on DEGRADED_MODE (no routing, always gpt-oss-20b)

    # ── Retrieval (HuggingFace — separate cost stream) ───────────────────────
    "embedding_tokens":  int,    # tokens sent to HF embedding API
    "embedding_type":    str,    # "large" or "small"
    "rerank_tokens":     int,    # token-pairs sent to HF reranker

    # ── Cost fields ──────────────────────────────────────────────────────────
    "raw_cost_usd":      float,  # total_cost_usd from webhook (LLM + safety + multilingual)
                                 # does NOT include 30% margin
    "billed_cost_usd":  float,   # raw_cost_usd × 1.3 — what platform records as revenue

    # ── Speech — Groq (if applicable, default 0) ─────────────────────────────
    "audio_seconds":     float,  # for ASR billing (whisper), default 0.0
    "tts_characters":    int,    # for TTS billing (orpheus), default 0

    # ── Tool calls — Groq Compound (if applicable, default 0) ────────────────
    "tool_calls":        int,    # compound web_search calls, $5.00/1000

    # ── Safety Gate tokens (Groq, default 0 per field) ───────────────────────
    # Populated by update_handler.py AFTER gate completes; always 0 at orchestrator return.
    # Billed via actual_safety_cost() in webhook.py — included in raw_cost_usd.
    "safety_pass1_tokens":             int,   # llama-prompt-guard-2-22m input tokens
    "safety_pass2_tokens":             int,   # llama-prompt-guard-2-86m input tokens
    "safety_safeguard_tokens":         int,   # gpt-oss-safeguard-20b input tokens ($0.075/1M)
    "safety_safeguard_output_tokens":  int,   # gpt-oss-safeguard-20b output tokens ($0.30/1M)
    "safety_agent_input_tokens":       int,   # safety_agent LLM judge input tokens ($0.075/1M)
    "safety_agent_output_tokens":      int,   # safety_agent LLM judge output tokens ($0.30/1M)

    # ── Multilingual preprocessor (Groq, default 0) ──────────────────────────
    # On ALLOW/DEGRADED: billed via actual_multilingual_cost() in webhook.py.
    # On HEAVY: already included in result.usage.cost_usd by _run_heavy().
    # webhook.py guards against double-billing (skips if epk_decision == HEAVY_REQUIRED).
    "multilingual_input_tokens":   int,   # allam-2-7b or qwen3.6-27b input tokens
    "multilingual_output_tokens":  int,   # allam-2-7b or qwen3.6-27b output tokens
    "multilingual_model":          str,   # "allam-2-7b" | "qwen/qwen3.6-27b" | "passthrough"

    # ── Long-context transformer (Groq, default 0) ───────────────────────────
    # qwen3.6-27b, GENERAL tier rates ($0.60/$3.00 per 1M).
    # Billed inside _run_heavy() — included in result.usage.cost_usd.
    "lc_transformer_input_tokens":   int,  # qwen3.6-27b input tokens
    "lc_transformer_output_tokens":  int,  # qwen3.6-27b output tokens

    # ── Metadata ─────────────────────────────────────────────────────────────
    "intent":  str,   # classified intent value (for analytics)
    "lang":    str,   # request language code, default "en"
}
```

**`result.usage.cost_usd` semantics (IMPORTANT):**
This field is NOT the total request cost. It represents LLM execution cost only:
- On ALLOW/DEGRADED paths: `cost_usd` = LLM tokens + embedding + rerank (no safety, no multilingual)
- On HEAVY path: `cost_usd` = LLM tokens + embedding + rerank + lc_transformer + shaper + safety_agent

Safety Gate cost and multilingual cost on ALLOW/DEGRADED are added in `webhook.py`:
```python
total_cost_usd = result.usage.cost_usd + safety_cost + _ml_cost
```
`total_cost_usd` is what gets deducted from the user balance and recorded as `raw_cost_usd`.
`result.usage.cost_usd` alone is semantically incomplete — always use `raw_cost_usd` from
`UsageEntry` for analytics, never `result.usage.cost_usd` directly.

Without complete usage_meter data the system cannot bill correctly.
Missing fields = unbillable request = revenue leak.

HuggingFace costs (embedding_tokens, rerank_tokens) must be tracked separately
from Groq costs for accurate split billing and quota management.

---

## 8. MARGIN AND USER BILLING

### Revenue model (DECIDED — Jun 2026)

Platform margin is captured at **top-up time via TON→USD conversion rate**, not at
per-request deduction. This is the intentional architecture.

`ac.deduct(user_id, total_cost_usd)` correctly deducts **raw cost** from balance.
Applying × 1.3 at deduction time would double-charge margin and must NOT be done.

```python
MARGIN = 1.3   # target markup — applies to billed_cost_usd analytics and top-up rate
```

### Correct billing flow (webhook.py)

```python
# 1. Compute total raw cost from all components
total_cost_usd = result.usage.llm_cost_usd + safety_cost + _ml_cost

# 2. Deduct RAW cost from user balance  ← correct, margin is in top-up conversion rate
await ac.deduct(user_id, total_cost_usd)

# 3. Compute billed for revenue analytics only
billed = meter.compute_billed(total_cost_usd)   # total_cost_usd × 1.3

# 4. Record both raw and billed to Supabase
await meter.record(UsageEntry(
    raw_cost_usd=total_cost_usd,
    billed_cost_usd=billed,
    ...
))
```

### What `billed_cost_usd` is for

`billed_cost_usd` (= `raw_cost_usd × 1.3`) is a **revenue analytics field**.
It is recorded to Supabase on every request but is NOT deducted from user balance.

Purpose:
- **Revenue tracking:** `SUM(billed_cost_usd)` = theoretical gross revenue per period
- **Profitability analysis:** `billed_cost_usd − raw_cost_usd` = 30% per-request margin target
- **Migration path:** if revenue model ever switches to per-request markup, this field already
  contains the correct value — one line change: `ac.deduct(user_id, billed)`

### Top-up conversion rate — open action item

`pricing_engine.nano_to_usd()` currently uses live CoinGecko market rate with **no markup**.
The margin model requires a spread to be applied here:

```python
# pricing_engine.py — nano_to_usd() — CURRENT (0% margin)
return ton * price

# TO ACTIVATE MARGIN — apply before going to production at scale:
TOPUP_RATE = 1.0 / 1.3   # user receives ~76.9% of market rate in USD credits
return ton * price * TOPUP_RATE
```

⚠️ **Until `TOPUP_RATE` is applied in `pricing_engine.py`, platform earns 0% margin.**
`billed_cost_usd` exists and is correct — revenue mechanism just needs to be activated
at the top-up layer. This is the single open action item for the billing system.

---

## 9. FREE TRIAL BALANCE

```python
# access_controller.py
_DEFAULT_BALANCE_USD = 0.10   # $0.10 free trial
```

Capacity at FAST tier ($0.075/$0.30 per 1M, ~500 token requests):
≈ 30-60 short queries on FAST tier (~500 input + 300 output = $0.000128/query × 1.3 margin)
≈ 3-5 queries on GENERAL tier (~1000 input + 800 output = $0.003/query × 1.3 margin)

When balance drops below $0.10 threshold → webhook.py sends low_balance_warning.
When balance reaches $0.00 → EPK returns DENY → user sees balance_exhausted message.

---

## 10. EXECUTION FLOW (BILLING PERSPECTIVE)

> **Note:** this section describes when costs are **recorded**, not physical execution order.
> Physical execution order: architecture.md §4 (canonical lifecycle).
> Key distinction: Safety Gate executes **before** EPK and may short-circuit the request.
> Billing: if the request reaches confirmation, Safety Gate usage is accounted in the billing phase.

```
1.  input received
2.  [Safety Gate Pass 1 + Pass 2 execute here — before EPK, see architecture.md §4]
3.  embedding (retrieval)       → bill: embedding_tokens [HuggingFace]
4.  reranker                    → bill: rerank_tokens [HuggingFace]
5.  estimate_cost()             → EPK input (no billing yet)
6.  EPK: DENY / ALLOW / DEGRADED_MODE / HEAVY_REQUIRED
7.  [DENY → exit, no LLM billing; Safety Gate cost IS billed if gate tokens present on result]
7b. [VERBATIM → exit, no LLM billing, tool cost only — §47]
8.  Safety Gate usage           → bill: safety tokens [Groq]  ← recorded post-confirmation
9.  select_tier() [ALLOW only]
10. LLM execution               → bill: input_tokens + output_tokens [Groq]
11. [Compound tool calls]       → bill: tool_calls count [Groq]
12. [Speech if is_voice_input]  → bill: audio_seconds / tts_characters [Groq]
13. usage_meter records all fields
14. total_cost_usd = result.usage.cost_usd + safety_cost + _ml_cost  (webhook.py)
15. ac.deduct(user_id, total_cost_usd)   ← raw cost deducted from balance (correct, see §8)
16. billed_cost_usd = total_cost_usd × 1.3
17. usage_log written to Supabase (raw_cost_usd + billed_cost_usd)
18. response delivered
```

**OrchestratorResult safety fields lifecycle:**
`OrchestratorResult.safety_pass1_tokens`, `.safety_pass2_tokens`, `.safety_safeguard_tokens`,
`.safety_safeguard_output_tokens` are **always 0 at orchestrator return** on ALLOW/DEGRADED paths.
They are populated by `update_handler.py` via `dataclasses.replace()` AFTER the gate completes,
before the result reaches `webhook.py`. Do not read these fields inside the orchestrator — they
will be 0. Only `webhook.py` and `usage_meter.py` see the final populated values.

`safety_agent_input_tokens` / `safety_agent_output_tokens` are the exception: these are set
by the orchestrator itself (filled from `CoordinationResult`) and are correct at orchestrator return.

---

## 11. SYNCHRONIZATION CONTRACTS

This document is synchronized with:

**models.md** — model names, tier assignments, fallback order:
- FAST primary: openai/gpt-oss-20b — $0.075/$0.30 per 1M ✓
- FAST fallback: gemma2-9b-it REMOVED (deprecated Aug 2025) ✓
- GENERAL primary: qwen/qwen3.6-27b — $0.60/$3.00 per 1M ✓
- HEAVY primary: openai/gpt-oss-120b — $0.15/$0.60 per 1M ✓
- VISION: qwen/qwen3.6-27b — $0.60/$3.00 per 1M (billing in pricing_engine._VISION_RATES) ✓
- LONG_CONTEXT: qwen/qwen3.6-27b — same rates, billed as lc_transformer tokens ✓
- MULTILINGUAL: qwen/qwen3.6-27b (primary) + allam-2-7b (Arabic) ✓
- canopylabs/orpheus-v1-english → $22.00/1M chars ✓
- canopylabs/orpheus-arabic-saudi → $40.00/1M chars ✓
- BAAI/bge-* → HuggingFace (NOT Groq) ✓
- llama-4-scout, llama-3.3-70b-versatile, qwen3-32b, llama-3.1-8b-instant → deprecated, removed from active routing ✓

**architecture.md** — EPK signals and execution paths:
- EPK signals: ALLOW / DENY / DEGRADED_MODE / HEAVY_REQUIRED ✓
- DEGRADED_MODE → Fast Tier only ✓
- HEAVY_REQUIRED → bypasses select_tier() ✓
- Safety Gate → both passes billed ✓

**decision_matrix.py** — reads from RUNTIME (policy_registry.py), no hardcoded values:
- `_FAST_CEILING = RUNTIME.epk.fast_ceiling` = 0.001 ✓
- `_GENERAL_CEILING = RUNTIME.epk.degrade_threshold` = 0.006 ✓

**execution_policy_kernel.py** — reads from RUNTIME (policy_registry.py):
- `_DEGRADE_THRESHOLD = RUNTIME.epk.degrade_threshold` = 0.006 ✓
- `_HEAVY_THRESHOLD = RUNTIME.epk.heavy_threshold` = 0.010 ✓

**access_controller.py** — initial balance must match this document:
- `_DEFAULT_BALANCE_USD = 0.10` ✓

---

## 12. OPEN ITEMS (FUTURE)

- [x] **Jul 17, 2026:** qwen/qwen3-32b и llama-4-scout заменены на qwen3.6-27b и gpt-oss-20b в model_router.py. MODEL_RATES обновлены. ✅ CLOSED
- [x] **Aug 16, 2026:** llama-3.1-8b-instant и llama-3.3-70b-versatile — заменены (gpt-oss-20b как FAST primary, qwen3.6-27b как GENERAL). ✅ CLOSED
- [x] **qwen/qwen3.6-27b Groq pricing:** опубликована Jun 22, 2026 — $0.60/$3.00 per 1M tokens. Добавлена в §1.1. ✅ CLOSED
- [x] **Vision billing fix (Jun 2026):** _VISION_RATES обновлены с llama-4-scout ($0.11/$0.34) на qwen3.6-27b ($0.60/$3.00). ✅ CLOSED
- [x] **DENY billing fix (Jun 2026):** Safety Gate tokens биллятся на DENY путях (voice pass1 block). webhook.py guard обновлён. ✅ CLOSED
- [x] **actual_cost() safeguard output (Jun 2026):** добавлен параметр safety_safeguard_output_tokens. ✅ CLOSED
- [x] **MISMATCH-A4 (CLOSED Jun 2026):** Revenue model decided — margin via TON→USD conversion rate at top-up, not per-request deduction. `ac.deduct(raw)` is correct. `billed_cost_usd` is analytics field. §8 updated. ✅
- [ ] **TOPUP_RATE (ACTION REQUIRED before production scale):** `pricing_engine.nano_to_usd()` uses live market rate with no markup. Apply `TOPUP_RATE = 1.0 / 1.3` to activate 30% margin. See §8.
- [ ] Per-route billing: preferred_model now logged per-request (models.md §25.3) → update actual_cost() to use per-model rates when ready
- [x] **Multilingual billing на ALLOW/DEGRADED путях (Jun 2026):** webhook.py вычисляет `_ml_cost` на ALLOW/DEGRADED; на HEAVY пропускается (cost_usd уже включает). ✅ CLOSED
- [x] **Compound/compound-mini billing (CLOSED Jun 2026):** Groq confirmed passthrough pricing. `_COMPOUND_RATES`, `_COMPOUND_UNDERLYING_RATES`, and `actual_compound_cost_from_breakdown()` implemented in `cost_model.py`. `groq_client.py` parses `usage.usage_breakdown`. Exact per-model billing active in `webhook.py`. `§1.3` updated. ✅
- [x] **allam-2-7b pricing (Jun 2026):** нет публичного листинга — зафиксировано как FAST equivalent $0.075/$0.30 per 1M. §1.6 обновлён. ✅ CLOSED
- [ ] HF Inference Endpoints pricing if serverless quota exceeded
- [ ] Batch API discount (50%) — applicable when usage grows, not yet implemented
- [ ] Prompt caching discount (50% input) — applicable for high cache-hit workloads