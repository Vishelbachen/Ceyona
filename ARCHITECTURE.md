# 🧠 PROJECT ARCHITECTURE (v1 — STABLE CORE)

## 🎯 Goal
Minimal stable AI system with controlled and incremental growth.

System is designed as a modular backend with strict separation of concerns.

---

# 🧱 ACTIVE FILES (current production stage)

## main.py
FastAPI entry point.

## app/api/webhook.py
Telegram webhook handler.
- receives external messages
- forwards them to orchestrator layer

## app/llm.py
LLM execution layer.
- executes model inference
- does NOT perform model selection

## app/core/orchestrator.py
Application flow controller.
- receives input from API layer (webhook)
- selects model via model_router
- calls LLM

---

# ⚙️ CURRENT FLOW (MVP)

Telegram → webhook → orchestrator → llm → response

---

# 🚀 TARGET ARCHITECTURE (future state)

Telegram → webhook → core/orchestrator → engine → llm → tools/memory → response

---

# 🚀 RESERVED (not implemented yet)

## app/engine/model_router.py
Planned model selection layer
- dynamic model routing
- fallback logic
- runtime model discovery via Groq API

## app/engine/agent.py
Planned reasoning / decision layer

## app/tools/tool_router.py
Planned external tool execution layer

## app/memory/
Planned persistence layer (sessions, history, state)

---

# 🔒 ARCHITECTURAL RULES

## 1. File creation rule
A new module is created only if:
- existing module cannot be extended without violating responsibility boundaries

## 2. Single Responsibility Principle
Each module must have exactly one responsibility:
- no mixing of routing, execution, and transport layers

## 3. Deletion rule
Unused or unreferenced files must be removed to prevent architectural drift

## 4. Scale rule (MVP constraint)
Maximum active modules in MVP stage: 7

---

# 🧠 MODEL SYSTEM

- models are dynamically provided by Groq API at runtime
- system does not rely on a static model registry
- model selection is delegated to model_router (future module)
- Groq API is the source of truth for available models
- llm layer is execution-only and does not perform decision-making

---

# 🔐 ENVIRONMENT VARIABLES

All secrets must be stored in environment variables only.

No hardcoded credentials are allowed.

---

## AI / LLM
- GROQ_API_KEY

---

## Telegram Integration
- BOT_TOKEN

---

## Security Layer
- JWT_SECRET
- ENCRYPTION_KEY

---

## Backend / Database
- SUPABASE_URL
- SUPABASE_ANON_KEY
- SUPABASE_SERVICE_ROLE_KEY

---

## External APIs
- OPENWEATHER_API_KEY
- MAPBOX_TOKEN
- SERPAPI_KEY
- BREVO_API_KEY

---

## Payments
- TON_WALLET

---

## Deployment
- WEBHOOK_URL

---

# 🚫 SECURITY RULES

- no secrets in repository
- only environment variables via deployment platform (e.g. Railway)
- all new integrations must be explicitly registered in this document before implementation