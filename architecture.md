# CEYONA — CANONICAL ARCHITECTURE
Version: 8.4 — Response-First Edition
Status: Active Source of Truth
Supersedes: architecture.md (all previous versions)

This document defines **architectural rules and principles only**.
Implementation status, resolved issues, and open bugs are tracked in `audit.md`.

If runtime behavior contradicts this document — the runtime must be corrected.

> **Первое правило при открытии этого файла:**
> Архитектура существует ради одного — чтобы бот отвечал на уровне
> Claude / ChatGPT. Если ответы сломаны — это приоритет №1 над любым
> архитектурным рефакторингом. Подробнее: `audit.md` → раздел
> «АБСОЛЮТНЫЙ ПРИОРИТЕТ — КАЧЕСТВО ОТВЕТОВ».

---

## 1. CORE PHILOSOPHY

Ceyona is a governed deterministic AI orchestration system.

It is NOT:
- an emergent multi-agent swarm
- a self-organizing reasoning ecosystem
- a recursive autonomous agent mesh
- a collection of independent LLM wrappers
- a prompt-driven improvisation engine

The system operates through:
- centralized policy governance
- deterministic execution lifecycles
- explicit authority ownership
- bounded orchestration
- controlled escalation
- synchronized model governance
- synchronized economic governance
- retrieval-grounded execution

The architecture prioritizes:
- correctness
- execution determinism
- factual stability
- scalable orchestration
- explicit contracts
- bounded cognition
- anti-drift resilience
- authority clarity

---

## 2. CONSTITUTIONAL RULES

### 2.1 Single Policy Authority Principle

Architectural policy layers define:
- execution policy
- routing semantics
- escalation policy
- truth policy
- model eligibility
- lifecycle governance
- orchestration permissions

Runtime execution nodes MUST NOT create policy.

### 2.2 Deterministic Execution Principle

All execution paths must be:
- explicit
- bounded
- observable
- reproducible

Forbidden:
- hidden execution chains
- recursive uncontrolled agent systems
- unbounded retry loops
- emergent orchestration behavior
- implicit execution mutation

### 2.3 No Hidden Authority

No handler, coordinator, verifier, retriever, synthesizer, helper, adapter,
or runtime node may silently:
- escalate tiers
- select models independently
- mutate routing
- redefine truth semantics
- alter orchestration topology
- redefine execution ownership

All authority must be explicit and declared.

### 2.4 Runtime Obeys Architecture

Implementation convenience never overrides architecture.
If runtime diverges from architecture:
- runtime must be corrected
- architecture must not be bypassed

### 2.5 Explicit Ownership Principle

Every execution subsystem MUST have:
- declared authority
- declared responsibilities
- declared invocation boundaries
- declared upstream dependencies
- declared downstream dependencies

Shared undeclared ownership is forbidden.

---

## 3. ARCHITECTURAL LAYERS

### Layer 1 — Constitutional Layer

`architecture.md`

Defines:
- execution philosophy
- authority graph
- orchestration model
- lifecycle semantics
- execution invariants
- ownership contracts
- system governance

Nothing may contradict this layer.

### Layer 2 — Policy Layers

**`models.md`** defines ONLY:
- approved models
- model capabilities
- role assignments
- tier eligibility
- deterministic fallback hierarchy

models.md MUST NOT:
- define orchestration
- define execution policy
- mutate routing
- override architecture

**`economic.md`** defines ONLY:
- actual model pricing (USD per 1M tokens)
- token estimation caps (for EPK cost estimation only)
- EPK thresholds (DENY / DEGRADE / HEAVY)
- decision_matrix thresholds (tier selection)
- balance and billing rules

Economic policy MAY:
- restrict execution
- deny escalation
- apply cost controls

Economic policy MUST NOT:
- redefine orchestration
- redefine authority
- mutate TruthMode
- bypass EPK

### Layer 3 — Retrieval Layer

Responsible for:
- external data acquisition
- retrieval normalization
- evidence packaging
- retrieval grounding

Retrieval MAY:
- fetch, normalize, rank, structure retrieved evidence
- score source credibility
- filter low-trust sources before LLM exposure

Retrieval MUST NOT:
- synthesize unsupported facts
- fabricate missing evidence
- mutate TruthMode
- bypass EPK
- silently suppress evidence

Retrieval is grounding. Retrieval is not synthesis.

### Layer 4 — Cognition Layer

Responsible for:
- decomposition
- reasoning structure
- constraint handling
- verification coordination
- correction coordination

Cognition MAY:
- structure reasoning
- organize analytical stages
- coordinate bounded correction

Cognition MUST NOT:
- own orchestration
- mutate execution topology
- self-authorize escalation
- bypass EPK
- redefine runtime authority

Cognition structures reasoning. Cognition does not govern execution.

### Layer 5 — Runtime Execution Layer

Contains:
- orchestrators, coordinators, handlers, retrievers
- agents, synthesizers, verification stages
- execution adapters

Runtime nodes execute. Runtime nodes do NOT define policy.

### Layer 6 — META Layer

META layers MAY:
- normalize output
- annotate quality
- repair presentation
- emit diagnostics
- stabilize formatting

META layers MUST NEVER:
- reroute execution
- escalate tiers
- redefine policy
- alter orchestration topology
- override authority

META exists to support execution clarity. META does not govern execution.

---

## 4. EXECUTION LIFECYCLE

