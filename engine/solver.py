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
        """
        Main AI execution pipeline:
        - build prompt
        - select model
        - generate response
        - validate output
        """

        prompt = self._build_prompt(text, context, reasoning)

        try:
            response = await self._generate_with_retry(prompt, route)

            validated = self._validate_response(response)

            return validated

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
            logger.warning(f"[Solver] Prompt build failed: {e}")
            return f"User input: {text}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _generate_with_retry(self, prompt: str, route: Dict[str, Any]) -> str:
        """
        Retry layer for unstable APIs
        """
        result = await self.selector.generate(prompt, route)

        if not result or not result.strip():
            raise ValueError("Empty response from model")

        return result

    def _validate_response(self, response: str) -> str:
        """
        Output validation layer
        """

        if not isinstance(response, str):
            return "Ceyona AI error: invalid response type"

        cleaned = response.strip()

        if len(cleaned) < 3:
            return "Ceyona AI: response too short, retry later."

        return cleaned

    def _fallback_response(self, text: str) -> str:
        """
        Final safety layer if everything fails
        """
        return (
            "Ceyona AI encountered an issue processing your request.\n"
            "Please try again.\n\n"
            f"Input: {text}"
        )