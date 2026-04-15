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
            prompt = self._build_prompt(text, context, reasoning, route)

            logger.info(f"[Solver] route={route} prompt_ready=True")

            response = await self._generate_with_retry(prompt, route)

            return self._validate_response(response)

        except Exception as e:
            logger.exception(f"[Solver] FAILURE: {e}")
            return self._fallback_response(text)

    def _build_prompt(self, text, context, reasoning, route):
        try:
            return self.prompt_builder.build(text, context, reasoning)
        except Exception as e:
            logger.warning(f"[Solver] PromptBuilder failed: {e}")

            return f"""
User: {text}
Context: {context}
Reasoning: {reasoning}
Route: {route}
"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def _generate_with_retry(self, prompt: str, route: Dict[str, Any]):

        result = await self.selector.generate(prompt, route)

        if not result or not isinstance(result, str):
            raise ValueError("Empty or invalid model output")

        return result

    def _validate_response(self, response: str) -> str:
        if not response:
            return "AI error: empty response"

        cleaned = response.strip()

        if len(cleaned) < 2:
            return "AI error: response too short"

        return cleaned

    def _fallback_response(self, text: str) -> str:
        return (
            "AI system temporary error.\n"
            "Please retry.\n\n"
            f"Input: {text}"
        )