Canonical execution lifecycle:

```
User Input
→ Safety Gate Pass 1  [llama-prompt-guard-2-22m — observability only, non-blocking]
→ Feature Extraction  [_classify_complexity: complexity, input_tokens estimation]
→ Multilingual Normalization  [allam-2-7b → Arabic | llama-3.3-70b → other non-Latin]
→ Safety Gate Pass 2  [gpt-oss-safeguard-20b — observability only, non-blocking]
→ Conversation History Load
→ Memory + Embedding Retrieval + Reranker
→ Web Search  [pre-EPK, balance-gated — skipped for zero-balance users]
→ EPK Policy Resolution  [SOLE policy authority — inside orchestrator]
→ analysis.py (pre-reasoning hints) [IMPLEMENTED ✅ — see §27]
→ Intent Classification
→ Execution Plan (via multi_agent_coordinator)
→ Model Resolution (via model_router)
→ Economic Validation (via cost_model → EPK)
→ Retrieval / Runtime Invocation
→ Verification Stage (safety_agent)
→ Response Synthesis (7-step pipeline)
→ META Normalization (correction + output_normalizer)
→ History Save
→ META Side-channel (reflection + memory_audit — async, non-blocking)
→ TTS Synthesis  [voice responses only — skipped for text input]
→ Output
```

### Порядок Safety Gate Pass 1 / Multilingual / Pass 2 — обоснование (Вариант А)

Pass 1 стоит ДО Feature Extraction и Multilingual: это быстрый pre-filter на сыром
input до любой обработки. Модель 22m — лёгкая, задержка минимальна.

Multilingual Normalization стоит МЕЖДУ Pass 1 и Pass 2.
Это архитектурно правильно по следующей причине:
Pass 2 использует gpt-oss-safeguard-20b — LLM-based классификатор. Он значительно
точнее работает с нормализованным текстом. Если пользователь пишет на арабском или
другом нелатинском языке, Pass 2 получает уже нормализованный вариант — риск
false-positive на экзотическом вводе снижается. Это также означает что у Pass 2 есть
полный контекст Feature Extraction (complexity, is_voice_input) как дополнительные сигналы.

Вариант Б (оба Gate до Multilingual) был бы симметричнее, но хуже по качеству
классификации Pass 2 на нелатинских языках. Вариант А выбран намеренно.

No hidden execution stages are allowed.
No runtime node may insert undeclared execution phases.

---

## 5. EPK — EXECUTION POLICY KERNEL

EPK is the sole policy authority of the system.

EPK owns:
- execution policy
- truth policy
- escalation permissions
- activation permissions
- routing permissions
- execution mode resolution
- orchestration eligibility
- safety_agent activation (post-reasoning blocking authority)

No runtime node may override EPK.

EPK reads ONLY: `estimated_cost` + `user_balance`
EPK does NOT access: memory, embeddings, LLM, agents, logs, metrics, model_router, pricing tables

EPK governs execution. Runtime executes execution.

---

## 6. ORCHESTRATOR

The orchestrator is execution-only.

The orchestrator MAY:
- execute DAGs
- schedule nodes
- invoke execution stages
- manage sequencing
- coordinate execution flow

The orchestrator MUST NOT:
- create policy
- reinterpret intent
- self-escalate
- choose models
- redefine TruthMode
- synthesize responses

The orchestrator executes orchestration. EPK governs orchestration.

---

## 7. REASONING ENGINE

The reasoning engine is strategy-oriented.

Reasoning MAY:
- decompose problems
- structure reasoning chains
- organize constraints
- propose analytical steps

Reasoning MUST NOT:
- activate Heavy Tier
- mutate routing
- select execution policy
- directly invoke models
- override EPK
- redefine orchestration

Reasoning generates strategy. Reasoning does not own execution.

---

## 8. MODEL GOVERNANCE

Model governance is split across two files with distinct responsibilities:

**`model_router.py`** — ROUTING AUTHORITY
- owns: tier → model mapping, API token limits, fallback models
- does NOT own: prices, cost estimation, billing

**`cost_model.py`** — ECONOMIC AUTHORITY
- owns: pricing tables (MODEL_RATES), cost estimation functions
- owns: MAX_OUTPUT_CAP — conservative estimation cap for EPK input ONLY
- does NOT own: model names, API limits, routing decisions

These are separate authorities. Neither imports from the other.
`MAX_OUTPUT_CAP` and `_MAX_TOKENS` serve different purposes and MUST NOT be equal:
- `MAX_OUTPUT_CAP`: conservative bound for cost estimation → EPK input
- `_MAX_TOKENS`: hard API limit passed to Groq → controls actual model output

Canonical model resolution flow:
```
cost_model.estimate_cost()     → estimated_cost (USD float)
    ↓
EPK.evaluate(cost, balance)    → ALLOW | DENY | DEGRADED | HEAVY_REQUIRED
    ↓
decision_matrix.select_tier()  → Tier (on ALLOW path only)
    ↓
model_router.route_model(tier) → model name string
    ↓
agents → groq_client           → API call with model + max_tokens
```

Runtime nodes MUST NOT self-select models.

---

## 9. ECONOMIC GOVERNANCE

Economic governance is subordinate to architecture.

Economics MAY:
- restrict expensive execution
- deny escalation
- enforce token budgets
- enforce throughput limits

