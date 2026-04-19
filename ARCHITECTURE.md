# 🧠 PROJECT ARCHITECTURE (v1.3 — STABLE CORE SIMPLIFIED + MEMORY READY)

## 🎯 GOAL
Production-capable modular AI backend with:
- strict separation of concerns (simplified)
- deterministic execution flow
- full traceable request lifecycle
- unified response + error handling
- memory-ready architecture (prepared, not required)
- clean upgrade path to Agent Layer

---

# 🧱 SYSTEM OVERVIEW (SIMPLIFIED)

## 🟢 ARCHITECTURE MODEL

API LAYER ↓ CORE LAYER (ORCHESTRATION) ↓ ENGINE LAYER (EXECUTION) ↓ DOMAIN LAYER (CONTRACTS + RESPONSE + LOGGING) ↓ TRANSPORT (Telegram via Engine)

---

# 🔁 FULL REQUEST FLOW (CURRENT)
Telegram → webhook (API) → Orchestrator (CORE) → Model Router (ENGINE) → LLM (ENGINE) → Response Handler (DOMAIN) → Telegram Sender (ENGINE) → User

---

# 📦 ACTIVE FILES (PRODUCTION STATE)

---

## 🚪 API LAYER

### main.py
FastAPI entry point:
- app bootstrap
- lifecycle init
- route registration

---

### app/api/webhook.py
Telegram INBOUND adapter:
- receives Telegram updates
- extracts payload
- generates trace_id
- builds OrchestratorRequest
- calls orchestrator
- passes result to ResponseHandler

Responsibilities:
- input validation
- no business logic
- no AI logic
- no formatting

---

# 🧠 CORE LAYER

---

### app/core/orchestrator.py
Central application controller:

Responsibilities:
- request coordination
- model selection coordination
- memory integration (optional)
- LLM invocation orchestration
- error normalization
- trace lifecycle logging

Flow:
- receive OrchestratorRequest
- load memory (optional)
- select model
- build prompt
- call LLM
- save memory (optional)
- return SuccessResponse / ErrorResponse

---

# ⚙️ ENGINE LAYER

---

### app/engine/model_router.py
Model selection system:

Responsibilities:
- choose best model based on input
- routing logic (fast / general / heavy / safety)
- no execution logic

---

### app/engine/llm.py
LLM execution layer:

Responsibilities:
- model inference execution
- retry logic
- timeout handling
- structured logging
- returns LLMResponse

Stateless execution only.

---

### app/engine/telegram.py
Transport adapter:

Responsibilities:
- send messages via Telegram Bot API
- HTTP client only
- no business logic
- used exclusively by Response Layer

---

# 🧩 DOMAIN LAYER

---

## 📜 app/contracts/message.py
Data contracts:

- UserMessage
- OrchestratorRequest

Guarantees:
- strict input schema
- trace_id propagation
- deterministic structure

---

## 📜 app/contracts/response.py
Unified response schema:

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
❌ app/core/errors.py (DOMAIN ERROR SYSTEM)
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
📊 app/core/logger.py
Structured logging system:
JSON logs
trace_id tracking
event-based logs
Events:
webhook_received
orchestrator_start
model_selected
llm_request
llm_response
response_sent
error events
📤 app/domain/response_handler.py
Unified output handler:
Responsibilities:
normalize Success/ErrorResponse
format user-facing text
send via telegram engine
guarantee delivery attempt logging
Flow:
receive response object
extract text/error
send via telegram adapter
log success/failure
🧠 MEMORY LAYER (READY BUT OPTIONAL)
app/memory/session_store.py
In-memory session storage:
user message history
assistant message history
simple key-value structure
app/memory/memory_service.py
Memory orchestration:
build context for LLM
append messages after response
isolation from orchestrator logic
IMPORTANT:
optional dependency
system works without it
🧠 MODEL SYSTEM (IMPORTANT - DO NOT REMOVE)
⚡ FAST MODELS
groq/compound-mini
llama-3.1-8b-instant
Use case:
low latency responses
simple queries
🧠 GENERAL MODELS
llama-3.3-70b-versatile
qwen/qwen3-32b
openai/gpt-oss-20b
Use case:
balanced reasoning
standard chat
🧠 HEAVY MODELS
openai/gpt-oss-120b
meta-llama/llama-4-scout-17b-16e-instruct
Use case:
deep reasoning
complex tasks
🛡 SAFETY MODELS
openai/gpt-oss-safeguard-20b
meta-llama/llama-prompt-guard-2-22m
meta-llama/llama-prompt-guard-2-86m
Use case:
moderation
safety filtering
🎙 AUDIO MODELS
whisper-large-v3
whisper-large-v3-turbo
Use case:
speech-to-text
🎭 EXPERIMENTAL MODELS
allam-2-7b
groq/compound
canopylabs/orpheus-v1-english
canopylabs/orpheus-arabic-saudi
Use case:
testing
experimental pipelines
future agent features
🔐 ENVIRONMENT VARIABLES (CRITICAL)
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
no secrets in repo
env-only configuration
no direct external calls outside engine layer
strict transport isolation
no business logic in API layer
📊 OBSERVABILITY
Logging includes:
timestamp
event
trace_id
payload
model used
execution stage
Trace lifecycle:

webhook_received
→ orchestrator_start
→ model_selected
→ llm_request
→ llm_response
→ response_sent
→ error (if any)
💥 CURRENT STATUS (STABLE CORE v1.3)
System is:
✅ fully working end-to-end
✅ production-stable pipeline
✅ traceable request lifecycle
✅ modular but simplified architecture
✅ memory-ready (optional)
✅ safe response handling
✅ multi-model routing enabled
⚠️ CURRENT LIMITATIONS
no persistent memory (only in-memory optional)
no agent reasoning layer
no streaming responses
no structured UI responses (v2 planned)
no tool-usage system yet
🚀 ROADMAP (NEXT EVOLUTION)
🔜 1. MEMORY LAYER (PRODUCTION)
Redis-based storage
TTL sessions
context summarization
🔜 2. PROMPT BUILDER LAYER
structured prompt formatting
context compression
model-specific templates
🤖 3. AGENT LAYER (MAJOR UPGRADE)
multi-step reasoning
tool usage
planning loop
autonomous decision flow
🧾 4. RESPONSE FORMAT v2
JSON / Markdown / UI formats
structured output schemas
channel-based formatting
📡 5. STREAMING SUPPORT
partial responses
token streaming
real-time UX
🧱 SYSTEM CLASS
Production-ready modular AI backend:
MVP → STABLE CORE → PRE-AGENT ARCHITECTURE