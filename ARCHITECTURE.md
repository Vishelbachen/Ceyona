# 🧠 PROJECT ARCHITECTURE (v1.3 — STABLE CORE SIMPLIFIED + MEMORY INTEGRATED)

## 🎯 GOAL
Minimal but production-capable AI backend with:
- strict separation of concerns
- deterministic execution flow
- full traceable request lifecycle (trace_id pipeline)
- unified response + error handling
- memory system integrated (session-based, optional)
- clean upgrade path to Agent Layer

---

# 🧱 SYSTEM OVERVIEW (SIMPLIFIED)

## 🟢 ARCHITECTURE MODEL

API LAYER ↓ CORE LAYER (ORCHESTRATION) ↓ ENGINE LAYER (EXECUTION + TRANSPORT) ↓ DOMAIN LAYER (CONTRACTS + LOGGING + RESPONSE) ↓ MEMORY LAYER (SESSION STATE - OPTIONAL)

---

# 🔁 FULL REQUEST FLOW (CURRENT PRODUCTION FLOW)
Telegram → webhook (API) → Orchestrator (CORE) → MemoryService (optional context injection) → Model Router (ENGINE) → LLM (ENGINE) → Response Handler (DOMAIN) → Telegram Sender (ENGINE) → User

---

# 📦 ACTIVE FILES (CURRENT PRODUCTION STAGE — STABLE CORE++)

---

# 🚪 API LAYER

## main.py
FastAPI entry point:
- application bootstrap
- route registration
- lifecycle management

---

## app/api/webhook.py
Telegram webhook handler (INBOUND layer)

Responsibilities:
- receives external Telegram updates
- validates and parses payload
- generates trace_id
- builds OrchestratorRequest
- calls orchestrator (handle_request)
- forwards result to ResponseHandler
- does NOT format responses
- does NOT contain business logic

---

# 🧠 CORE LAYER

## app/core/orchestrator.py
Application flow controller (CORE layer)

Responsibilities:
- central coordination point
- receives OrchestratorRequest
- logs full lifecycle
- model selection coordination
- LLM execution orchestration
- memory integration (optional)
- returns structured responses:
  - SuccessResponse
  - ErrorResponse

Lifecycle steps:
- start
- memory load (if enabled)
- model selection
- prompt building
- LLM call
- memory save (post-response)
- return response

No transport awareness.

---

# ⚙️ ENGINE LAYER

## app/engine/model_router.py
Model selection layer:
- routing logic (fast / general / heavy / safety)
- selects model from available pool
- no execution logic

---

## app/engine/llm.py
LLM execution layer:
- model inference execution
- retry logic (bounded)
- timeout handling
- structured logging with trace_id
- returns LLMResponse
- stateless execution only

---

## app/engine/telegram.py
Telegram transport adapter:
- sends messages via Telegram Bot API
- pure HTTP client
- no business logic
- used ONLY by response layer

---

# 🧩 DOMAIN LAYER

---

## app/contracts/message.py
Data contract layer:
- UserMessage
- OrchestratorRequest

Ensures:
- strict schema enforcement
- trace_id propagation
- deterministic structure

---

## app/contracts/response.py
Response contract layer:

