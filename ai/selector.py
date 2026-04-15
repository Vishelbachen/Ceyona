import asyncio
import logging

from ai.groq import GroqClient
from ai.openai import OpenAIClient
from ai.mistral import MistralClient
from ai.gemini import GeminiClient

logger = logging.getLogger(__name__)


class AISelector:
    """
    PRO MAX AI ROUTER
    - safe imports assumed
    - graceful fallback
    - no debug leakage
    - production stable routing
    """

    def __init__(self, settings):
        self.settings = settings

        # =========================
        # SAFE INIT (NO CRASH MODE)
        # =========================
        self.groq = self._safe_init(GroqClient, settings, "groq")
        self.openai = self._safe_init(OpenAIClient, settings, "openai")
        self.mistral = self._safe_init(MistralClient, settings, "mistral")
        self.gemini = self._safe_init(GeminiClient, settings, "gemini")

        self.models = {
            "groq": self.groq,
            "openai": self.openai,
            "mistral": self.mistral,
            "gemini": self.gemini,
        }

    def _safe_init(self, cls, settings, name: str):
        """
        Prevent system crash if one provider fails to init
        """
        try:
            return cls(settings)
        except Exception as e:
            logger.warning(f"[AISelector] {name} init failed: {e}")
            return None

    # =========================
    # ROUTING LOGIC
    # =========================
    def select_order(self, model_type: str):
        if model_type == "fast":
            return [self.groq, self.mistral, self.openai]

        if model_type == "analysis":
            return [self.gemini, self.openai, self.mistral]

        if model_type == "coding":
            return [self.openai, self.gemini, self.mistral]

        return [self.groq, self.openai, self.mistral, self.gemini]

    # =========================
    # MAIN GENERATION PIPELINE
    # =========================
    async def generate(self, prompt: str, route: dict) -> str:
        model_type = (route or {}).get("type", "general")
        order = self.select_order(model_type)

        last_error = None

        for model in order:
            if model is None:
                continue

            try:
                result = await model.generate(prompt)

                if isinstance(result, str):
                    cleaned = result.strip()

                    if cleaned:
                        return self._clean_output(cleaned)

            except Exception as e:
                last_error = e
                logger.warning(f"[AISelector] model failed: {e}")
                continue

        # =========================
        # FINAL SAFE FALLBACK
        # =========================
        logger.error(f"[AISelector] ALL MODELS FAILED: {last_error}")

        return self._fallback()

    # =========================
    # CLEAN OUTPUT (ANTI GARBAGE)
    # =========================
    def _clean_output(self, text: str) -> str:
        if not text:
            return ""

        # remove internal system artifacts
        unwanted = [
            "[Ceyona refined output]",
            "[refined output]",
            "Ceyona AI:",
            "[OUTPUT]",
            "[FINAL]"
        ]

        for u in unwanted:
            text = text.replace(u, "")

        return text.strip()

    # =========================
    # SAFE FALLBACK (NO DEBUG LEAK)
    # =========================
    def _fallback(self) -> str:
        return (
            "I'm unable to generate a response right now.\n"
            "Please try again."
        )