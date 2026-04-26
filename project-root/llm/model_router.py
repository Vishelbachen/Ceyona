from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

from llm.groq_client import GroqClient
from llm.hf_client import HFClient


# =========================
# 🧠 MODEL MODES
# =========================
ModelMode = Literal["fast", "general", "heavy", "safety"]


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    mode: ModelMode
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model_used: str
    raw: Any


# =========================
# 🧠 MODEL ROUTER
# =========================
class ModelRouter:
    """
    Deterministic LLM routing layer.

    RULES:
    - NO reasoning
    - NO intent classification
    - NO policy decisions
    - ONLY model selection + execution
    """

    def __init__(
        self,
        groq: GroqClient,
        hf: HFClient,
    ):
        self.groq = groq
        self.hf = hf

    # =========================
    # 🚀 MAIN ENTRY
    # =========================
    async def route(self, prompt: str, mode: ModelMode) -> LLMResponse:

        if mode == "fast":
            return await self._fast(prompt)

        if mode == "general":
            return await self._general(prompt)

        if mode == "heavy":
            return await self._heavy(prompt)

        if mode == "safety":
            return await self._safety(prompt)

        # fallback guard (never should happen)
        return await self._fast(prompt)

    # =========================
    # 🟢 FAST LAYER
    # =========================
    async def _fast(self, prompt: str) -> LLMResponse:
        result = await self.groq.complete(
            model="llama-3.1-8b-instant",
            prompt=prompt,
        )

        return LLMResponse(
            text=result,
            model_used="llama-3.1-8b-instant",
            raw=result,
        )

    # =========================
    # 🔵 GENERAL LAYER
    # =========================
    async def _general(self, prompt: str) -> LLMResponse:
        result = await self.groq.complete(
            model="llama-3.3-70b-versatile",
            prompt=prompt,
        )

        return LLMResponse(
            text=result,
            model_used="llama-3.3-70b-versatile",
            raw=result,
        )

    # =========================
    # 🔴 HEAVY LAYER
    # =========================
    async def _heavy(self, prompt: str) -> LLMResponse:
        result = await self.groq.complete(
            model="llama-4-scout-17b-16e-instruct",
            prompt=prompt,
        )

        return LLMResponse(
            text=result,
            model_used="llama-4-scout-17b-16e-instruct",
            raw=result,
        )

    # =========================
    # 🛡 SAFETY LAYER
    # =========================
    async def _safety(self, prompt: str) -> LLMResponse:
        result = await self.hf.complete(
            model="gpt-oss-safeguard-20b",
            prompt=prompt,
        )

        return LLMResponse(
            text=result,
            model_used="gpt-oss-safeguard-20b",
            raw=result,
        )