Economics MUST NOT:
- redefine orchestration
- redefine reasoning
- mutate TruthMode
- bypass EPK
- silently downgrade execution quality

Heavy Tier activation requires:
- architectural eligibility
- policy eligibility
- economic eligibility

---

## 10. TRUTH MODES

TruthMode defines factual generation permissions.

**STRICT:**
- no unsupported factual generation
- no speculative completion
- no inferred geo data
- no invented schedules
- no fabricated availability
- no hallucinated retrieval output
- if retrieval incomplete → state uncertainty, state retrieval limitation
- absence of evidence is a valid terminal state

**HYBRID:**
- retrieved grounding
- bounded synthesis
- contextual completion
- generalized knowledge
- MUST still avoid fabricated claims

**STRICT and agentic intents — critical distinction:**
TruthMode.STRICT is assigned to WEATHER, MAPS, MAPS_POI, MAPS_ROUTE, SEARCH by `resolve_truth_mode()`.
This instructs the LLM: "do not fabricate — only use what your tools return."
This is correct and must remain.

However, the pre-execution truth gate in orchestrator.py is separate:
it checks `has_grounding = bool(retrieved_context) or bool(tool_output)` BEFORE compound executes.
Agentic intents are excluded from `_STRICT_INTENTS` in the orchestrator gate —
because compound_agent self-grounds by calling tools during its reasoning loop.
The STRICT instruction still reaches compound via `_build_messages()` — it just
does not trigger a pre-execution block that would fire unconditionally (compound
has not had a chance to run yet at gate time).

---

## 11. MAPS / GEO / SEARCH POLICY

STRICT-only intents: MAPS_ROUTE, MAPS_POI, SEARCH, AVAILABILITY, SCHEDULE, LOCATION_FACTS

The system MUST NEVER invent:
bus numbers, train schedules, hotel availability, pricing, routes,
geo facts, opening hours, transport lines.

All such data must originate from retrieval.
If retrieval fails → system returns retrieval limitation, NOT hallucination.

---

## 12. WEATHER POLICY

WEATHER intents are STRICT-grounded.
Weather responses MUST originate from validated weather retrieval.
If weather retrieval fails → system returns retrieval limitation, NOT fabricated conditions.

---

## 13. PROVIDER INTEGRATION RULES

Providers MAY: supply external data, provide retrieval evidence, provide infrastructure services.
Providers MUST NOT: alter orchestration, redefine TruthMode, mutate execution policy.

---

## 14. INFRASTRUCTURE CONFIGURATION RULES

Environment variables configure infrastructure access only.
Infrastructure configuration MUST NOT alter architecture or bypass policy governance.

---

## 15. VISION PIPELINE

`vision_handler.py` is a multimodal ingress adapter.

Role: preprocess multimodal input, extract structured signals, normalize image-derived context.

vision_handler MUST NOT:
- select models independently
- redefine routing
- bypass EPK
- own orchestration
- self-escalate execution

Correct lifecycle:
```
Input → Vision Preprocessing → Structured Extraction → EPK → Runtime Orchestration
```

Vision is ingress. Vision is not policy.
Vision handler is OUTSIDE the EPK DAG by design — it is a second ingress path.
Results feed back into the normal pipeline via update_handler with forced_intent.

**Token governance (май 2026):**
vision_handler makes a direct Groq call outside the EPK DAG.
`max_tokens` for this call MUST be read from `policy_registry.RUNTIME`:
```python
RUNTIME.tier_configs[Tier.FAST].max_output_tokens
```
Rationale: extraction is a bounded, low-complexity call → FAST tier limit applies.
Hardcoded `max_tokens` is a Single Policy Authority violation (§2.1) even outside EPK —
token limits have one source of truth: `policy_registry.RUNTIME`.
Fix applied: май 2026.

---

## 16. MULTI-AGENT COORDINATOR

`multi_agent_coordinator.py` is the agent execution fabric.

Coordinator MAY:
- sequence and dispatch agents (fast / deep / creative)
- manage execution order and dependencies
- run safety_agent where architecturally required
- run consensus_engine on ALLOW + use_consensus paths
- implement bounded self-correction (MATH verification loop, max 1 correction pass)
- aggregate execution metadata and agent outputs
- return CoordinationResult to orchestrator

Coordinator MUST NOT:
- synthesize final truth or own narrative assembly
- redefine response authority
- redefine routing or TruthMode
- become hidden orchestration
- select models (uses model_router via agents)
- make policy decisions

Coordinator is called by orchestrator ONLY.
Coordinator returns results to orchestrator ONLY.

---

## 17. VERIFICATION LIFECYCLE

Verification is a bounded execution stage.

Types: Constraint Verification, Factual Verification, Consistency Verification.

Canonical lifecycle:
```
Primary Reasoning → Verification → Optional Single Correction Pass → Final Synthesis
```

Maximum retries must remain bounded. Recursive self-correction ecosystems are forbidden.

---

## 18. MATH / CONSTRAINT REASONING

Canonical cognition lifecycle:
```
Intent Resolution → Task Decomposition → Primary Reasoning
→ Constraint Verification → Correction Pass (max 1) → Synthesis → META Normalization
```

Reasoning, verification, and synthesis are separate stages.
They MUST NEVER collapse into a single uncontrolled generation pass.

---

## 19. RESPONSE SYNTHESIZER

The response synthesizer owns final response authority.

