# CEYONA — CANONICAL ARCHITECTURE
Version: 8.1 — Safety Gate Observability Edition
Status: Active Source of Truth
Supersedes: architecture.md (all previous versions)

This document is the ONLY canonical architectural authority of the system.
All previous architectural variants are deprecated and non-authoritative.
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
SerpAPI results → search.py._filter_results() → source_credibility.filter_results()
    BLOCKED tier → rejected entirely
    VERY_LOW tier → rejected
    LOW and above → passed (max 5 results)
→ LLM receives only trusted sources
```

**Call site B — retrieval/retrieval_engine.py (reserved)**:
```
pgvector similarity_search results → source_credibility.score_documents()
    Currently pass-through (MemoryRecord has no source_url yet)
    Will activate when MemoryRecord gains source_url field
→ cross_encoder.rerank()
```

source_credibility DOES actively block and filter — it is enforcement, not merely advisory.
It is NOT in the retrieval pipeline between query_preprocessor and reranker.
It is NOT called by retrieval_engine for SerpAPI results.

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

## 27. IMPLEMENTATION STATUS (May 2026)

This section tracks known gaps between architecture specification and runtime implementation.
All gaps are intentional architectural decisions, not defects.

### Safety Gate (§21)
**Status: OBSERVABILITY LAYER — NON-BLOCKING (May 2026)**
`security/safety_gate.py` — Pass 1 (`llama-prompt-guard-2-22m`) and Pass 2
(`gpt-oss-safeguard-20b`) are integrated into `update_handler.py`.
Both passes are non-blocking: suspicious signals are logged, execution always continues.

**Rationale for non-blocking design:**
prompt-guard models and gpt-oss-safeguard-20b produce unacceptable false-positive rates
on Russian, Arabic, and short casual text — blocking at input level causes full outage
for legitimate users with no meaningful safety gain over what safety_agent provides.

**Sole blocking authority: `safety_agent`** (post-reasoning, semantic, full context).
Safety Gate is intentionally observability-only. This is not a defect — it is the
correct architectural decision given the operational false-positive evidence.

### analysis.py — pre-reasoning hints (§4 Execution Lifecycle, §11 META Layer)
**Status: IMPLEMENTED (May 2026)**
`meta/analysis.py` — полностью подключён в pipeline. ✅

**Реализованный flow (Вариант А — строго по архитектуре §4):**
```
update_handler.py
  → meta/analysis.analyse(text, lightweight=False)   [после Pass 2, до orchestrator]
  → AnalysisReport → OrchestratorRequest.analysis_report
  → orchestrator.run()
  → intent_engine.classify(..., analysis_hints=analysis_report)
