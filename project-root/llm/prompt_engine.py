from __future__ import annotations

from typing import List, Dict, Any, Optional


# =========================
# PROMPT ENGINE
# =========================
class PromptEngine:
    """
    ROLE:
    - deterministic prompt construction
    - assemble structured messages for LLMs

    STRICT RULES:
    - no reasoning
    - no model selection
    - no memory access logic
    - no decision making
    """

    # =========================
    # SYSTEM MESSAGE WRAPPER
    # =========================
    def build_system(self, content: str) -> Dict[str, str]:
        return {
            "role": "system",
            "content": content,
        }

    # =========================
    # USER MESSAGE WRAPPER
    # =========================
    def build_user(self, content: str) -> Dict[str, str]:
        return {
            "role": "user",
            "content": content,
        }

    # =========================
    # ASSISTANT MESSAGE WRAPPER
    # =========================
    def build_assistant(self, content: str) -> Dict[str, str]:
        return {
            "role": "assistant",
            "content": content,
        }

    # =========================
    # BASE PROMPT ASSEMBLY
    # =========================
    def build_messages(
        self,
        system_prompt: Optional[str],
        user_input: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:

        messages: List[Dict[str, str]] = []

        # system
        if system_prompt:
            messages.append(self.build_system(system_prompt))

        # history (already formatted messages)
        if history:
            messages.extend(history)

        # current user input
        messages.append(self.build_user(user_input))

        return messages

    # =========================
    # LIGHTWEIGHT TEMPLATE HOOK
    # =========================
    def inject_context(
        self,
        base_prompt: str,
        context: Dict[str, Any],
    ) -> str:

        """
        Simple string injection (NO logic).
        """

        formatted_context = "\n".join(
            f"{k}: {v}" for k, v in context.items()
        )

        return f"{base_prompt}\n\nContext:\n{formatted_context}"