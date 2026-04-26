from __future__ import annotations

from typing import Optional, List, Dict, Any

from groq import Groq

from app.settings import Settings


# =========================
# GROQ CLIENT
# =========================
class GroqClient:
    """
    ROLE:
    - low-level wrapper over Groq API

    STRICT RULES:
    - no prompt logic
    - no retries
    - no business logic
    - no formatting
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = Groq(api_key=self._settings.GROQ_API_KEY)

    # =========================
    # CHAT COMPLETION
    # =========================
    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:

        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content

    # =========================
    # RAW RESPONSE (OPTIONAL)
    # =========================
    def chat_raw(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:

        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.model_dump()

    # =========================
    # HEALTH CHECK
    # =========================
    def healthcheck(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:
            return False