# 🧠 FINAL ARCHITECTURE (v1.3 — STABLE CORE SIMPLIFIED + CONFIG INTEGRATED)

---

# 🎯 GOAL
Minimal production-ready AI backend with:
- strict separation of concerns
- deterministic execution flow
- full traceable request lifecycle (trace_id)
- unified response + error handling
- optional memory layer (session-based)
- centralized configuration system (`settings.py`)
- integrated multi-model system (ALL models routed via engine layer)
- clean upgrade path to Agent Layer

---

# 🧱 SYSTEM OVERVIEW (SIMPLIFIED)

## 🟢 ARCHITECTURE MODEL

API LAYER  
↓  
CORE LAYER (ORCHESTRATION)  
↓  
ENGINE LAYER (EXECUTION + TRANSPORT)  
↓  
DOMAIN LAYER (CONTRACTS + LOGGING + RESPONSE)  
↓  
MEMORY LAYER (OPTIONAL STATE)  
↓  
CONFIG LAYER (CENTRALIZED SETTINGS)

---

# 🔁 FULL REQUEST FLOW (PRODUCTION FLOW)

Telegram  
→ webhook (API)  
→ Orchestrator (CORE)  
→ MemoryService (optional context injection)  
→ Model Router (ENGINE)  
→ LLM (ENGINE)  
→ Response Handler (DOMAIN)  
→ Telegram Sender (ENGINE)  
→ User  

---

# 📦 ACTIVE FILES (STABLE CORE++)

---

# 🚪 API LAYER

## main.py
FastAPI bootstrap:
- application startup
- route registration
- lifecycle management

---

## app/api/webhook.py
Telegram INBOUND layer:

Responsibilities:
- receive Telegram updates
- validate payload safely
- generate trace_id
- build `OrchestratorRequest`
- call `handle_request`
- pass result to `ResponseHandler`
- no business logic
- no formatting logic

---

# 🧠 CORE LAYER

## app/core/orchestrator.py

Responsibilities:
- central execution coordinator
- receives `OrchestratorRequest`
- full lifecycle logging
- model selection coordination
- LLM execution orchestration
- optional memory integration

Returns:
- `SuccessResponse`
- `ErrorResponse`

Lifecycle:
- start
- memory load (optional)
- model selection
- prompt building
- LLM call
- memory save (optional)
- return response

❌ no transport logic

---

# ⚙️ ENGINE LAYER

## app/engine/model_router.py

Model routing logic:

- selects model based on input size
- simple deterministic routing
- no execution logic

### Current model routing:
- small text → `groq/compound-mini`
- medium text → `llama-3.3-70b-versatile`
- large text → `openai/gpt-oss-120b`

---

## 🧠 FULL MODEL SYSTEM (INTEGRATED)

### ⚡ FAST MODELS
- groq/compound-mini  
- llama-3.1-8b-instant  

### 🧠 GENERAL MODELS
- llama-3.3-70b-versatile  
- qwen/qwen3-32b  
- openai/gpt-oss-20b  

### 🧠 HEAVY MODELS
- openai/gpt-oss-120b  
- meta-llama/llama-4-scout-17b-16e-instruct  

### 🛡 SAFETY MODELS
- openai/gpt-oss-safeguard-20b  
- meta-llama/llama-prompt-guard-2-22m  
- meta-llama/llama-prompt-guard-2-86m  

### 🎙 AUDIO MODELS
- whisper-large-v3  
- whisper-large-v3-turbo  

### 🎭 EXPERIMENTAL MODELS
- allam-2-7b  
- groq/compound  
- orpheus models  

✔ All models are unified and controlled via `model_router.py` + future extensions in engine layer.

---

## app/engine/llm.py

Responsibilities:
- model inference execution
- retry logic (bounded)
- timeout handling
- structured logging with trace_id
- stateless execution
- future Groq/OpenAI integration via `settings.py`

---

## app/engine/telegram.py

Responsibilities:
- Telegram Bot API client
- pure HTTP transport layer
- no business logic

✔ Uses:
`settings.BOT_TOKEN`

---

# 🧩 DOMAIN LAYER

## app/contracts/message.py
- UserMessage
- OrchestratorRequest

Ensures:
- strict schema
- trace_id propagation

---

## app/contracts/response.py

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
Shared context schema:
memory-ready
future agent layer compatible
app/core/errors.py
Unified error system:
AppError
OrchestratorError
LLMError
RouterError
APIError
app/core/logger.py
Structured JSON logging system:
Tracked events:
webhook_received
orchestrator_start
memory_loaded
model_selected
llm_request
llm_response
memory_saved
response_sent
app/core/response_handler.py
Responsibilities:
normalize responses
convert system output → user text
send via Telegram engine
ensure trace_id consistency
isolate transport concerns
🧠 MEMORY LAYER (OPTIONAL)
app/memory/session_store.py
in-memory user session storage
append message history
fast access
MVP-level implementation
app/memory/memory_service.py
builds context from session history
injects into orchestrator
saves messages after response
fully optional (safe fallback enabled)
⚙️ CONFIG LAYER (NEW — CRITICAL IMPROVEMENT)
app/config/settings.py (NEW SINGLE SOURCE OF TRUTH)
Responsibilities:
replaces ALL os.getenv() usage
central configuration loader
production-safe environment isolation
validation of critical variables
Used by:
telegram.py → BOT_TOKEN
llm.py → GROQ_API_KEY (future)
security layer
external API integrations
deployment configuration
app/config/init.py
Python
# empty file (required for package import)
✔ exists in all modules (standard Python package structure)
❌ REMOVED ARCHITECTURE PART
🔐 ENVIRONMENT VARIABLES SECTION (REMOVED)
Old duplicated config section is fully removed because:
✔ replaced by settings.py
✔ single source of truth
✔ no duplication risk
✔ cleaner architecture
🚫 SECURITY RULES
no secrets in repository
all config via settings.py
engine-only external API calls
strict separation of transport vs business logic
📊 OBSERVABILITY (TRACE PIPELINE)
Full lifecycle:
webhook_received
→ orchestrator_start
→ memory_loaded
→ model_selected
→ llm_request
→ llm_response
→ memory_saved
→ response_sent
💥 CURRENT STATUS (FINAL)
🟢 SYSTEM IS:
fully stable
production-ready MVP
memory-enabled (optional)
config-centralized
multi-model integrated
fully traceable
clean layered architecture
safe for scaling
⚠️ LIMITATIONS (INTENTIONAL)
no persistent memory (Redis/DB future)
no agent reasoning layer
no streaming responses
no tool execution system
🚀 NEXT EVOLUTION
🔜 1. MEMORY PERSISTENCE (Redis / DB)
🔜 2. PROMPT BUILDER LAYER
🔜 3. AGENT LAYER (multi-step reasoning)
🔜 4. RESPONSE FORMAT v2 (structured UI / JSON)
🔜 5. STREAMING TOKENS
🧱 SYSTEM CLASS
Production AI backend:
MVP → Stable Core → Agent-ready foundation