```

**Что делает analysis_hints в intent_engine.classify():**
- `HAS_MATH` с confidence ≥ 0.80 → немедленный return MATH (пропускает LLM pre-check)
- `IS_SHORT` или `IS_MULTILINGUAL` → повышает effective_min до max(текущий, 0.72)
- `HAS_CODE_BLOCK` → снижает effective_min до min(текущий, 0.50)
- Все hints non-binding — intent_engine может игнорировать их

**Позиция в lifecycle:**
После Safety Gate Pass 2 (нормализованный текст), перед Conversation History и Orchestrator.
lightweight=False передаётся всегда из update_handler — EPK-сигнал (ALLOW/DEGRADED)
недоступен до orchestrator, поэтому full-mode используется как safe default.

**Свойства модуля (верифицированы аудитом):**
Pure function, no I/O, no async, never raises. Zero execution authority.
Все regex-паттерны скомпилированы один раз при импорте — latency < 1ms.
Multilingual Normalization (§23)
Status: IMPLEMENTED
llm/multilingual_preprocessor.py — Arabic via allam-2-7b,
all other non-Latin via llama-3.3-70b-versatile, Latin-dominant → passthrough.
Integrated into update_handler.py after Safety Gate Pass 2. ✅
Agent Layer — Compound Models (§6, §16)
Status: IMPLEMENTED ✅ (May 2026)
groq/compound and groq/compound-mini are wired as the primary execution path
for tool-use intents (SEARCH, WEATHER, MAPS, MAPS_POI, MAPS_ROUTE).

Implementation:
  llm/groq_client.py          — ToolCall, ToolCallResponse dataclasses;
                                 GroqClient.complete_with_tools() method.
  agents/compound_agent.py    — tool execution loop (bounded: _MAX_TOOL_ROUNDS=3);
                                 run_fast() → groq/compound-mini (Tier.FAST);
                                 run_deep() → groq/compound (Tier.GENERAL).
  multi_agent_coordinator.py  — AgentType.COMPOUND_FAST / COMPOUND_DEEP;
                                 tool intents route to compound, fallback=AgentType.DEEP.

Supported tools: web_search, get_weather, geocode.
Tool execution delegates to: search_service, weather_service, maps_service (existing singletons).
Fallback: AgentType.DEEP (llama-3.3-70b-versatile) — activated if compound fails.
No policy authority. No model selection. Returns AgentResult — same contract as fast/deep agents.

Execution ownership split (May 2026 — закрывает conflict_ownership gap):
  _TOOL_INTENTS (WEATHER, MAPS, MAPS_ROUTE) → orchestrator tool-only path.
    Reason: format_current / format_geocode / format_route return final text — no LLM synthesis needed.
    These never reach compound_agent.
  _AGENTIC_INTENTS (SEARCH, MAPS_POI) → compound_agent via agentic path.
    Reason: require end-to-end LLM reasoning over retrieved data.
    SEARCH: compound decides what to search and how to present results.
    MAPS_POI: compound reasons about which POIs are relevant and presents them.
    Orchestrator _NO_SEARCH_INTENTS prevents pre-EPK web search for these —
    compound owns tool execution itself.

Billing gap — CLOSED (May 2026):
  tool_calls: int now flows through the complete billing chain without gaps:
    compound_agent._run_compound() counts each tool call → AgentResult.tool_calls
    → CoordinationResult.tool_calls (coordinator aggregates)
    → OrchestratorResult.tool_calls (all three execution paths: _run_allow, _run_degraded, _run_heavy)
    → webhook.py passes tool_calls to UsageEntry.tool_calls
    → usage_meter.record() writes to Supabase usage_log.
  UsageEntry.tool_calls field and Supabase column were already declared — no migration needed.
Speech Layer (§12)
Status: IMPLEMENTED ✅ (ASR + TTS + Billing, май 2026)
external/speech_to_text.py — Whisper ASR via Groq API. ✅
external/text_to_speech.py — Orpheus TTS via Groq API. ✅
transport/telegram/message_router.py — extract_voice() / has_voice(). ✅
transport/telegram/update_handler.py — voice path: download → ASR → Safety Gate Pass 1
(observability only, non-blocking) → pipeline. TTS on response when is_voice_input = True. ✅
audio_seconds and tts_characters wired to OrchestratorResult and UsageEntry (май 2026). ✅
update_handler.py: _asr_audio_seconds and _tts_characters set on result via dataclasses.replace()
before return — webhook.py receives real values, not zeros.
OrchestratorResult.tts_audio_bytes + Telegram sendVoice
Status: IMPLEMENTED (May 2026)
OrchestratorResult now declares tts_audio_bytes: bytes = b"". ✅
update_handler.py sets field via `dataclasses.replace(result, tts_audio_bytes=...) after TTS synthesis. ✅
webhook.py now implements _send_voice() and checks tts_audio_bytes before sending:
non-empty → sendVoice (Telegram voice message)
sendVoice failure → silent fallback to _send_message() (text)
empty → text only ✅
Speech Billing
Status: IMPLEMENTED ✅ (май 2026)
UsageEntry fields audio_seconds, tts_characters, tool_calls declared. ✅
Supabase migration applied: audio_seconds FLOAT8, tts_characters BIGINT, tool_calls BIGINT. ✅
update_handler.py: _asr_audio_seconds и _tts_characters wire на OrchestratorResult перед return. ✅
webhook.py: audio_seconds и tts_characters передаются в UsageEntry. ✅
usage_meter.record(): пишет extended fields когда non-zero; PGRST204 fallback оставлен
как защитный слой на случай schema cache miss — не удалять.
policy_registry.py
Status: IMPLEMENTED — LIVE (May 2026)
Previously dead code — nobody imported it. Now the true single source of truth:
execution_policy_kernel.py reads RUNTIME.epk.* for all EPK thresholds ✅
model_router.py reads RUNTIME.tier_configs[tier].max_output_tokens for _MAX_TOKENS ✅
access_controller.py reads RUNTIME.default_balance_usd for _DEFAULT_BALANCE_USD ✅
To change any threshold or default balance — edit policy_registry.py only.
All three modules pick up the change automatically. No more scattered hardcoded values.
Test Suite (§11.2)
Status: IMPLEMENTED ✅ (May 2026)
tests/ — полный unit test suite. Все тесты pure unit, без внешних вызовов (Supabase, Redis, Groq, HF — всё мокируется на границе).
Файлы: test_epk.py, test_analysis.py, test_usage_meter.py, test_safety_gate.py,
test_intent_engine_hints.py, test_orchestrator_web_search.py, conftest.py
CI: .github/workflows/ci.yml — pytest + ruff + critical import checks на каждый push/PR в main.
LAYER FREEZE STATUS (May 2026)
Статусы проставлены по результатам полного аудита кода (май 2026).
Все файлы каждого слоя прочитаны и верифицированы против architecture.md v8.0.
Определения статусов
Sealed √ — authority boundary слоя (EPK, policy, kernel).
Изменения только через полное архитектурное ревью с обновлением architecture.md.
Никаких правок "по удобству" или "для быстрого фикса".
Frozen √ — логика и интерфейсы стабильны. Слой соответствует архитектуре.
Изменения допустимы только через явное архитектурное решение с обновлением §27.
Pending Fix — известная проблема, слой не готов к заморозке.
После фикса и верификации → переводится в Frozen √.
core/kernel/ — 🔒 Sealed √
Файлы: policy_registry.py, execution_policy_kernel.py, decision_matrix.py, cost_model.py
Верифицировано: май 2026.
Все threshold'ы читаются из policy_registry.RUNTIME — нет хардкода.
EPK порядок (DENY→HEAVY→DEGRADE→ALLOW) строго соответствует §5.
MODEL_RATES синхронизированы с economic.md v5.1.
MAX_OUTPUT_CAP ≠ _MAX_TOKENS — разные authority, правильно (§8).
security/ — ✅ Frozen √
Файлы: safety_gate.py, auth.py, rate_limiter.py, origin_guard.py, encryption.py
Верифицировано: май 2026.
Safety Gate: оба прохода non-blocking (observability only) — см. §21 и §27 Safety Gate.
Решение принято намеренно: false-positive rate на русском/арабском/коротком тексте
делал blocking-режим неприемлемым для production. Единственный blocking authority — safety_agent.
core/execution/ — ✅ Frozen √
Файлы: orchestrator.py
Верифицировано: май 2026.
Не создаёт policy. _TOOL_INTENTS и _STRICT_INTENTS корректны.
_TOOL_INTENTS: {WEATHER, MAPS, MAPS_ROUTE} — детерминированные форматтеры, tool-only path.
  SEARCH и MAPS_POI намеренно исключены — идут на compound_agent через agentic path (май 2026).