Synthesizer owns: coherence, response assembly, multilingual consistency,
narrative stabilization, final user-facing output.

**Canonical 7-step pipeline (code-authoritative):**

```
1. assemble            — accept raw LLM output
2. normalize_telegram  — LaTeX→Unicode, strip Markdown (headers/bold/tables)
                         MUST run before structure/format (downstream sees clean text)
                         Owned by: synthesizer (inline utility, not a meta module)
3. structure           — intent-aware shaping (reserved, identity today)
4. format              — whitespace normalization
5. correction          — meta/correction.py: preamble/sign-off stripping
                         Owned by: meta/ | Executed by: synthesizer only
6. output_normalizer   — meta/output_normalizer.py: retrieval contamination cleanup
                         (context self-reference phrases, source tags, garbled URLs,
                          English term leaks in non-English responses)
                         Owned by: meta/ | Executed by: synthesizer only
7. finalize            — truncate to Telegram 4096-char limit
```

Steps 5 and 6 are owned by `meta/` but executed exclusively by synthesizer.
Their position is fixed. Reordering breaks the cleanup chain.
Both are excluded from the META side-channel DAG.

META layers support synthesis. META layers do NOT replace synthesis authority.
The synthesizer is the final response authority.

---

## 20. SOURCE CREDIBILITY

`source_credibility.py` has two call sites with distinct purposes:

**Call site A — external/search.py (primary)**:
```
Search provider results (Tavily / SerpAPI / SearXNG)
    → search.py._filter_results() → source_credibility.filter_results()
    BLOCKED tier → rejected entirely
    VERY_LOW tier → rejected
    LOW and above → passed (max 5 results)
→ LLM receives only trusted sources
```
Provider selection is internal to search.py (three-tier fallback chain — see §28).
source_credibility filters results regardless of which provider produced them.

**Call site B — retrieval/retrieval_engine.py (reserved)**:
```
pgvector similarity_search results → source_credibility.score_documents()
    Currently pass-through (MemoryRecord has no source_url yet)
    Will activate when MemoryRecord gains source_url field
→ cross_encoder.rerank()
```

source_credibility DOES actively block and filter — it is enforcement, not merely advisory.
It is NOT in the retrieval pipeline between query_preprocessor and reranker.
It is NOT called by retrieval_engine for web search results (search.py owns that path).

source_credibility MUST NOT:
- mutate retrieval artifacts beyond filtering
- become routing authority
- influence EPK
- redefine orchestration

---

## 21. SAFETY ACTIVATION

**Safety Layer (input observability — NON-BLOCKING):**
- meta-llama/llama-prompt-guard-2-22m (Pass 1, before Feature Extraction)
- meta-llama/llama-prompt-guard-2-86m + openai/gpt-oss-safeguard-20b (Pass 2, after Feature Extraction)
- both passes are non-blocking: log suspicious signals only, never DENY
- rationale: prompt-guard models produce unacceptable false-positive rates on Russian,
  Arabic, and short casual messages (e.g. "дешёвые отели в Воронеже", "В смысле?",
  "Ты шутишь?") — blocking at this layer causes full outage for legitimate users
- model unavailability → pass-through (observability degraded, execution continues)

**safety_agent (post-reasoning semantic validation — SOLE BLOCKING AUTHORITY):**
- runs inside coordinator, after primary reasoning
- is the only layer that can block execution on safety grounds
- activation rules:
  - ALLOW + use_consensus=True → runs before consensus
  - ALLOW + DEEP primary + no consensus → runs
  - HEAVY_REQUIRED → mandatory
  - DEGRADED_MODE → skipped
  - EMOTIONAL → skipped
  - default GENERAL (FAST primary, no fallback) → skipped

These two systems serve distinct roles and do NOT duplicate each other:
- Safety Layer → input signal logging (observability only)
- safety_agent → post-reasoning blocking authority (enforcement)

---

## 22. MUTEX RULES

Heavy Tier and Consensus are mutually exclusive:
- HEAVY_REQUIRED → Consensus SKIP
- ALLOW → Consensus ACTIVE

openai/gpt-oss-120b serves as:
- PRIMARY: Heavy Tier reasoning
- SECONDARY: Consensus arbiter (only when Heavy not active)
- NEVER active in both roles simultaneously

---

## 23. MULTILINGUAL EXECUTION

Language preservation is mandatory throughout the pipeline.
The system MUST preserve user language and avoid silent language drift.

Language normalization: synthesis + META normalization (output_normalizer leak maps).
Language selection MUST NOT emerge randomly from reasoning stages.

Multilingual normalization (before EPK, no policy influence):
- allam-2-7b → Arabic (one model, one call, three contexts: preprocessing / TTS / routing)
- llama-3.3-70b-versatile → all other languages

---

## 24. FALLBACK SEMANTICS

Fallback behavior MUST be deterministic.
Fallbacks MAY occur only through: EPK policy, model registry, economic eligibility.
Runtime nodes MUST NOT invent fallback chains or mutate fallback behavior silently.

---

## 25. ANTI-AGENT-AUTONOMY RULES

Agents MUST NEVER:
- recursively invoke uncontrolled agents
- self-create orchestration chains
- mutate execution topology
- self-authorize escalation
- create hidden execution paths

Agents are execution participants. Agents are not autonomous systems.

---

## 26. RUNTIME REGISTRY RULES

