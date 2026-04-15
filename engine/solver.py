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
            response = await self._generate(prompt, route)
            return self._clean(response)

        except Exception as e:
            logger.exception(f"[Solver ERROR]: {e}")

            try:
                fallback = await self.selector.generate(
                    prompt,
                    {"type": "general"}
                )
                return self._clean(fallback)
            except Exception:
                return self._fallback(text)

    def _safe_prompt(self, text, context, reasoning):
        try:
            return self.prompt_builder.build(text, context, reasoning)
        except Exception:
            return f"User input: {text}"

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=3))
    async def _generate(self, prompt: str, route: Dict[str, Any]) -> str:
        route = route or {"type": "general"}

        result = await self.selector.generate(prompt, route)

        if not isinstance(result, str) or not result.strip():
            raise ValueError("Invalid model output")

        return result

    def _clean(self, response: str) -> str:
        if not response:
            return "No response generated."

        return (
            response
            .replace("[Ceyona refined output]", "")
            .replace("[refined output]", "")
            .replace("```", "")
            .strip()
        )

    def _fallback(self, text: str) -> str:
        return (
            "Ceyona AI temporary failure.\n"
            "Please retry.\n\n"
            f"Input: {text}"
        )