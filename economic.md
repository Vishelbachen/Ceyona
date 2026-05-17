# CEYONA — ECONOMIC MODEL
Version: 5.0 — Synchronized Edition
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
Model roles and tier assignments → models1.md
Architecture and DAG → architecture.md

---

## 1. MODEL PRICING — SINGLE SOURCE OF TRUTH

All rates in USD per 1M tokens. Verified from groq.com/pricing, May 2026.

### 1.1 LLM Tiers

```
FAST tier
  llama-3.1-8b-instant     → input: $0.05   output: $0.08   (840 TPS)
  [fallback removed: gemma2-9b-it deprecated by Groq, Aug 2025]

GENERAL tier
  llama-3.3-70b-versatile  → input: $0.59   output: $0.79   (394 TPS)
  qwen/qwen3-32b           → input: $0.29   output: $0.59   (662 TPS)
  openai/gpt-oss-20b       → input: $0.075  output: $0.30   (1000 TPS)

HEAVY tier
  openai/gpt-oss-120b      → input: $0.15   output: $0.60   (500 TPS)
  llama-4-scout-17b-16e    → input: $0.11   output: $0.34   (594 TPS)
```

**MODEL_RATES in cost_model.py** uses the PRIMARY model of each tier:

```python
MODEL_RATES = {
    Tier.FAST:    {"input": 0.05,  "output": 0.08},   # llama-3.1-8b-instant
    Tier.GENERAL: {"input": 0.59,  "output": 0.79},   # llama-3.3-70b-versatile (primary)
    Tier.HEAVY:   {"input": 0.15,  "output": 0.60},   # openai/gpt-oss-120b (primary)
}
```

Note on HEAVY: gpt-oss-120b at $0.15/$0.60 is cheaper than GENERAL llama-3.3-70b on output
due to MoE architecture. This is correct and expected — HEAVY = more capable, not always more expensive.

### 1.2 Safety Layer

```
openai/gpt-oss-safeguard-20b → input: $0.075  output: $0.30
```

Safety models are billed identically to gpt-oss-20b (same pricing).
Billing: every request passing through Safety Gate is charged.
No exceptions. Safety model fired = cost recorded.

### 1.3 Agent Layer (Compound)

```
groq/compound      → deep_agent.py  → $5.00 / 1000 web_search tool calls
groq/compound-mini → fast_agent.py  → pricing TBD (not publicly listed, May 2026)
```

Compound tool calls (web search) are billed separately per call, not per token.
usage_meter.py MUST record tool call counts alongside token counts.

### 1.4 Speech Layer

```
whisper-large-v3        → $0.111 / hour transcribed   (217x real-time)
whisper-large-v3-turbo  → $0.040 / hour transcribed   (228x real-time)

orpheus-v1-english      → $22.00 / 1M characters
orpheus-arabic-saudi    → $40.00 / 1M characters
```

Speech is billed per audio hour (ASR) and per character (TTS), NOT per token.
usage_meter.py MUST record audio seconds and TTS character counts separately.

### 1.5 Embeddings and Reranking (HuggingFace Serverless)

```
BAAI/bge-large-en-v1.5  → ~$0.10 / 1M tokens  (HF serverless estimate)
BAAI/bge-small-en-v1.5  → ~$0.02 / 1M tokens
BAAI/bge-reranker-large → ~$0.10 / 1M token-pairs
```

HuggingFace serverless pricing is approximate — no official published rate.
These are conservative estimates. If usage grows, move to HF Inference Endpoints
with dedicated pricing.

```python
EMBEDDING_RATES = {
    "large": 0.10,
    "small": 0.02,
}
RERANK_RATE = 0.10  # per 1M token-pairs
```

### 1.6 Multilingual Normalization

```
allam-2-7b → Arabic normalization — no public pricing listed on Groq (May 2026)
             treat as FAST tier equivalent: $0.05 input / $0.08 output
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
- Embedding calls (retrieval + intent classification)
- Reranker calls

**If a model answered → cost was incurred → user balance is decremented.**

The only calls NOT billed to user balance:
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
# NOT the same as model_router._MAX_TOKENS (API hard limits).
# These are intentionally lower — estimate must be safe, not exact.
MAX_OUTPUT_CAP = {
    Tier.FAST:    512,    # estimation cap (actual API limit: 1024)
    Tier.GENERAL: 2048,   # estimation cap (actual API limit: 3072)
    Tier.HEAVY:   4096,   # estimation cap (actual API limit: 6144)
}

def estimate_output_tokens(input_tokens, complexity, tier):
    raw = int(input_tokens * COMPLEXITY_MULTIPLIER[complexity])
    return min(raw, MAX_OUTPUT_CAP[tier])
```