_structured_search path удалён — больше не нужен (SEARCH теперь compound ownership).
DENY/HEAVY/DEGRADED/ALLOW пути чистые, без скрытых ветвлений.
tool_calls из CoordinationResult прокидывается в OrchestratorResult во всех трёх путях.
llm/ — ✅ Frozen √
Файлы: model_router.py, groq_client.py, fallback_handler.py, heavy_input_shaper.py,
multilingual_preprocessor.py, prompt_engine.py, hf_client.py
Верифицировано: май 2026.
_MAX_TOKENS читается из policy_registry.RUNTIME.
HF endpoint обновлён на router.huggingface.co.
413-обработка с truncation retry в fallback_handler.
qwen thinking=False применяется через requires_thinking_disabled().
agents/ — ✅ Frozen √
Файлы: fast_agent.py, deep_agent.py, creative_agent.py, safety_agent.py, consensus_engine.py,
compound_agent.py
Верифицировано: май 2026.
fast_agent и deep_agent: complete_with_fallback(Tier.FAST/GENERAL) — plain text synthesis.
compound_agent: tool-use execution loop (IMPLEMENTED ✅, май 2026).
  run_fast() → groq/compound-mini, run_deep() → groq/compound.
  Bounded: _MAX_TOOL_ROUNDS=3. Fallback: AgentType.DEEP.
  Поддерживаемые tools: web_search, get_weather, geocode.
  AgentResult.tool_calls: int — billing counter, flows to CoordinationResult → OrchestratorResult → UsageEntry.
  Billing gap закрыт (май 2026) — tool_calls chain замкнут без разрывов.