Every new runtime node MUST declare:
- authority, lifecycle role, invocation conditions
- upstream and downstream dependencies
- TruthMode behavior, model governance compliance

Undeclared runtime nodes are non-canonical.
No new module may silently introduce orchestration, create hidden routing,
own undeclared policy, duplicate responsibilities, or redefine existing ownership domains.

---


## 27. IMPLEMENTATION NOTES

Implementation status, resolved audit items, and open bugs are tracked in `audit.md`.
This document specifies rules — `audit.md` tracks what has been done and what is broken.

**Key architectural decisions recorded in audit.md:**
- §12.1: Unified agentic path — все tool intents через compound_agent (май 2026)
- §12.2: STRICT truth gate — agentic интенты исключены из pre-execution gate (май 2026)
- §14.1: Three-tier search fallback — Tavily → SerpAPI → SearXNG (май 2026)
- §15.1: healthcheck timeout fix — asyncio.wait_for + concurrent gather (май 2026)
- §13.2: conversation history context loss — закрыт tier-зависимыми бюджетами (май 2026)
- §11.x–12.x: предыдущие audit items (billing, epk, coordinator, safety gate)

**Open bugs (май 2026):** см. audit.md §13.
Критические: 13.1 (tool intents → сервис недоступен).

---

---

## 32. SPEECH-TO-TEXT (ASR)

`external/speech_to_text.py` is the voice ingress adapter.

**Activation:** `is_voice_input = True` only. Text messages never reach this module.

**Lifecycle position:**
```
Telegram voice message → download_telegram_voice() → transcribe()
    → transcript text → Safety Gate Pass 1 → Feature Extraction → normal pipeline
```

**Models (Groq Whisper API):**
- `whisper-large-v3` — primary (default, $0.111/hour)
- `whisper-large-v3-turbo` — fast fallback ($0.040/hour, slightly lower accuracy)

**Format handling:**
Telegram sends voice as OGG Opus. Groq Whisper does not accept OGG/Opus — the module converts to WAV via ffmpeg before upload. ffmpeg is guaranteed present (installed in Dockerfile).

**Billing:** `audio_seconds` in `UsageEntry` — separate from LLM tokens. Groq returns duration directly; falls back to size-based estimate (OGG Opus ≈ 2000 bytes/sec) when absent.

**Constraints:**
- Max file size: 25 MB (Groq limit) — returns `success=False` if exceeded
- Never raises — returns `TranscriptResult(success=False)` on all errors
- MUST NOT influence EPK, routing, or TruthMode
- MUST NOT be called for text input

---

## 33. TEXT-TO-SPEECH (TTS)

`external/text_to_speech.py` is the voice egress adapter.

**Activation:** `is_voice_input = True` AND synthesized response text is available. Runs after the full synthesis pipeline, before Event Store write.

**Lifecycle position:**
```
Response Synthesizer (7 steps complete) → synthesize() → OGG Opus bytes → Telegram sendVoice
```

**Models (Groq Orpheus API):**
- `canopylabs/orpheus-v1-english` — all non-Arabic languages ($22.00/1M chars)
- `canopylabs/orpheus-arabic-saudi` — Arabic only ($40.00/1M chars)

Language routing: `lang == "ar"` → Arabic model; everything else → English model.

**Audio pipeline:**
Orpheus returns WAV. Telegram `sendVoice` requires OGG Opus. Conversion: WAV → ffmpeg → OGG Opus (libopus, 32kbps, 48kHz mono). ffmpeg guaranteed present.

**Voice IDs (verified May 2026 — "default" returns HTTP 400):**
- English: `diana` (default), `autumn`, `hannah`, `austin`, `daniel`, `troy`
- Arabic: `noura` (default), `fahad`, `sultan`, `lulwa`, `aisha`

**Vocal directions** (`[cheerful]`, `[whisper]`): supported by English model only. NOT supported by Arabic model.

**Billing:** `tts_characters` in `UsageEntry` — per character, not per token. `char_count` is length of text passed to Orpheus (truncated to 5000 chars max per call).

**Arabic normalization:** allam-2-7b is called by `multilingual_preprocessor` before the pipeline reaches TTS. TTS receives already-normalized Arabic text and does not call allam itself.

**Constraints:**
- Never raises — returns `SynthesisResult(success=False)` on all errors
- Caller (`update_handler`) falls back to text-only response on TTS failure
- MUST NOT influence EPK, routing, or TruthMode

---

## 34. MULTILINGUAL PREPROCESSOR

`llm/multilingual_preprocessor.py` runs between Safety Gate Pass 2 and EPK.

**Role:** normalize non-Latin input text before intent classification and EPK. Does NOT translate — normalizes within the same language (punctuation, encoding artifacts, non-standard characters).

**Decision tree:**
```
Latin-dominant script (>90% Latin chars in first 240 chars)
    → passthrough, no LLM call

Arabic script (>15% Arabic Unicode chars)
    → allam-2-7b normalization

Other non-Latin (Cyrillic, CJK, Hangul, Devanagari, Georgian, Hebrew, Thai, Greek)
    → llama-3.3-70b-versatile normalization
```

**Script detection:** samples first 240 characters only. Unicode ranges checked per script family.

**Safety guards:**
- If normalized output loses original script (ratio drops from >10% to <5%) → revert to original
- If model returns empty string → revert to original
- Timeout: 20 seconds — on timeout, reverts to original; pipeline continues

