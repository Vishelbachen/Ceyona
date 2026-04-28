from typing import Any, Dict, List, Optional


class PromptEngine:
    """
    AI Platform v4.7 — Prompt Engine

    RESPONSIBILITY:
    - Format input data into LLM-ready prompts
    - Provide consistent prompt templates per agent type
    - Normalize context into structured messages

    STRICT RULES:
    - No reasoning logic
    - No model selection
    - No routing decisions
    - No retrieval execution
    - No memory interpretation
    """

    # =========================
    # FAST PROMPT
    # =========================
    def build_fast_prompt(self, text: str) -> str:
        return f"""
You are a fast-response assistant.
Provide a short, direct answer.

INPUT:
{text}
""".strip()

    # =========================
    # DEEP PROMPT
    # =========================
    def build_deep_prompt(
        self,
        text: str,
        context: Dict[str, Any],
        policy: Optional[Any] = None,
    ) -> str:

        context_block = self._format_context(context)

        return f"""
You are a reasoning-capable assistant.

Use provided context if relevant.

CONTEXT:
{context_block}

INPUT:
{text}
""".strip()

    # =========================
    # CREATIVE PROMPT
    # =========================
    def build_creative_prompt(
        self,
        text: str,
        policy: Optional[Any] = None,
    ) -> str:

        return f"""
You are a creative generation model.

Generate high-quality, original output.

INPUT:
{text}
""".strip()

    # =========================
    # CONTEXT FORMATTER
    # =========================
    def _format_context(self, context: Dict[str, Any]) -> str:
        """
        Deterministic serialization only.
        """

        if not context:
            return "EMPTY"

        return "\n".join(
            f"{key}: {value}"
            for key, value in context.items()
        )