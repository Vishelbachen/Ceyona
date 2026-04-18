# 🧠 PROJECT ARCHITECTURE (v1 — STABLE CORE)

## 🎯 Цель
Минимальный, стабильный AI-бот с возможностью роста.

---

# ✅ ACTIVE FILES (используются)

## 1. main.py
Точка входа (FastAPI)
- запускает сервер
- подключает роуты

## 2. app/api/webhook.py
Webhook (Telegram → API)
- принимает сообщения
- передаёт их в систему

## 3. app/llm.py
Работа с LLM (Groq)
- отправка запроса
- получение ответа

---

# ⚙️ CURRENT FLOW

Telegram → webhook.py → llm.py → ответ пользователю

---

# 🚫 НЕ СУЩЕСТВУЕТ (пока запрещено)

- agent.py
- model_router.py
- tool_router.py
- memory.py
- orchestrator.py

❗ Эти файлы будут добавляться ТОЛЬКО при необходимости

---

# 🔒 RULES (обязательно)

## 1. Новый файл
Создаётся только если:
- невозможно расширить существующий

## 2. Любой файл должен:
- использоваться (import / вызов)
- иметь чёткую роль

## 3. Если файл не используется:
→ он удаляется

## 4. Максимум активных файлов:
→ до 7 (на этом этапе)

---

# 🚀 NEXT STEP (план развития)

1. Стабилизировать webhook + llm
2. Добавить model_router (если появится 2+ модели)
3. Добавить agent (логика)
4. Добавить memory (история)

---

# 🧠 ИСТИНА ПРОЕКТА

Этот файл — источник правды.
Если файл не указан здесь — его не существует.

---

# 🔐 ENVIRONMENT VARIABLES (SECRETS LAYER)

Все ключи хранятся ТОЛЬКО в environment variables (Railway / .env).
Никогда не хардкодятся в коде.

---

## 🤖 AI / LLM
- GROQ_API_KEY

---

# 🧠 MODEL STRATEGY

- модели не фиксируются в архитектуре
- выбор модели осуществляется через runtime (model_router)
- система поддерживает динамический список моделей от провайдера

---

## 🤖 Telegram Bot
- BOT_TOKEN

---

## 🔐 Security
- JWT_SECRET
- ENCRYPTION_KEY

---

## 🧠 Backend / DB
- SUPABASE_URL
- SUPABASE_ANON_KEY
- SUPABASE_SERVICE_ROLE_KEY

---

## 🌍 External APIs
- OPENWEATHER_API_KEY
- MAPBOX_TOKEN
- SERPAPI_KEY
- BREVO_API_KEY

---

## 💳 Payments / Wallet
- TON_WALLET

---

## 🌐 Deployment
- WEBHOOK_URL

---

# 🚫 RULES

- Никогда не коммитить реальные ключи в GitHub
- Все ключи только через Railway Variables
- Любой новый API → добавляется сюда до использования