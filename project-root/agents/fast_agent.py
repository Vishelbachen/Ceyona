from typing import Any, Dict


class FastAgent:
    """
    AI Platform v4.7 — Fast Agent

    RESPONSIBILITY:
    - Handle low-latency simple tasks
    - Use lightweight model via model_router
    - Return fast structured response

    STRICT RULES:
    - No reasoning
    - No orchestration
    - No retrieval logic
    - No memory decisions
    - No agent coordination
    """

    def __init__(self, model_router, prompt_engine):
        self.model_router = model_router
        self.prompt_engine = prompt_engine

    async def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fast execution path.
        """

        text = payload.get("text", "")

        # =========================
        # PROMPT PREPARATION (NO LOGIC)
        # =========================
        prompt = self.prompt_engine.build_fast_prompt(text)

        # =========================
        # MODEL EXECUTION
        # =========================
        response = await self.model_router.generate(
            mode="FAST",
            prompt=prompt,
            context={}
        )

        return {
            "agent": "fast",
            "output": response,
            "mode": "FAST",
        }