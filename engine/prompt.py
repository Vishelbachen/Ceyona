class PromptBuilder:
    def build(self, text, context, reasoning):

        domain = reasoning.get("domain", "general")
        route_type = reasoning.get("type", "general")

        # =========================
        # MATH MODE (VERY STRICT)
        # =========================
        if domain == "math":
            return f"""
You are a world-class mathematician and theoretical scientist.

RULES:
- Solve step by step with full logical derivation
- Use formal mathematical notation
- Do NOT chat or add filler phrases
- No emojis
- No conversational tone
- Provide final answer clearly

TASK:
{text}
"""

        # =========================
        # API TOOL MODE
        # =========================
        if route_type in ["weather", "maps", "search"]:
            return f"""
You are a precise API assistant.

RULES:
- Return only factual structured response
- No conversation
- No greetings
- Be minimal and accurate

TASK:
{text}
"""

        # =========================
        # GENERAL LLM MODE
        # =========================
        return f"""
You are a helpful AI assistant.

Context:
{context}

Reasoning:
{reasoning}

User:
{text}

Provide a clear, useful answer.
"""