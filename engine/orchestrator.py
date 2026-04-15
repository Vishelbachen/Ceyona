from engine.router import Router
from engine.reasoning import ReasoningEngine
from engine.selfcorrection import SelfCorrection
from engine.score import ScoreEngine

from memory.memoryintelligence import MemoryIntelligence

from ai.selector import ModelSelector


class Orchestrator:
    def __init__(self):
        self.router = Router()
        self.reasoning = ReasoningEngine()
        self.corrector = SelfCorrection()
        self.scorer = ScoreEngine()

        self.memory = MemoryIntelligence()
        self.selector = ModelSelector()

    async def handle(self, user_input: str, user_id: str, context: dict = None):
        context = context or {}

        # 1. Memory retrieval (semantic + history)
        memory_context = await self.memory.retrieve(user_id, user_input)

        # 2. Routing
        route = self.router.route(user_input, context)

        # 3. Model selection (smart)
        model = self.selector.select(route, user_input, context)

        # 4. Reasoning pipeline
        reasoning_output = await self.reasoning.process(
            input_text=user_input,
            memory=memory_context,
            model=model,
            route=route
        )

        # 5. Self-correction (only if needed)
        corrected_output = await self.corrector.correct(
            input_text=user_input,
            output=reasoning_output,
            model=model
        )

        # 6. Scoring
        score = self.scorer.evaluate(corrected_output)

        # 7. Save memory
        await self.memory.store(
            user_id=user_id,
            user_input=user_input,
            response=corrected_output,
            score=score
        )

        return {
            "response": corrected_output,
            "score": score,
            "route": route,
            "model": model.__class__.__name__
        }