cognition/ — ✅ Frozen √
Файлы: intent_engine.py, reasoning_engine.py, multi_agent_coordinator.py,
response_synthesizer.py
Верифицировано: май 2026.
MATH self-correction: max 1 pass — bounded.
safety_agent activation rules строго по §21.
7-step synthesizer pipeline — порядок фиксирован, нарушение ломает cleanup chain.
meta/ — ✅ Frozen √ (кроме analysis.py — см. ниже)
Файлы: analysis.py, correction.py, output_normalizer.py, reflection.py, memory_audit.py
Верифицировано: май 2026.
Все модули (кроме analysis.py): pure functions, no I/O, never raise.
correction и output_normalizer вызываются исключительно через synthesizer (steps 5, 6).
Не имеют execution authority — только observability и cleanup.
analysis.py: IMPLEMENTED ✅ — вызывается в update_handler.py до orchestrator, результат передаётся в OrchestratorRequest.analysis_report (см. §27).
payments/ — ✅ Frozen √
Файлы: usage_meter.py, access_controller.py, pricing_engine.py, ton_client.py, wallet_manager.py
Верифицировано: май 2026.
usage_meter: PGRST204 fallback сохранён как защитный слой (schema cache miss protection).
Speech Billing полностью закрыт (май 2026) — см. §27.
_DEFAULT_BALANCE_USD читается из policy_registry.RUNTIME.
retrieval/ — ✅ Frozen √
Файлы: retrieval_engine.py, source_credibility.py, dense/, sparse/, reranker/, cache/
Верифицировано: май 2026.
pgvector similarity_search теперь реально вызывается (BUG FIX — ранее candidates=[]).
source_credibility активно блокирует BLOCKED/VERY_LOW — не advisory.
external/ — ✅ Frozen √
Файлы: search.py, maps.py, weather.py, web_tools.py, speech_to_text.py, text_to_speech.py
Верифицировано: май 2026.
search.py: URL sanitization + _SUSPICIOUS_PATTERNS + structured header для tool-only пути.
maps.py: _RHETORICAL_PATTERNS фильтр, LLM-based POI extraction, country bias.
Speech billing: IMPLEMENTED ✅ (май 2026, см. §27).
transport/telegram/ — ✅ Frozen √
Файлы: webhook.py, update_handler.py, vision_handler.py, message_router.py,
auth_middleware.py, callback_handler.py
Верифицировано: май 2026.
update_handler lifecycle строго соответствует §4 execution lifecycle.
_send_voice() реализован, fallback на text при ошибке sendVoice.
vision_handler.py: полностью верифицирован (май 2026).
  Соответствует §15: не выбирает модели, не обходит EPK, forced_intent → update_handler.
  max_tokens читается из policy_registry.RUNTIME[Tier.FAST] (фикс §15, май 2026).
  classifier fallback при ошибке → needs_pipeline=True (безопасный дефолт).
memory/ — ✅ Frozen √
Файлы: conversation_history.py, supabase_store.py, vector_memory.py
Верифицировано: май 2026.
_MAX_HISTORY_TOKENS=1200 (уменьшен с 2000 — исправлены 413 на llama-3.1-8b-instant).
_trim_history_to_budget: drop oldest, keep newest.
supabase_store.py: MemoryRecord получил source_url: str | None = None (§5.3, май 2026).
  fetch_by_user() и similarity_search() маппят source_url из БД.
  Supabase migration: ALTER TABLE memory ADD COLUMN source_url text DEFAULT NULL.
context/, contracts/, i18n/, observability/, events/, infra/ — ✅ Frozen √
Верифицировано: май 2026.
resolve_truth_mode: STRICT/HYBRID/GENERATIVE маппинг корректен.
shared_types: Tier, Complexity, EPKDecision, TruthMode — все enum'ы правильные.
events/: parallel с memory write, независимые failure domains.
i18n/strings.py: data-only файл (1322 строк локализаций), архитектурной логики нет.
infra/: полностью верифицирован (май 2026).
  env_validator.py: все обязательные env vars декларированы явно, sys.exit(1) при отсутствии.
  healthcheck.py: redis + supabase ping, metrics_snapshot() — живой импорт, не мёртвый.
  config_loader.py: инфраструктура, не архитектурная логика.
### observability/tracing.py — Log-based Tracing Contract (May 2026)
**Status: IMPLEMENTED ✅**

Tracing = structured JSON spans via stdlib logging. No OTLP collector required.

**Design:**
- `with trace(name, **tags)` — stable public contract, backend-agnostic
- `trace_id` propagated via `contextvars` — asyncio-safe, callers never manage it
- Nested spans inherit `trace_id`, record `parent_id`
- `status: ok | error` set automatically on exception
- Span output: `{"event": "span", "trace_id": ..., "span_id": ..., "parent_id": ..., "elapsed_ms": ..., "status": ...}`
- `current_trace_id()` — public API for cross-module correlation

**Dependencies:** `opentelemetry-api` and `opentelemetry-sdk` removed from
`pyproject.toml` — were dead (declared, never imported).

**OTLP migration path:** replace backend of `tracing.py` only.
All call sites (`webhook.py`, `orchestrator.py`) remain unchanged.
Collector (Jaeger, Grafana Tempo, Honeycomb) is a separate infrastructure task.

### observability/metrics.py — Metrics Contract (May 2026)
**Status: IMPLEMENTED ✅**
`observability/metrics.py` — in-memory counters and gauges, exported via `GET /metrics`.

**Canonical design (закрывает audit §7.3 / §10.1):**
- `increment()` and `gauge()` are pure in-memory operations — no side effects, no I/O.
- `snapshot()` is the sole export boundary, consumed by `GET /metrics` (app/main.py).
- Metrics are per-process and reset on restart. No persistence layer is used by design.
- Data is NOT aggregated across workers or instances (single-instance deployment).
- Dead import `snapshot as metrics_snapshot` removed from `webhook.py`.

**Explicit contract:**
Metrics = ephemeral signal layer (observability), not state layer.
MUST NOT participate in execution (no side effects in increment/gauge).
Prometheus/StatsD export = separate future task — external adapter only,
no changes to metrics.py required when that time comes.

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