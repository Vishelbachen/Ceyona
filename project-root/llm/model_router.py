from typing import Any, Dict, Optional

from llm.groq_client import GroqClient
from llm.hf_client import HFClient


class ModelRouter:
    """
    AI Platform v4.7 — Model Router

    RESPONSIBILITY:
    - Select appropriate LLM provider (Groq / HF)
    - Select model based on execution mode (FAST / GENERAL / HEAVY)
    - Route request to correct client

    STRICT RULES:
    - No prompt engineering
    - No reasoning logic
    - No retrieval / memory access
    - No orchestration decisions
    - No business logic
    """

    def __init__(self, groq_client: GroqClient, hf_client: HFClient):
        self.groq = groq_client
        self.hf = hf_client

        # deterministic model mapping (single source of truth)
        self.model_map = {
            "FAST": {
                "provider": "groq",
                "model": "llama-3.1-8b-instant",
            },
            "GENERAL": {
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
            },
            "HEAVY": {
                "provider": "hf",
                "model": "gpt-oss-120b",
            },
        }

    async def generate(
        self,
        mode: str,
        prompt: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Routes request to correct model provider.
        """

        if mode not in self.model_map:
            raise ValueError(f"Invalid mode: {mode}")

        config = self.model_map[mode]

        provider = config["provider"]
        model = config["model"]

        messages = self._build_messages(prompt, context or {})

        # =========================
        # ROUTING ONLY (NO LOGIC)
        # =========================

        if provider == "groq":
            return await self.groq.chat_completion(
                model=model,
                messages=messages,
            )

        if provider == "hf":
            return await self.hf.chat_completion(
                model=model,
                messages=messages,
            )

        raise ValueError(f"Unknown provider: {provider}")

    def _build_messages(self, prompt: Any, context: Dict[str, Any]):
        """
        Minimal formatting only (no prompt engineering logic).
        """

        return [
            {
                "role": "user",
                "content": str(prompt),
            }
        ]