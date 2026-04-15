from engine.router import Router
from engine.reasoning import ReasoningEngine
from engine.selfcorrection import SelfCorrection
from engine.selfimprove import SelfImprove
from engine.score import ScoreEngine

from memory.memoryintelligence import MemoryIntelligence

from ai.selector import ModelSelector


class Orchestrator:
    def __init__(self):
        self.router = Router()
        self.reasoning = ReasoningEngine()
        self.corrector = SelfCorrection()
        self.improver = SelfImprove()
        self.scorer = ScoreEngine()

        self.memory = MemoryIntelligence()
        self.selector = ModelSelector()

    async def handle(self, user_input: str, user_id: str, context: dict = None):
        context = context or {}

        # 1. Memory
        memory_context = await self.memory.retrieve(user_id, user_input)

        # 2. Route
        route = self.router.route(user_input, context)

        # 3. Model
        model = self.selector.select(route, user_input, context)

        # 4. Reasoning
        reasoning_output = await self.reasoning.process(
            input_text=user_input,
            memory=memory_context,
            model=model,
            route=route
        )

        # 5. Correction
        corrected = await self.corrector.correct(
            user_input,
            reasoning_output,
            model
        )

        # 6. Score
        score = self.scorer.evaluate(corrected)

        # 7. Improve if weak
        improved = await self.improver.improve(
            user_input,
            corrected,
            score,
            model
        )

        # 8. Store memory
        await self.memory.store(
            user_id=user_id,
            user_input=user_input,
            response=improved,
            score=score
        )

        return {
            "response": improved,
            "score": score,
            "route": route,
            "model": model.__class__.__name__
        }