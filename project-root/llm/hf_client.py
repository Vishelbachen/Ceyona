from __future__ import annotations

from typing import List, Dict, Any, Optional

from huggingface_hub import InferenceClient

from app.settings import Settings


# =========================
# HF CLIENT
# =========================
class HFClient:
    """
    ROLE:
    - low-level wrapper over HuggingFace Inference API

    STRICT RULES:
    - no routing logic
    - no prompt building
    - no retries
    - no fallback logic
    - no business interpretation
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = InferenceClient(
            token=self._settings.HF_TOKEN
        )

    # =========================
    # CHAT COMPLETION (TEXT MODELS)
    # =========================
    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> str:

        response = self._client.chat_completion(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return response.choices[0].message["content"]

    # =========================
    # TEXT GENERATION (RAW MODE)
    # =========================
    def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> str:

        response = self._client.text_generation(
            model=model,
            prompt=prompt,
            max_new_tokens=max_tokens,
            temperature=temperature,
        )

        return response

    # =========================
    # RAW RESPONSE (DEBUG / OBSERVABILITY)
    # =========================
    def chat_raw(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:

        response = self._client.chat_completion(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return response