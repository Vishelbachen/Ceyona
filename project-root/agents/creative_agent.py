from typing import Any, Dict


class CreativeAgent:
    """
    AI Platform v4.7 — Creative Agent

    RESPONSIBILITY:
    - Handle creative / generative tasks (stories, ideas, text generation)
    - Use HEAVY or creative-capable model via model_router
    - Produce high-variance outputs

    STRICT RULES:
    - No reasoning control
    - No orchestration logic
    - No retrieval decisions
    - No memory policy handling
    - No agent coordination
    """

    def __init__(self, model_router, prompt_engine):
        self.model_router = model_router
        self.prompt_engine = prompt_engine

    async def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creative execution path.
        """

        text = payload.get("text", "")
        policy = payload.get("policy")

        # =========================
        # PROMPT PREPARATION
        # =========================
        prompt = self.prompt_engine.build_creative_prompt(
            text=text,
            policy=policy,
        )

        # =========================
        # MODEL EXECUTION (HEAVY MODE)
        # =========================
        response = await self.model_router.generate(
            mode="HEAVY",
            prompt=prompt,
            context={},
        )

        return {
            "agent": "creative",
            "output": response,
            "mode": "HEAVY",
        }
