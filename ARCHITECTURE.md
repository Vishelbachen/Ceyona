# 🧠 PROJECT ARCHITECTURE (v1.1 — STABLE CORE + TELEGRAM LOOP)

## 🎯 Goal
Minimal stable AI system with controlled and incremental growth.

System is designed as a modular backend with strict separation of concerns, deterministic execution flow, and full request lifecycle visibility (traceable pipeline).

---

# 🧱 ACTIVE FILES (CURRENT PRODUCTION STAGE — STABLE CORE+)

## main.py
FastAPI entry point.
- application bootstrap
- route registration
- lifecycle management

---

## app/api/webhook.py
Telegram webhook handler (INBOUND layer).
- receives external messages from Telegram
- validates and parses payload
- generates `trace_id`
- builds `OrchestratorRequest`
- forwards request to orchestrator (`handle_request`)
- sends response via Response Layer

---

## app/core/orchestrator.py
Application flow controller (CORE layer).
- central coordination point
- receives structured request (`OrchestratorRequest`)
- logs lifecycle:
  - start
  - model selection
  - LLM call
  - completion
  - error handling
- invokes model_router
- calls LLM execution layer
- returns raw response text

---

## app/engine/model_router.py
Model selection layer.
- routing logic (fast / smart / fallback)
- selects model from available pool
- keeps system model-agnostic
- no execution logic

---

## app/engine/llm.py
LLM execution layer (ENGINE).
- executes model inference (stub / Groq-compatible abstraction)
- retry logic (bounded)
- timeout handling
- structured logging with trace_id
- stateless execution
- NO decision-making responsibility

---

## app/engine/telegram.py
Telegram transport layer (OUTBOUND adapter).
- sends messages via Telegram Bot API
- pure HTTP client
- no business logic
- no orchestration responsibility
- used ONLY by response layer

---

## app/core/response_handler.py
Response abstraction layer.
- unifies output delivery
- decouples business logic from transport
- formats response text
- routes to Telegram transport
- logs `response_sent`
- ensures trace_id propagation

---

## app/contracts/message.py
Data contract layer.
- strict schemas:
  - `UserMessage`
  - `OrchestratorRequest`
- enforces structured data flow
- guarantees trace consistency across system

---

## app/core/logger.py
Structured logging system.
- JSON logs
- unified format
- includes:
  - timestamp
  - event
  - trace_id
  - payload
- used across all layers

# 🔁 REQUEST LIFECYCLE (TRACEABLE PIPELINE)

Each request includes:

- trace_id (UUID)
- full lifecycle tracking
- structured logs per stage

```text
trace_id: abc-123

webhook_received
→ orchestrator_start
→ model_selected
→ llm_request
→ llm_response
→ orchestrator_done
→ response_sent

# 🧠 MODEL SYSTEM

## ⚡ FAST MODELS (low latency)
- groq/compound-mini  
- llama-3.1-8b-instant  

---

## 🧠 GENERAL MODELS (balanced reasoning)
- llama-3.3-70b-versatile  
- qwen/qwen3-32b  
- openai/gpt-oss-20b  

---

## 🧠 HEAVY MODELS (reasoning)
- openai/gpt-oss-120b  
- meta-llama/llama-4-scout-17b-16e-instruct  

---

## 🛡 SAFETY MODELS
- openai/gpt-oss-safeguard-20b  
- meta-llama/llama-prompt-guard-2-22m  
- meta-llama/llama-prompt-guard-2-86m  

---

## 🎙 AUDIO MODELS
- whisper-large-v3  
- whisper-large-v3-turbo  

---

## 🎭 EXPERIMENTAL
- allam-2-7b  
- groq/compound  
- canopylabs/orpheus-v1-english  
- canopylabs/orpheus-arabic-saudi  

---

# 🔒 ARCHITECTURAL RULES

## 1. Single Responsibility Principle
Each module has exactly one responsibility.

---

## 2. Layer Separation

| Layer     | Responsibility              |
|----------|-----------------------------|
| API       | Input handling              |
| Core      | Orchestration               |
| Engine    | Execution (LLM / transport) |
| Contracts | Data schemas                |
| Logger    | Observability              |

---

## 3. Transport Isolation
- Telegram is NOT part of business logic  
- Telegram = external transport adapter  
- inbound ≠ outbound  

---

## 4. Deterministic Flow
No hidden logic, no side effects.

---

## 5. No Dead Code
Unused modules are removed immediately.

---

## 6. MVP Scale Constraint
Max active modules in MVP stage: 8

---

## 7. Infrastructure Separation
- no deployment logic in code  
- environment-based configuration only  

---

# 🔐 ENVIRONMENT VARIABLES

## AI / LLM
- GROQ_API_KEY  

---

## Telegram
- BOT_TOKEN  

---

## Security
- JWT_SECRET  
- ENCRYPTION_KEY  

---

## Database (reserved)
- SUPABASE_URL  
- SUPABASE_ANON_KEY  
- SUPABASE_SERVICE_ROLE_KEY  

---

## External APIs (reserved)
- OPENWEATHER_API_KEY  
- MAPBOX_TOKEN  
- SERPAPI_KEY  
- BREVO_API_KEY  

---

## Payments (reserved)
- TON_WALLET  

---

## Deployment
- WEBHOOK_URL  

---

# 🚫 SECURITY RULES

- no secrets in repository  
- env-only configuration  
- no direct external calls outside engine layer  
- strict separation of transport vs business logic  

---

# 📊 OBSERVABILITY

## Logging

JSON structured logs including:
- timestamp  
- event  
- trace_id  
- payload  

---

## Debug capability
- full request trace  
- LLM visibility  
- retry tracking  
- response lifecycle tracking  

---

# 💥 CURRENT LIMITATIONS

- no memory / session layer  
- no agent / reasoning layer  
- no unified error schema yet  
- response layer is minimal (no formatting policies yet)  

---

# 🚀 NEXT EVOLUTION (PLANNED)

## 1. Error Schema Layer (NEXT PRIORITY)
- standard error format  
- remove raw string errors  

---

## 2. Memory Layer
- session persistence  
- chat history  

---

## 3. Agent Layer
- reasoning engine  
- multi-step execution  

---

## 4. Response Formatting Policy
- structured outputs  
- templates per message type  

---

# 💥 STATUS

## 🟢 SYSTEM STATUS: STABLE CORE v1.1

System is:
- fully working (end-to-end)  
- traceable  
- modular  
- transport-enabled (Telegram IN/OUT)  
- response-layer separated  
- ready for controlled scaling  

---

# 🧱 SYSTEM CLASS

Production-capable modular AI backend (MVP stage)
---

# ⚙️ CURRENT FLOW (MVP — FULL LOOP)

```text
Telegram
→ webhook (INBOUND)
→ orchestrator (CORE)
→ model_router (ENGINE)
→ llm (ENGINE)
→ orchestrator (CORE)
→ response_handler (RESPONSE LAYER)
→ telegram.py (OUTBOUND)
→ Telegram user

