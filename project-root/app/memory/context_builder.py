# app/memory/context_builder.py

from typing import List


class ContextBuilder:
    """
    Builds LLM context from session history + current input
    """

    @staticmethod
    def build(history: List[str], current_message: str) -> str:
        if not history:
            return current_message

        formatted_history = "\n".join(history)
        return f"""Conversation history:
{formatted_history}

User:
{current_message}
"""