**Critical distinction:**
- `MAX_OUTPUT_CAP` → cost_model.py → conservative pre-execution estimate
- `_MAX_TOKENS` → model_router.py → actual Groq API `max_tokens` parameter
- These values MUST NOT be identical. They serve different purposes.
- The misleading comment "matches model_router._MAX_TOKENS exactly" has been removed.

---

## 4. COST FUNCTIONS

### 4.1 Pre-execution estimate (EPK input)

```python
def estimate_cost(
    input_tokens,
    estimated_output_tokens,
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

### 4.2 Post-execution actual cost (billing)

```python
def actual_cost(
    input_tokens,
    output_tokens,
    embedding_tokens,
    rerank_tokens,
    tier,
    embedding_type="large",
) -> float:
    rates = MODEL_RATES[tier]
    return (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
        + embedding_tokens * EMBEDDING_RATES[embedding_type]
        + rerank_tokens * RERANK_RATE
    ) / 1_000_000
```

The difference: `estimated_output_tokens` (pre) vs `output_tokens` (actual from usage_meter).

---

## 5. EPK — PRE-EXECUTION POLICY

```python
_DEGRADE_THRESHOLD = 0.003   # USD — above this: DEGRADED_MODE
_DENY_MULTIPLIER   = 1.0     # estimated_cost > user_balance → DENY

def evaluate_request(estimated_cost, user_balance):
    if estimated_cost > user_balance:
        return EPKSignal.DENY

    if estimated_cost > _DEGRADE_THRESHOLD:
        return EPKSignal.DEGRADED_MODE

    return EPKSignal.ALLOW
```

EPK does NOT select the tier. EPK only gates execution.
Tier selection happens in decision_matrix.py, AFTER EPK returns ALLOW.

---

## 6. DECISION MATRIX — TIER SELECTION

**Critical bug fixed in this version:**

Previous code had `_FAST_CEILING = 0.05` and `_GENERAL_CEILING = 0.003`.
Since 0.05 > 0.003, every request went to FAST (below $0.05) or HEAVY (above $0.05).
GENERAL tier was unreachable. This is now corrected.

```python
# Correct thresholds — ascending order enforced
_FAST_CEILING:    float = 0.0005   # below $0.0005 estimated cost → FAST
_GENERAL_CEILING: float = 0.003    # below $0.003 → GENERAL (matches EPK degrade threshold)

def select_tier(estimated_cost: float) -> Tier:
    """
    Called ONLY after EPK returns ALLOW.
    HEAVY_REQUIRED and DEGRADED_MODE bypass this — tier is implicit in EPK signal.
    """
    if estimated_cost < _FAST_CEILING:
        return Tier.FAST
    if estimated_cost < _GENERAL_CEILING:
        return Tier.GENERAL
    return Tier.HEAVY
```

**What these thresholds mean in practice:**

At FAST tier rates ($0.05 input / $0.08 output per 1M):
- A 500-token input + 300-token estimated output = $0.000049
- Threshold $0.0005 → requests under ~5000 combined tokens → FAST
- This covers: greetings, short questions, simple weather queries

At GENERAL tier rates ($0.59 input / $0.79 output per 1M):
- A 1000-token input + 1200-token output = $1.53 / 1M → $0.00153
- Threshold $0.003 → medium complexity queries → GENERAL
- This covers: analysis, code, search synthesis, route queries

HEAVY: above $0.003 estimated cost.
- Covers: deep reasoning, long documents, multi-source synthesis

---

## 7. USAGE METER — MANDATORY FIELDS

Every request MUST record:

```python
usage = {
    # LLM tokens
    "input_tokens":      int,   # from Groq response.usage.prompt_tokens
    "output_tokens":     int,   # from Groq response.usage.completion_tokens
    "tier":              str,   # Tier.FAST / GENERAL / HEAVY

    # Retrieval
    "embedding_tokens":  int,   # tokens sent to HF embedding API
    "embedding_type":    str,   # "large" or "small"
    "rerank_tokens":     int,   # token-pairs sent to reranker

    # Speech (if applicable)
    "audio_seconds":     float, # for ASR billing
    "tts_characters":    int,   # for TTS billing

    # Tool calls (if applicable)
    "tool_calls":        int,   # compound web_search calls
}
```

Without complete usage_meter data the system cannot bill correctly.
Missing fields = unbillable request = revenue leak.

---

## 8. MARGIN AND USER BILLING

```python
MARGIN = 1.3   # 30% markup over raw LLM cost

