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
- builds OrchestratorRequest
- forwards request to orchestrator
- sends response via Telegram API

---

## app/core/orchestrator.py
Application flow controller (CORE layer).
- central coordination point
- receives structured request
- logs lifecycle (start / end / error)
- invokes model_router
- calls LLM layer
- returns final response

---

## app/engine/model_router.py
Model selection layer.
- routing logic (fast / smart / fallback)
- selects model from available pool
- keeps system model-agnostic

---

## app/engine/llm.py
LLM execution layer.
- executes model inference
- retry logic
- timeout handling
- structured logging
- NO decision-making
- stateless

---

## app/engine/telegram.py
Telegram transport layer (OUTBOUND).
- sends messages via Telegram Bot API
- pure HTTP client
- no business logic
- no orchestration responsibility

---

## app/contracts/message.py
Data contract layer.
- defines strict schemas
- `UserMessage`
- `OrchestratorRequest` (with trace_id)
- ensures safe and consistent data flow

---

## app/core/logger.py
Structured logging system.
- JSON logs
- unified log format
- supports `trace_id`
- used across all layers

---

# ⚙️ CURRENT FLOW (MVP — FULL LOOP)

Telegram  
→ webhook (IN)  
→ orchestrator  
→ model_router  
→ llm  
→ orchestrator  
→ telegram (OUT)  
→ Telegram user  

---

# 🔁 REQUEST LIFECYCLE (TRACEABLE)

Each request includes:

- `trace_id` (UUID)
- full pipeline visibility
- structured logs per stage

Example flow:

```text
trace_id: abc-123

webhook_received
→ orchestrator_start
→ model_selected
→ llm_request
→ llm_response
→ orchestrator_done
→ telegram_send

# 🧠 MODEL SYSTEM

## ⚡ FAST MODELS (low latency)
- groq/compound-mini  
- llama-3.1-8b-instant  

---

## 🧠 GENERAL MODELS (balanced)
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

| Layer        | Responsibility               |
|--------------|------------------------------|
| API          | Input handling               |
| Core         | Orchestration                |
| Engine       | Execution (LLM / transport)  |
| Contracts    | Data schemas                 |
| Core/Logger  | Observability                |

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
Max active modules in MVP stage: 7–8 (current: 8)

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
- no direct external calls outside engine layer (future enforcement)  

---

# 📊 OBSERVABILITY

## Logging
- JSON structured logs  
- includes:
  - timestamp  
  - event  
  - trace_id  
  - payload  

---

## Debug capability
- full request trace  
- LLM visibility  
- retry tracking  

---

# 💥 CURRENT LIMITATIONS

- Telegram tightly coupled in webhook (no response abstraction yet)  
- no response formatting layer  
- no error standardization schema  
- no memory / session layer  
- no agent / reasoning layer  

---

# 🚀 NEXT EVOLUTION (PLANNED)

## 1. Response Layer
- decouple transport from API  
- unified response handling  

---

## 2. Error Schema
- consistent error structure across system  

---

## 3. Agent Layer
- reasoning  
- multi-step execution  

---

## 4. Memory Layer
- persistence  
- chat history  

---

# 💥 STATUS

## 🟢 SYSTEM STATUS: STABLE CORE v1.1

System is:
- fully working (end-to-end)  
- traceable  
- modular  
- transport-enabled (Telegram IN/OUT)  
- ready for controlled scaling  

---

# 🧱 SYSTEM CLASS

Production-capable modular AI backend (MVP stage)

---