# CEYONA — CANONICAL ARCHITECTURE
Version: 8.2 — Unified Agentic Path Edition
Status: Active Source of Truth
Supersedes: architecture.md (all previous versions)

This document defines **architectural rules and principles only**.
Implementation status, resolved issues, and open bugs are tracked in `audit.md`.

If runtime behavior contradicts this document — the runtime must be corrected.

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
- §11.x–12.x: предыдущие audit items (billing, epk, coordinator, safety gate)

**Open bugs (май 2026):** см. audit.md §13.
Критические: 13.1 (tool intents → сервис недоступен), 13.2 (потеря контекста).

Что НЕ верифицировано в этом аудите
Все слои верифицированы. Открытых пунктов нет.
ANTI-DRIFT PRINCIPLES
Architecture MUST scale through:
explicit contracts, bounded execution, centralized governance
deterministic orchestration, synchronized policy layers
Architecture MUST NOT scale through:
emergent behavior, hidden coupling, implicit orchestration
undocumented authority, runtime improvisation
FINAL SYSTEM PRINCIPLE
Ceyona is a governed orchestration system.
It is NOT a collection of autonomous AI behaviors.
The system succeeds only if:
authority remains explicit
execution remains deterministic
policy remains synchronized
runtime remains subordinate to architecture
retrieval remains grounded
orchestration remains bounded
Architecture governs the system. Runtime executes the system.

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

**Fly.io constraint:** `/health` timeout = 5s (fly.toml `[[http_service.checks]]`).
All sub-checks MUST complete with margin. Budget: 3s per check.

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