**Constraints:**
- MUST NOT translate (translation is a cognition concern)
- MUST NOT influence EPK, routing, or TruthMode
- Never raises — always returns original text on failure

---

## 35. CONVERSATION HISTORY

`memory/conversation_history.py` is the per-user turn store (Supabase table `conversation_history`).

**Lifecycle position:** loaded at "Conversation History Load" step in §4 lifecycle, before EPK.

**Token budgets (tier is unknown at load time — EPK runs after retrieval):**

| Budget constant | Value | Approximate turns | When used |
|---|---|---|---|
| `FAST_HISTORY_BUDGET` | 2800 tokens | ~10–11 pairs | LOW complexity + short message |
| `GENERAL_HISTORY_BUDGET` | 3500 tokens | ~12–15 pairs | Everything else |

Caller selects budget using the same complexity heuristic as `orchestrator._estimate_tier` — before EPK runs.

**Fetch and trim:**
- SQL fetches up to 40 turns ordered by `created_at DESC` — upper bound only, not a hard cap
- Turns are reversed to chronological order, then trimmed oldest-first until within budget
- Token estimation: `len(content) // 4` (byte-approximate, conservative)

**Constraints:**
- Storage only — no semantic logic, no ranking, no policy
- MUST NOT influence EPK or routing
- On any DB error: returns `[]` (history unavailable → pipeline continues without context)

**Separation from `history_filter.py`:**
`conversation_history.py` loads and trims turns by token budget (I/O, per-request).
`history_filter.py` selects topically relevant turns from the already-loaded list (pure function, no I/O). They run in sequence: load → filter → prompt assembly.

---

## 36. SUPABASE STORE

`memory/supabase_store.py` is the raw vector memory storage layer (Supabase table `memory`).

**Role:** insert, fetch, and pgvector similarity-search `MemoryRecord` rows. No semantic logic. No ranking. Storage only.

**Key contracts:**
- `insert(MemoryEntry)` — stores content + embedding + metadata
- `fetch_by_user(user_id, limit, mem_type)` — recency-ordered fetch, no vector search
- `similarity_search(embedding, user_id, limit, threshold)` — calls `match_memory` Postgres RPC (pgvector cosine similarity)
- `delete_by_user(user_id)` — full wipe for user

**`MemoryRecord.source_url`** — provenance field for retrieval-originated records. Populated by `VectorMemory.remember()` via `metadata["source_url"]`. Used by `source_credibility` call site B (§20) when activated.

**`similarity` field:** cosine score returned by `match_memory` RPC. Default `1.0` for `fetch_by_user` calls (no vector search performed).

**Constraints:**
- MUST NOT perform ranking, scoring, or semantic interpretation
- MUST NOT influence EPK, routing, or TruthMode
- Never raises — returns `[]` / `False` on all errors

---

## 37. VECTOR MEMORY

`memory/vector_memory.py` is the semantic memory interface. Sits between callers and `SupabaseStore`.

**Role:** generate embeddings via HF client and delegate storage/retrieval to `SupabaseStore`. No interpretation beyond cosine similarity ranking returned by pgvector.

**Models:**
- `bge-large` — default (higher quality)
- `bge-small` — fast path (`use_fast=True`) — lower latency, lower cost

**Public API:**
- `remember(user_id, content, mem_type, importance, metadata, use_fast)` — embed + store
- `recall(user_id, query, limit, threshold, use_fast)` — embed query + similarity search
- `forget(user_id)` — delegates to `SupabaseStore.delete_by_user()`

**`source_url` propagation:** extracted from `metadata["source_url"]` and passed to `MemoryEntry` — preserves provenance through to `MemoryRecord`.

**Constraints:**
- No ranking beyond cosine similarity from pgvector
- MUST NOT interpret content, influence routing, or touch EPK
- Never raises — returns `False` / `[]` on embedding or storage errors

---

## 38. HISTORY FILTER

`llm/history_filter.py` selects topically relevant turns from the already-loaded conversation history before prompt assembly. Pure function — no I/O, no LLM calls.

**Lifecycle position:**
```
conversation_history.get_history() → [loaded turns]
    → select_relevant_history(user_message, history) → [filtered turns]
    → prompt_engine.build_messages() → messages list
```

**Selection logic:**
1. If `user_message` is a closure phrase ("спасибо", "ok thanks", "got it", etc.) → return `None` (no history injected)
2. Extract topic terms from `user_message` (words ≥3 chars, minus stopwords EN+RU)
3. Score each turn by overlap ratio: `|common terms| / min(|current|, |turn|)`
4. Turns below `_MIN_HISTORY_OVERLAP` (0.18) are excluded
5. Recent turns (last 2) get +0.05 recency bonus
6. Keep up to `_MAX_SELECTED_TURNS` (6), preserving original chronological order
7. Deduplicate by `(role, content)` key

**Separation from `memory_audit.py`:**
`history_filter.py` — runtime per-request selection (sync, no I/O, runs in critical path).
`memory_audit.py` — async diagnostic side-channel (runs after response, reads no data itself, zero execution authority). Different layer, different purpose, no overlap.

**Constraints:**
- MUST NOT call LLMs, read DB, or perform I/O of any kind
- MUST NOT influence EPK, routing, or TruthMode
- Never raises

---

## 39. PROMPT POLICY MODULE

`llm/prompt_policy.py` is a shared constants file for prompt-layer behavioral rules.

