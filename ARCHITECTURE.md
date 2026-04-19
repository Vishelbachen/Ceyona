🧠 FINAL ARCHITECTURE (v1.3.2 — MODEL DECISION UNIFIED + RESPONSE REFACTOR)
🎯 GOAL
Production-ready AI backend with:
strict separation of concerns
single model decision brain (model_decision.py)
deterministic execution flow
full traceable lifecycle (trace_id)
unified response system (formatter + handler)
optional memory layer (session-based MVP)
centralized config (settings.py)
multi-model ecosystem (FAST / GENERAL / HEAVY / SAFETY)
prompt abstraction layer (PromptBuilder)
safe legacy fallback layer (controlled only inside decision system)
🧱 SYSTEM OVERVIEW (FINAL CLEAN MODEL)
🟢 ARCHITECTURE MODEL
API LAYER
↓
CORE LAYER (ORCHESTRATION)
↓
ENGINE LAYER (EXECUTION + MODEL + TRANSPORT)
↓
DOMAIN LAYER (CONTRACTS + LOGGING + RESPONSE)
↓
MEMORY LAYER (OPTIONAL STATE)
↓
CONFIG LAYER (SINGLE SOURCE OF TRUTH)
🔁 FULL REQUEST FLOW (PRODUCTION FLOW v1.3.2)
Telegram
→ webhook (API)
→ Orchestrator (CORE)
→ MemoryService (optional context injection)
→ Model Decision Layer (model_decision.py)
→ PromptBuilder
→ LLM Engine
→ Response Formatter
→ Response Handler
→ Telegram Transport
→ User
📦 ACTIVE FILES (FINAL CORE)
🚪 API LAYER
app/api/webhook.py
receive Telegram updates
validate payload
generate trace_id
build OrchestratorRequest
call orchestrator
pass result to ResponseHandler
❌ no business logic
❌ no model logic
❌ no formatting logic
🧠 CORE LAYER
app/core/orchestrator.py
RESPONSIBILITIES
central execution coordinator
memory integration (optional)
calls resolve_model() ONLY
prompt building via PromptBuilder
LLM execution
returns structured response
FLOW
✔ memory load
✔ model decision (UNIFIED BRAIN)
✔ prompt build
✔ LLM call
✔ memory save
✔ return response
❌ no legacy router usage
❌ no policy usage directly
❌ no classification logic
🧠 MODEL DECISION SYSTEM (NEW CORE BRAIN)
app/engine/model_decision.py ⭐ (SOURCE OF TRUTH)
RESPONSIBILITIES
Intent classification
Policy routing
Legacy fallback safety net
confidence-aware routing
final model resolution
PIPELINE
IntentClassifier
ModelPolicy
Legacy fallback (model_router)
Safety net (settings default)
RULE:
👉 ONLY orchestrator uses this file
🧠 INTENT SYSTEM
app/engine/intent_classifier.py
lightweight heuristic classifier
returns:
Python
IntentResult(intent, confidence)
app/engine/model_policy.py
ROLE
👉 PURE MAPPING ONLY:
intent → model group
NO LOGIC BEYOND:
safety
reasoning
creative
fast
❗ IMPORTANT RULE
✔ must NOT be used directly in orchestrator
✔ only used inside model_decision
🧯 LEGACY SAFETY SYSTEM
app/engine/model_router.py
ROLE
👉 EMERGENCY FALLBACK ONLY
RULES
NEVER primary system
ONLY used inside model_decision
never imported in orchestrator
Python
# DO NOT IMPORT OUTSIDE model_decision.py
# EMERGENCY FALLBACK ONLY
🧾 PROMPT SYSTEM
app/core/prompt_builder.py
ROLE
prompt formatting abstraction
context normalization
model input standardization
❌ no model logic
❌ no memory logic
⚙️ ENGINE LAYER
app/engine/llm.py
stateless inference
retry + timeout
trace logging
future Groq/OpenAI integration via settings
app/engine/telegram.py
pure transport layer
sends messages only
no logic
🧩 DOMAIN LAYER
app/contracts/message.py
UserMessage
OrchestratorRequest
app/contracts/response.py
SuccessResponse
JSON
{
  "success": true,
  "data": "...",
  "trace_id": "..."
}
ErrorResponse
JSON
{
  "success": false,
  "error": {
    "code": "...",
    "message": "...",
    "layer": "..."
  },
  "trace_id": "..."
}
app/core/logger.py
TRACE EVENTS
webhook_received
orchestrator_start
memory_loaded
model_selected
llm_request
llm_response
memory_saved
response_formatted
response_sent
app/core/errors.py
OrchestratorError
LLMError
RouterError
APIError
🧠 RESPONSE SYSTEM (FINAL SPLIT)
🧾 response_formatter.py
ROLE:
pure transformation
✔ Success/Error → user text
✔ edge-case handling
❌ no sending
📤 response_handler.py
ROLE:
delivery controller
✔ calls formatter
✔ sends via Telegram
✔ logs result
❌ no formatting logic
🧠 MEMORY LAYER (OPTIONAL)
session_store.py
in-memory storage
append messages
limit history
memory_service.py
builds context
orchestrator injection layer
safe fallback
⚙️ CONFIG LAYER (CRITICAL)
settings.py (SINGLE SOURCE OF TRUTH)
CONTAINS:
API keys
Telegram token
model groups:
FAST
GENERAL
HEAVY
SAFETY
external APIs
✔ replaces os.getenv everywhere
✔ controls full model ecosystem
📊 OBSERVABILITY (TRACE PIPELINE v1.3.2)
Plain text
webhook_received
→ orchestrator_start
→ memory_loaded
→ model_decision_start
→ intent_classified
→ model_selected
→ llm_request
→ llm_response
→ memory_saved
→ response_formatted
→ response_sent
🧠 CRITICAL ARCHITECTURE RULES (NEW)
🚨 MODEL SYSTEM RULE
❌ NO direct model_policy usage in orchestrator
❌ NO model_router usage anywhere except model_decision
✔ ONLY model_decision.resolve_model is valid entry point
🚨 SEPARATION RULE
Layer
Responsibility
model_decision
brain
model_policy
mapping
model_router
fallback
orchestrator
coordinator
💥 CURRENT STATUS (v1.3.2 STABLE CORE)
🟢 SYSTEM IS:
production-ready MVP
fully modular
single decision brain architecture
safe fallback system
clean layered separation
multi-model routing ready
prompt abstraction stable
response system fully split
traceable end-to-end
config centralized
⚠️ INTENTIONAL LIMITATIONS
no persistent memory (Redis next)
no agent reasoning layer
no streaming
no tool execution system
🚀 NEXT EVOLUTION PATH
🔜 model scoring system (weighted routing)
🔜 cost-aware model selection
🔜 latency-aware routing
🔜 user-tier model allocation
🔜 agent reasoning layer (v2 architecture)
🧱 SYSTEM CLASS
Production AI backend evolving toward agentic architecture:
MVP → Stable Core → Decision Brain System → Agent-ready AI Platform