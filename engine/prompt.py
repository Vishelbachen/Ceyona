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

        try:
            prompt = self._build_prompt(text, context, reasoning)

            response = await self._generate_with_retry(prompt, route)

            return self._clean(response)

        except Exception as e:
            logger.exception(f"[Solver] Failed: {e}")
            return self._fallback(text)

    def _build_prompt(self, text, context, reasoning):
        return self.prompt_builder.build(text, context, reasoning)

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4))
    async def _generate_with_retry(self, prompt: str, route: Dict[str, Any]) -> str:
        result = await self.selector.generate(prompt, route)

        if not result:
            raise ValueError("Empty model output")

        return result

    def _clean(self, response: str) -> str:
        return response.strip()

    def _fallback(self, text: str) -> str:
        return (
            "System temporarily unavailable.\n"
            f"Input: {text}"
        )