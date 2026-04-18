# 🧠 PROJECT ARCHITECTURE (v1 — STABLE CORE)

## 🎯 Goal
Minimal stable AI system with controlled and incremental growth.

System is designed as a modular backend with strict separation of concerns and deterministic execution flow.

---

# 🧱 ACTIVE FILES (CURRENT PRODUCTION STAGE — STABLE CORE)

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

## app/engine/llm.py
LLM execution layer.
- executes model inference
- no decision-making
- stateless
- does NOT select models

---

## app/engine/model_router.py
Model selection layer.
- routing logic (fast / smart / fallback)
- selects from available model pool
- keeps system model-agnostic

---

## app/contracts/message.py
Data contract layer.
- defines strict input/output schemas
- ensures consistent data flow between layers
- prevents implicit or unsafe data structures across system boundaries

---

# ⚙️ CURRENT FLOW (MVP — STABLE)

Telegram  
→ webhook  
→ orchestrator  
→ model_router  
→ llm  
→ response

---

# 🚀 TARGET ARCHITECTURE (FUTURE EXPANSION)

Telegram  
→ webhook  
→ orchestrator  
→ engine (agent)  
→ tools / memory  
→ response

---

# 🚀 RESERVED (NOT IMPLEMENTED YET)

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
A module is created ONLY if:
- extending existing module breaks responsibility boundaries

---

## 2. Single Responsibility Principle
Each module has exactly one responsibility.

No mixed concerns.

---

## 3. Deletion rule
Unused modules must be removed immediately.

---

## 4. Scale rule (MVP constraint)
Maximum active modules in MVP stage: 7

---

## 5. Infrastructure separation rule
- no deployment logic inside application code
- no Railway / Procfile coupling in business logic

---

# 🧠 MODEL SYSTEM

## ⚡ FAST MODELS (low latency, cheap)
- groq/compound-mini  
- llama-3.1-8b-instant  

---

## 🧠 GENERAL MODELS (balanced reasoning)
- llama-3.3-70b-versatile  
- qwen/qwen3-32b  
- openai/gpt-oss-20b  

---

## 🧠 HEAVY / SMART MODELS (high reasoning)
- openai/gpt-oss-120b  
- meta-llama/llama-4-scout-17b-16e-instruct  

---

## 🛡 SAFETY / GUARD MODELS
- openai/gpt-oss-safeguard-20b  
- meta-llama/llama-prompt-guard-2-22m  
- meta-llama/llama-prompt-guard-2-86m  

---

## 🎙 AUDIO MODELS
- whisper-large-v3  
- whisper-large-v3-turbo  

---

## 🎭 SPECIAL / EXPERIMENTAL
- allam-2-7b  
- groq/compound  
- canopylabs/orpheus-v1-english  
- canopylabs/orpheus-arabic-saudi  

---

# ⚙️ DEPLOYMENT

## Runtime
Application is started via Procfile.

## Notes
- Procfile is single source of truth
- system must remain portable across environments

---

# 🔐 ENVIRONMENT VARIABLES

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
- no direct external calls outside engine layer (future rule)  

---

# 💥 STATUS

## 🟢 SYSTEM STATUS: STABLE CORE (v1)

System is:
- deployable  
- modular  
- deterministic  
- ready for Telegram integration  
- ready for incremental scaling