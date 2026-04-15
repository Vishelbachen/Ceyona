import logging
from typing import Dict, Any, Optional

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

            logger.info(f"[Solver] Prompt built successfully")

            response = await self._generate_with_retry(prompt, route)

            response = self._validate_response(response)

            return response

        except Exception as e:
            logger.exception(f"[Solver] Critical failure: {e}")
            return self._fallback_response(text)

    def _build_prompt(
        self,
        text: str,
        context: Dict[str, Any],
        reasoning: Dict[str, Any]
    ) -> str:

        try:
            return self.prompt_builder.build(text, context, reasoning)

        except Exception as e:
            logger.warning(f"[Solver] PromptBuilder failed: {e}")

            return (
                f"User input: {text}\n"
                f"Context: {context}\n"
                f"Reasoning: {reasoning}"
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def _generate_with_retry(self, prompt: str, route: Dict[str, Any]) -> str:

        if not route:
            route = {"type": "general"}

        result = await self.selector.generate(prompt, route)

        if not result or not isinstance(result, str):
            raise ValueError("Invalid or empty model response")

        return result

    def _validate_response(self, response: str) -> str:

        if not isinstance(response, str):
            return "Ceyona AI error: invalid response type"

        cleaned = response.strip()

        if len(cleaned) < 3:
            return "Ceyona AI: response too short, retry later."

        return cleaned

    def _fallback_response(self, text: str) -> str:

        return (
            "Ceyona AI encountered a system-level issue.\n"
            "Please try again.\n\n"
            f"Input: {text}"
        )