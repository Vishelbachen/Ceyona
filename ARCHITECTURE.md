# 🧠 PROJECT ARCHITECTURE (v1 — STABLE CORE)

## 🎯 Goal
Minimal stable AI system with controlled and incremental growth.

System is designed as a modular backend with strict separation of concerns and deterministic execution flow.

---

# 🧱 ACTIVE FILES (current production stage — 5 FILES)

## main.py
FastAPI entry point.
- application bootstrap
- route registration
- lifecycle management

---

## app/api/webhook.py
Telegram webhook handler.
- receives external messages
- validates input
- forwards request to orchestrator

---

## app/core/orchestrator.py
Application flow controller.
- central coordination layer
- receives input from API layer
- invokes model_router
- calls LLM layer
- returns final response

---

## app/llm.py
LLM execution layer.
- executes model inference
- no decision-making
- stateless
- does NOT select models

---

## app/engine/model_router.py
Model selection layer.
- dynamic model discovery via Groq API
- routing logic (fast / smart / fallback)
- handles model availability

---

# ⚙️ CURRENT FLOW (MVP)

Telegram  
→ webhook  
→ orchestrator  
→ model_router  
→ llm  
→ response

---

# 🚀 TARGET ARCHITECTURE (future expansion)

Telegram  
→ webhook  
→ orchestrator  
→ engine (agent)  
→ tools / memory  
→ response

---

# 🚀 RESERVED (not implemented yet)

## app/engine/agent.py
Planned reasoning layer
- decision making
- multi-step execution

---

## app/tools/tool_router.py
Planned tool execution layer
- external APIs
- function calling

---

## app/memory/
Planned persistence layer
- sessions
- chat history
- state management

---

# 🔒 ARCHITECTURAL RULES

## 1. File creation rule
A new module is created ONLY if:
- extending existing module would violate responsibility boundaries

---

## 2. Single Responsibility Principle
Each module must have exactly one responsibility.

No mixed concerns allowed.

---

## 3. Deletion rule
Unused or abandoned modules must be removed immediately.

No dead code.

---

## 4. Scale rule (MVP constraint)
Maximum active modules in MVP stage: 7

---

## 5. Infrastructure separation rule
- application logic must NOT depend on deployment details
- no Railway / Procfile / environment logic inside code

---

# 🧠 MODEL SYSTEM

- models are dynamically fetched via Groq API
- no static model registry
- model_router is the decision layer
- llm is execution-only
- system is model-agnostic by design

---

# ⚙️ DEPLOYMENT

## Runtime
Application is started via Procfile:

## Notes
- Procfile is the single source of truth for execution
- UI-based start commands must not be relied upon
- system must remain portable across environments

---

# 🔐 ENVIRONMENT VARIABLES

All secrets must be stored in environment variables ONLY.

No hardcoded values.

---

## AI / LLM
- GROQ_API_KEY

## Telegram
- BOT_TOKEN

## Security
- JWT_SECRET
- ENCRYPTION_KEY

## Database
- SUPABASE_URL
- SUPABASE_ANON_KEY
- SUPABASE_SERVICE_ROLE_KEY

## External APIs
- OPENWEATHER_API_KEY
- MAPBOX_TOKEN
- SERPAPI_KEY
- BREVO_API_KEY

## Payments
- TON_WALLET

## Deployment
- WEBHOOK_URL

---

# 🚫 SECURITY RULES

- no secrets in repository
- environment variables only
- all integrations must be declared before implementation
- no direct external calls outside tool layer (future rule)

---

# 💥 STATUS

Architecture is stable and ready for:
- webhook integration
- Telegram connection
- incremental feature expansion