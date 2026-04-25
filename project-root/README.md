Ceyona AI

Ceyona is an experimental AI backend focused on controllable reasoning, model routing, and long-term memory.

The project is built as a modular system rather than a thin wrapper over LLM APIs.

---

Overview

Most AI backends today are tightly coupled to a single provider and lack control over reasoning and execution.

Ceyona approaches this differently:

- separates decision-making from execution
- routes requests dynamically across models
- introduces a reasoning layer as a first-class component

The goal is to move from “prompt-in → text-out” toward a structured AI system.

---

Core Concepts

1. Model Routing

All model selection is handled by a dedicated decision layer:

- "intent_classifier" — detects user intent
- "task_classifier" — determines task type (chat / coding / reasoning / etc.)
- "model_policy" — maps task → model group
- "model_decision" — final resolution with fallback

This allows switching providers without touching business logic.

---

2. Reasoning Layer

Instead of relying on raw LLM output, the system introduces:

- "reasoning_engine" — builds structured reasoning steps
- "reasoning_verifier" — validates outputs (planned)

This layer is designed for correctness, not just fluency.

---

3. Memory System

Long-term memory is handled separately from the core pipeline:

- external storage (Supabase)
- context injection at runtime
- no hard coupling with model logic

---

4. Clean Architecture

The system follows strict layering:

- api/ — transport (HTTP / Telegram)
- application/ — use cases / orchestration
- core/ — decision + reasoning logic
- infrastructure/ — external integrations (LLMs, DB, APIs)

Dependencies flow inward only.

---

Request Flow

A typical request goes through:

request
→ intent_classifier
→ task_classifier
→ reasoning_engine
→ model_decision
→ llm provider
→ response_formatter

Each step is isolated and replaceable.

---

Setup

git clone <repo>
cd ceyona

pip install -r requirements.txt
cp .env.example .env

Run:

python main.py

---

Configuration

All secrets are loaded via ".env".

Required:

- LLM provider keys
- Supabase credentials

Never commit ".env" or service keys.

---

Project Status

The system is in active development.

Current focus:

- stabilizing reasoning pipeline
- improving model routing accuracy
- integrating verification layer

---

License

Proprietary.

All rights reserved.