**Role:** centralizes reusable rule strings so that `prompt_engine.py` and any other prompt-assembling module imports from one place rather than duplicating literals.

**Contents:**
- `VARIATION_RULE` — plain text, answer-first, no markdown, varied openings
- `NO_CARRYOVER_RULE` — do not carry over facts from unrelated history turns
- `VERIFIED_FACTS_RULE` — prefer retrieved/verified facts over model memory
- `NO_CUTOFF_RULE` — do not invent freshness or availability without grounding
- `ANSWER_FIRST_RULE` — first word of response is part of the answer
- `NO_UNSOLICITED_CODE_RULE` — no code blocks unless explicitly requested
- `FORMAT_RULES` — no markdown tables, no headers
- `join_rules(*rules)` — helper to concatenate non-empty rule fragments

**Constraints:**
- Data file only — no execution, no policy authority, no routing
- MUST NOT import from runtime, EPK, agents, or any execution layer
- May be imported by any module that assembles prompts

---

## 40. COMPOUND AGENT

`agents/compound_agent.py` is the HEAVY tier synthesis executor.

**Role:** call Groq compound model as a plain synthesizer. It is NOT an autonomous agent — it does not self-search, does not call tools, does not own any policy.

**Why compound is used as a synthesizer, not an agent:**
Groq compound (`groq/compound`, `groq/compound-mini`) does not accept custom tool schemas via the tool-calling API — passing `tools=` causes HTTP 400 (verified May 2026, audit §13.1). All external retrieval (Tavily/SerpAPI/SearXNG/weather/maps) is performed by the orchestrator before compound is called. Retrieved context is injected into the user turn via `PromptContext` → `build_messages()`. Compound receives fully assembled messages and synthesizes the response.

**This preserves:**
- `source_credibility.py` filtering (§20) — retrieval is filtered before compound sees it
- `TruthMode.STRICT` invariant (§10) — grounding is already present in messages
- Retrieval pipeline ownership (§3) — compound does not bypass it

**Invocation:**
Called by `multi_agent_coordinator` (§16) on HEAVY tier path. Returns `AgentResult`. On any failure: `AgentResult(success=False)` — coordinator handles fallback.

**`max_tokens`:** read from `route_max_tokens(tier)` via `model_router` — never hardcoded.

**Constraints:**
- No tool schemas, no tool loop, no tool execution
- No policy authority, no model selection, no routing decisions
- MUST NOT self-search or self-escalate

---

## 41. INTENT EXAMPLES

`cognition/intent_examples.py` is a static data file containing few-shot classification examples.

**Role:** provides `INTENT_EXAMPLES: dict[str, list[str]]` — minimum 15 examples per intent class, multilingual (RU/EN/AR/UK/ES/FR/DE/IT and others). Used by `intent_engine.py` for few-shot prompting.

**Current intent classes include `recommendation` and `recall` as distinct categories (added May–June 2026):**
- `recommendation` — travel/food/hotel/city advice ("what should I eat in the Netherlands", "best area to stay in NYC"). Kept separate from `question` to route advice queries to HYBRID path rather than STRICT, and to reduce hallucination in broad travel prompts.
- `recall` — memory-style lookups ("what was that anime called", "what did we discuss about X"). Kept separate from `search` to avoid triggering web search for queries the bot can answer from conversation history.

**Constraints:**
- Static data only — no execution, no policy, no routing authority
- Adding/removing examples affects classification accuracy directly — changes must be validated against held-out test cases
- MUST NOT import from runtime, EPK, or any execution layer

---

## 42. MEDIA GROUP AGGREGATOR

`transport/telegram/media_group_aggregator.py` handles Telegram photo albums.

**Problem:** Telegram sends each photo in an album as a separate `Update` sharing the same `media_group_id`. Without aggregation, the bot processes them as independent single-image messages — 10 photos → 10 separate responses.

**Solution:** Redis-backed debounce. When the last photo's TTL sentinel expires, all buffered photos are flushed as a batch to a caller-supplied callback.

**Redis key layout per group:**
```
media_group:{group_id}       LIST    — serialized MediaGroupItem JSON
media_group:{group_id}:ttl   STRING  — debounce sentinel (3s EXPIRE)
media_group:{group_id}:lock  STRING  — flush-once guard (SETNX)
media_group:{group_id}:seen  SET     — deduplicated message_ids
```

**Flush triggers (whichever comes first):**
1. TTL expiry on `:ttl` key → Redis keyspace event → `_keyspace_listener` → `_flush()`
2. Group size reaches 10 (Telegram album limit) → immediate flush

**Atomicity:** two Lua scripts ensure correctness across multiple bot instances:
- `_LUA_ADD`: RPUSH + EXPIRE + dedup check — atomic per photo add
- `_LUA_FLUSH`: SETNX lock + LRANGE + DEL all keys — flush-once guarantee. Lock is deleted in the same script that acquires it (not after TTL) — prevents ghost-album bug when user sends a second album immediately after.

**Debounce TTL:** 3 seconds. Telegram delivers album photos within ~300ms on good connections, up to 2s on congested mobile. 3s provides margin without excessive latency.

**Lifecycle position:**
```
Telegram Update (photo with media_group_id)
    → update_handler → MediaGroupAggregator.add()
    → [3s debounce]
    → on_group_ready callback → all items → vision_handler (§15)
```

