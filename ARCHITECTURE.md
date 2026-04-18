# 🧠 PROJECT ARCHITECTURE (v1 — STABLE CORE)

## 🎯 Goal
Minimal stable AI system with controlled and incremental growth.

System is designed as a modular backend with strict separation of concerns.

---

# 🧱 ACTIVE FILES (current production stage)

## main.py
FastAPI entry point.
- starts application
- mounts API routes

## app/api/webhook.py
Telegram webhook handler.
- receives external messages
- forwards them to application layer

## app/llm.py
LLM execution layer.
- executes model inference
- does NOT contain model selection logic

---

# ⚙️ CURRENT FLOW (MVP)

Telegram → webhook → llm → response

---

# 🚀 TARGET ARCHITECTURE (future state)

Telegram → webhook → core/orchestrator → engine → llm → tools/memory → response

---

# 🧠 NOT ACTIVE (reserved modules)

These modules are planned but not yet implemented:

- app/core/orchestrator.py
- app/engine/model_router.py
- app/engine/agent.py
- app/tools/tool_router.py
- app/memory/

These modules are part of the future scalable architecture.

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