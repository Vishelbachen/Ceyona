from typing import Any, Dict


class DeepAgent:
    """
    AI Platform v4.7 — Deep Agent

    RESPONSIBILITY:
    - Handle medium/high complexity tasks
    - Use stronger reasoning-capable model via model_router
    - Support retrieval + structured context usage (if provided)

    STRICT RULES:
    - No orchestration logic
    - No tier decisions
    - No LLM routing decisions
    - No memory policy decisions
    - No retrieval initiation (only usage of injected tools)
    """

    def __init__(self, model_router, prompt_engine):
        self.model_router = model_router
        self.prompt_engine = prompt_engine

    async def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        GENERAL / DEEP execution path.
        """

        text = payload.get("text", "")
        policy = payload.get("policy")
        retrieval_engine = payload.get("retrieval_engine", None)

        # =========================
        # 1. OPTIONAL RETRIEVAL USAGE (IF PROVIDED)
        # =========================
        retrieval_context = {}

        if retrieval_engine and policy and policy.allow_retrieval:
            retrieval_context = await retrieval_engine.search(text)

        # =========================
        # 2. PROMPT PREPARATION
        # =========================
        prompt = self.prompt_engine.build_deep_prompt(
            text=text,
            context=retrieval_context,
            policy=policy,
        )

        # =========================
        # 3. MODEL EXECUTION (GENERAL MODE)
        # =========================
        response = await self.model_router.generate(
            mode="GENERAL",
            prompt=prompt,
            context=retrieval_context,
        )

        return {
            "agent": "deep",
            "output": response,
            "mode": "GENERAL",
            "retrieval_used": bool(retrieval_context),
        }