**Constraints:**
- All state in Redis — works correctly across multiple bot instances
- Idempotent: duplicate `message_id` arrivals are deduplicated by `_seen` SET
- Redis keyspace notifications must be enabled: `notify-keyspace-events Ex`
- MUST NOT influence EPK, routing, or TruthMode
- MUST NOT be called for non-album (single-photo) updates

---

## 43. OUTPUT NORMALIZER

`meta/output_normalizer.py` is step 6 of the response synthesizer pipeline (§19).

**Problem it solves:** retrieval brings multilingual/English snippets → LLM partially absorbs snippet language → response leaks English terms even when system prompt says "respond in Russian". This is retrieval contamination, not a model failure. Cleaning it at output is correct.

**Pipeline (deterministic, no LLM):**
```
1. Strip invisible chars     (zero-width, soft-hyphen — leak from OCR/retrieval)
2. Strip source tags         ("(источник 3)", "(source 2)" — internal retrieval labels)
3. Strip garbled URLs        (URLs with non-ASCII chars — SerpAPI artifact)
4. Apply language leak map   (English transport terms → native equivalents per lang)
5. Strip vision meta openers (when from_vision=True — "I see that...", "На изображении...")
6. Collapse whitespace       (double spaces left by removals)
```

**Language leak maps:** cover 30+ languages with common transport/UI terms (route, station, stop, departure, arrival, platform, traffic, drive time, distance). Applied case-insensitively with case restoration. Languages where leaks don't occur in production (`en`, `ja`, `zh`, `ko`, `ar`, `he`, etc.) are in `_SKIP_SUBSTITUTION` — no substitution applied.

**Adding entries to `_LEAK_MAPS`:** only terms confirmed in production logs (Sentry). Substitution must be semantically equivalent. No terms that appear in code, URLs, or proper nouns.

**Constraints:**
- MUST NOT translate or rewrite meaning — surface artifact cleanup only
- MUST NOT make routing decisions or influence EPK
- Never raises — caller keeps original text on exception
- Position is fixed at step 6 — must run after `correction.py` (step 5), before `finalize` (step 7)

---

## 28. SEARCH PROVIDER POLICY

`external/search.py` implements a three-tier fallback chain for web search:

```
1. Tavily   (primary)   — LLM-optimised structured results, 1000 req/mo free
                          API key: TAVILY_API_KEY
2. SerpAPI  (secondary) — reliable reserve, hotel pack support, 250 req/mo free
                          API key: SERPAPI_KEY
3. SearXNG  (tertiary)  — meta-search (Google/Bing/DDG aggregated), no rate limit
                          self-hosted via docker-compose.yml, URL: SEARXNG_URL
```

**Fallback rule:** each provider tried in order. First success wins.
Provider silently skipped if its key/URL is not configured in settings.
Caller (compound_agent) sees only `search_service.search()` — provider selection is internal.

**source_credibility** filters ALL provider results uniformly before LLM exposure (§20).

**Configuration authority:**
- `app/settings.py` declares `tavily_api_key`, `serpapi_key`, `searxng_url`
- `docker-compose.yml` runs SearXNG as a sidecar service on `ai-network`
- `SEARXNG_SECRET_KEY` MUST be set — without it SearXNG JSON API is unstable

**Provider MAY:** supply search results as grounding data.
**Provider MUST NOT:** alter orchestration, redefine TruthMode, mutate EPK.

---

## 29. HEALTHCHECK POLICY

`infra/healthcheck.py` is the sole implementation of `/health`.

**Note:** originally documented against Fly.io (5s timeout). Current deployment target is Oracle Cloud (OCI). Healthcheck budget constraints remain valid — concurrent checks within 3s each.

**Canonical implementation:**
```python
_REDIS_TIMEOUT    = 3.0   # asyncio.wait_for deadline
_SUPABASE_TIMEOUT = 3.0   # asyncio.wait_for deadline

# Checks run concurrently — total latency = max(redis, supabase), not sum
redis_ok, sb_ok = await asyncio.gather(
    check_redis(redis),      # asyncio.wait_for(redis.ping(), 3.0)
    check_supabase(supabase) # asyncio.wait_for(to_thread(query), 3.0)
)
```

**Supabase check MUST use `asyncio.to_thread`** — supabase-py client is synchronous.
Direct sync call in async context blocks the FastAPI event loop.
**Supabase check MUST use `asyncio.wait_for`** — to_thread alone has no deadline.

**Table queried:** `user_balances` (production table, always exists).
MUST NOT query non-existent or test-only tables.

healthcheck MUST NOT: influence EPK, alter routing, affect execution policy.

---

## 30. ANTI-DRIFT PRINCIPLES

Architecture MUST scale through:
- explicit contracts, bounded execution, centralized governance
- deterministic orchestration, synchronized policy layers

Architecture MUST NOT scale through:
- emergent behavior, hidden coupling, implicit orchestration
- undocumented authority, runtime improvisation

---

## 31. FINAL SYSTEM PRINCIPLE

Ceyona is a governed orchestration system.
It is NOT a collection of autonomous AI behaviors.

The system succeeds only if:
- authority remains explicit
- execution remains deterministic
- policy remains synchronized
- runtime remains subordinate to architecture
- retrieval remains grounded
- orchestration remains bounded

Architecture governs the system. Runtime executes the system.

healthcheck MUST NOT: influence EPK, alter routing, affect execution policy.