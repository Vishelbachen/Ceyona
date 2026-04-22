# 🚀 Ceyona AI

Ceyona is a modular AI SaaS system with multi-model routing, memory intelligence, and payment integration.

## 🧠 Features
- Multi-model AI (Gemini / OpenAI / Groq / Mistral)
- Long-term memory (Supabase)
- Telegram bot interface
- Tool system (Maps, Weather, Search)
- TON-based monetization
- Self-correcting reasoning engine

## ⚙️ Architecture
- engine → AI brain (router, reasoning, solver)
- ai → model providers
- memory → Supabase memory system
- payments → TON billing system
- services → external APIs

## 🚀 Setup

1. Clone repo
2. Install dependencies:
   pip install -r requirements.txt
3. Create `.env` from `.env.example`
4. Run:
   python main.py

## ⚠️ Security
Never expose:
- service_role keys
- API secrets
- .env file

## 🧠 Status
MVP in development stage

## License

All rights reserved.

This project is proprietary software.
Unauthorized copying, distribution, or modification is prohibited.