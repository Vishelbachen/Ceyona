import logging
from typing import Dict, Any

from engine.prompt import PromptBuilder
from ai.selector import AISelector
from config.settings import Settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class Solver:
    def __init__(self):
        self.settings = Settings()
        self.prompt_builder = PromptBuilder()
        self.selector = AISelector(self.settings)

    async def solve(
        self,
        text: str,
        context: Dict[str, Any],
        reasoning: Dict[str, Any],
        route: Dict[str, Any]
    ) -> str:

        prompt = self._safe_prompt(text, context, reasoning)

        try:
            response = await self._generate_with_retry(prompt, route)

            if not response:
                raise ValueError("Empty response from model")

            return self._clean(response)

        except Exception as e:
            logger.exception(f"[Solver ERROR]: {e}")

            # 🔥 FALLBACK LEVEL 1 (прямой вызов без routing)
            try:
                logger.warning("[Solver] Fallback direct call")

                response = await self.selector.generate(prompt, {"type": "general"})

                if response:
                    return self._clean(response)

            except Exception as e2:
                logger.exception(f"[Solver Fallback ERROR]: {e2}")

            # 🔥 FALLBACK LEVEL 2 (жёсткий)
            return self._fallback(text)

    def _safe_prompt(self, text, context, reasoning):
        try:
            return self.prompt_builder.build(text, context, reasoning)
        except Exception as e:
            logger.warning(f"[Prompt ERROR]: {e}")

            return f"User input: {text}"

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4))
    async def _generate_with_retry(self, prompt: str, route: Dict[str, Any]) -> str:
        if not route:
            route = {"type": "general"}

        result = await self.selector.generate(prompt, route)

        if not result or not isinstance(result, str):
            raise ValueError("Invalid model response")

        return result

    def _clean(self, response: str) -> str:
        return response.strip()

    def _fallback(self, text: str) -> str:
        return (
            "Ceyona AI temporary failure.\n"
            "Retry in a moment.\n\n"
            f"Input: {text}"
        )