# MODELS — Single Source of Truth v6.4

## Token Caps (SSoT: `llm/model_router._MAX_TOKENS`)

| Tier | Max output tokens | Groq model |
|---|---|---|
| FAST | 1 024 | llama-3.1-8b-instant |
| GENERAL | 3 072 | llama-3.3-70b-versatile (primary) |
| HEAVY | 6 144 | openai/gpt-oss-120b (primary) |

`cost_model.py` and `policy_registry.py` read from `model_router` — never duplicate.

---

## Safety Layer (firewall — before EPK)

| Model | Pass | Unavailable |
|---|---|---|
| prompt-guard-2-22m | Pass 1 — before Feature Extraction | DENY |
| prompt-guard-2-86m + gpt-oss-safeguard-20b | Pass 2 — after Feature Extraction | DENY |

Distinct from `safety_agent` (post-reasoning semantic validator, agents layer).

---

## LLM Tiers (mocked by EPK signal — not logic layers)

### FAST — `ALLOW` / `DEGRADED_MODE` only
- **llama-3.1-8b-instant** — primary Fast Tier inference
- **allam-2-7b** — Arabic multilingual normalization (one call, three contexts: preprocessing / TTS pipeline / routing)

### GENERAL — `ALLOW` only
- **llama-3.3-70b-versatile** — primary reasoning + creative + non-Arabic multilingual normalization
- **qwen/qwen3-32b** — structured logic / formatting (`thinking: False` enforced)
- **openai/gpt-oss-20b** — constraint-aware general inference

### HEAVY — `HEAVY_REQUIRED` only
- **openai/gpt-oss-120b** — deep multi-step reasoning (primary); also Consensus arbiter when Heavy is not active (mutex)
- **llama-4-scout-17b-16e-instruct** — long-context transformation (512K ctx)

---

## Utility / Specialized Models (outside tier system)

| Model | Role | File | Notes |
|---|---|---|---|
| llama-3.1-8b-instant | Input shaping | `llm/heavy_input_shaper.py` | NOT Fast Tier — utility only |
| llama-3.1-8b-instant | Route/POI extraction | `external/web_tools.py` | Cheap LLM parser, no generation |
| llama-4-scout-17b-16e-instruct | Image content extraction | `transport/telegram/vision_handler.py` | **Specialized role** — outside EPK DAG, routes through `groq_client` |
| groq/compound-mini | Fast Agent | `agents/fast_agent.py` | Tool-use execution fabric |
| groq/compound | Deep Agent | `agents/deep_agent.py` | Multi-step tool-use |
| openai/gpt-oss-120b | Consensus arbiter | `agents/consensus_engine.py` | Mutex with Heavy Tier |

---

## HF Embeddings & Retrieval

| Model | Role |
|---|---|
| BAAI/bge-large-en-v1.5 | Primary embedding (vectors only) |
| BAAI/bge-small-en-v1.5 | Fast embedding fallback |
| BAAI/bge-reranker-large | Cross-encoder reranking (scores only) |

All access via `retrieval/retrieval_engine.py`.

---

## Specialized / Speech Layer

| Model | Role |
|---|---|
| whisper-large-v3 | Primary STT |
| whisper-large-v3-turbo | Fast STT |
| orpheus-v1-english | English TTS |
| orpheus-arabic-saudi | Arabic TTS |

Activated only when `is_voice_input = true`.

---

## EPK Outputs → Model Activation

```
ALLOW          → Fast + General + Agents + safety_agent + Consensus
DENY           → nothing
DEGRADED_MODE  → Fast only
HEAVY_REQUIRED → heavy_input_shaper + Heavy + safety_agent (no Consensus)
```

---

## Hard Rules

- `qwen/qwen3-32b` → `thinking: False` enforced at every call site
- `gpt-oss-120b` → Heavy primary **or** Consensus arbiter — never both simultaneously
- Safety models unavailable → `DENY` — no fallback to `ALLOW`
- Heavy Tier → activated by EPK signal only — no self-activation
- `llama-4-scout` in vision → Specialized role, not Heavy Tier EPK path