def user_charge(actual_cost_usd: float) -> float:
    return actual_cost_usd * MARGIN
```

Margin rationale: covers HF costs (partially estimated), operational overhead,
and provides sustainable revenue. 30% is conservative — revisit when usage data
is available.

TON billing:
```python
# access_controller.py
credits_usd = actual_cost * MARGIN
# deduct credits_usd from user_balance_usd
# log to Supabase usage_log table
```

---

## 9. FREE TRIAL BALANCE

```python
# access_controller.py
_DEFAULT_BALANCE_USD = 0.10   # $0.10 free trial (≈ 50-100 FAST requests)
```

Previous value was $1.00 — too generous, extended indefinitely without monetization.
$0.10 provides enough to meaningfully test the bot (~50-100 short queries on FAST tier,
~5-10 queries on GENERAL tier) without providing unlimited free usage.

When balance drops below $0.10 → webhook.py sends low_balance_warning with topup button.
When balance reaches $0.00 → EPK returns DENY → user sees balance_exhausted message.

---

## 10. EXECUTION FLOW (BILLING PERSPECTIVE)

```
1. input received
2. embedding (retrieval)       → bill: embedding_tokens
3. reranker                    → bill: rerank_tokens
4. estimate_cost()             → EPK input (no billing yet)
5. EPK: DENY / ALLOW / DEGRADE / HEAVY_REQUIRED
6. [DENY → exit, no LLM billing]
7. Safety Gate calls           → bill: safety_input + safety_output tokens
8. select_tier() [ALLOW only]
9. LLM execution               → bill: input_tokens + output_tokens (actual)
10. [Speech if is_voice_input] → bill: audio_seconds / tts_characters
11. usage_meter records all fields
12. actual_cost() computed
13. user_charge = actual_cost * MARGIN
14. access_controller.deduct(user_id, user_charge)
15. usage_log written to Supabase
16. response delivered
```

---

## 11. SYNCHRONIZATION CONTRACTS

This document is synchronized with:

**models1.md** — model names, tier assignments, fallback order:
- FAST primary: llama-3.1-8b-instant ✓
- FAST fallback: gemma2-9b-it REMOVED (deprecated Aug 2025) ✓
- GENERAL primary: llama-3.3-70b-versatile ✓
- HEAVY primary: openai/gpt-oss-120b ✓
- llama-4-scout → HEAVY secondary → priced at $0.11/$0.34 ✓

**architecture.md** — EPK signals and execution paths:
- EPK signals: ALLOW / DENY / DEGRADED_MODE / HEAVY_REQUIRED ✓
- DEGRADED_MODE → Fast Tier only ✓
- HEAVY_REQUIRED → bypasses select_tier() ✓
- Safety Gate → both passes billed ✓

**decision_matrix.py** — thresholds must match this document exactly:
- `_FAST_CEILING = 0.0005` ✓
- `_GENERAL_CEILING = 0.003` ✓

**access_controller.py** — initial balance must match this document:
- `_DEFAULT_BALANCE_USD = 0.10` ✓

---

## 12. OPEN ITEMS (FUTURE)

- [ ] Compound/compound-mini token pricing not publicly listed — monitor Groq changelog
- [ ] allam-2-7b pricing not listed — treated as FAST equivalent until confirmed
- [ ] HF Inference Endpoints pricing if serverless quota exceeded
- [ ] Batch API discount (50%) — applicable when usage grows, not yet implemented
- [ ] Prompt caching discount (50% input) — applicable for high cache-hit workloads
- [ ] Speech billing not yet integrated into usage_meter (audio_seconds, tts_characters)
- [ ] Safety Gate token billing not yet integrated into usage_meter