### SuccessResponse
```json
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
app/contracts/context.py
Context contract layer (NEW / RESERVED):
defines shared context structure
memory-ready schema for future agent expansion
used for prompt enrichment
app/core/errors.py
Unified error schema layer:
AppError base class
OrchestratorError
LLMError
Standard format:
JSON
{
  "error": {
    "code": "...",
    "message": "...",
    "layer": "...",
    "trace_id": "..."
  }
}
app/core/logger.py
Structured logging system:
JSON logs
trace_id tracking
event-based lifecycle logging
Events:
webhook_received
orchestrator_start
memory_loaded
model_selected
llm_request
llm_response
memory_saved
response_sent
error events
app/core/response_handler.py
Response abstraction + formatting layer (DOMAIN OUTPUT)
Responsibilities:
normalize SuccessResponse / ErrorResponse
convert system output → user text
send via telegram engine
guarantee delivery logging
preserve trace_id consistency
Internal methods:
handle(response, chat_id)
send_text(text, chat_id, trace_id)
🧠 MEMORY LAYER (NEWLY IMPLEMENTED)
app/memory/session_store.py
Session storage layer:
per-user message history
append user/assistant messages
lightweight in-memory state
fast access
no external DB dependency yet
app/memory/memory_service.py
Memory orchestration layer:
Responsibilities:
build context from session history
inject context into orchestrator flow
store messages after LLM response
isolates memory logic from CORE layer
Integration:
used inside orchestrator (optional dependency)
system fully works without it
safe fallback behavior enabled
🧠 MODEL SYSTEM (DO NOT REMOVE)
⚡ FAST MODELS
groq/compound-mini
llama-3.1-8b-instant
🧠 GENERAL MODELS
llama-3.3-70b-versatile
qwen/qwen3-32b
openai/gpt-oss-20b
🧠 HEAVY MODELS
openai/gpt-oss-120b
meta-llama/llama-4-scout-17b-16e-instruct
🛡 SAFETY MODELS
openai/gpt-oss-safeguard-20b
meta-llama/llama-prompt-guard-2-22m
meta-llama/llama-prompt-guard-2-86m
🎙 AUDIO MODELS
whisper-large-v3
whisper-large-v3-turbo
🎭 EXPERIMENTAL MODELS
allam-2-7b
groq/compound
canopylabs/orpheus-v1-english
canopylabs/orpheus-arabic-saudi
🔐 ENVIRONMENT VARIABLES (CRITICAL — DO NOT MODIFY STRUCTURE)
AI / LLM
GROQ_API_KEY
Telegram
BOT_TOKEN
Security
JWT_SECRET
ENCRYPTION_KEY
Database (reserved future)
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
External APIs
OPENWEATHER_API_KEY
MAPBOX_TOKEN
SERPAPI_KEY
BREVO_API_KEY
Payments (future)
TON_WALLET
Deployment
WEBHOOK_URL
🚫 SECURITY RULES
no secrets in repository
env-only configuration
no external calls outside engine layer
strict separation of transport vs business logic
📊 OBSERVABILITY
Trace lifecycle:

webhook_received
→ orchestrator_start
→ memory_loaded
→ model_selected
→ llm_request
→ llm_response
→ memory_saved
→ response_sent
``` id="trace_1"

---

# 💥 CURRENT STATUS (STABLE CORE v1.3)

System is:
- fully working end-to-end
- memory-enabled (optional)
- fully traceable pipeline
- modular but simplified architecture
- production-safe
- ready for agent evolution

---

# ⚠️ CURRENT LIMITATIONS

- no persistent memory (session-only)
- no agent reasoning layer
- no streaming responses
- no structured UI response system (v2 planned)
- no tool execution layer

---

# 🚀 NEXT EVOLUTION ROADMAP

## 🔜 1. MEMORY PERSISTENCE LAYER
- Redis / DB storage
- long-term memory
- cross-session continuity

---

## 🔜 2. PROMPT BUILDER LAYER
- structured prompt templates
- context compression
- model-specific formatting

---

## 🤖 3. AGENT LAYER
- multi-step reasoning
- tool usage
- planning loop
- autonomous execution flow

---

## 🧾 4. RESPONSE FORMAT v2
- JSON / Markdown / UI outputs
- multi-channel responses
- structured templates

---

## 📡 5. STREAMING SUPPORT
- token streaming
- real-time UX layer

---

# 🧱 SYSTEM CLASS

Production-capable modular AI backend:
> MVP → STABLE CORE → PRE-AGENT FOUNDATION → AGENT READY ARCHITECTURE