# 🧠 PROJECT ARCHITECTURE (v1 — STABLE CORE)

## 🎯 Goal
Minimal stable AI system with controlled growth.

---

# 🧱 ACTIVE FILES (current production stage)

## main.py
FastAPI entry point

## app/api/webhook.py
Telegram webhook handler

## app/llm.py
Direct LLM execution layer

---

# ⚙️ CURRENT FLOW (MVP)

Telegram → webhook → llm → response

---

# 🚀 FUTURE FLOW (target architecture)

Telegram → webhook → core/orchestrator → engine → llm → tools/memory → response

---

# 🧠 NOT ACTIVE (planned modules)

These modules are not implemented yet but reserved:

- app/core/orchestrator.py
- app/engine/model_router.py
- app/engine/agent.py
- app/tools/tool_router.py
- app/memory/

---

# 🔒 RULES

## 1. File creation rule
A new file is created only if:
- existing module cannot be extended safely

## 2. Responsibility rule
Each file must have a single responsibility

## 3. Deletion rule
Unused files must be removed

## 4. Scale rule
Maximum active files in MVP stage: 7

---

# 🧠 MODEL SYSTEM

- models are dynamically provided by Groq API at runtime
- system does not rely on a static model registry
- model_router is responsible for model selection and fallback logic
- Groq API is the source of available model data

---

# 🔐 ENVIRONMENT VARIABLES

All secrets are stored in environment variables only.

Never hardcoded.

---

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

## Backend / DB
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
- only environment variables
- all new integrations must be declared here first