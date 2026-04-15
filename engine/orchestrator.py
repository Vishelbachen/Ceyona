from engine.router import Router
from engine.reasoning import ReasoningEngine
from engine.selfcorrection import SelfCorrection
from engine.selfimprove import SelfImprove
from engine.score import ScoreEngine

from engine.thread_manager import ThreadManager
from engine.function_calling import FunctionCalling

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

        self.threads = ThreadManager()
        self.functions = FunctionCalling({})

    async def handle(self, user_input: str, user_id: str, thread_id: str = None, context: dict = None):
        context = context or {}

        # 1. Thread handling
        if not thread_id:
            thread_id = self.threads.create_thread(user_id)

        self.threads.add_message(thread_id, "user", user_input)

        # 2. Memory
        memory_context = await self.memory.retrieve(user_id, user_input)

        # 3. Route
        route = self.router.route(user_input, context)

        # 4. Model selection
        model = self.selector.select(route, user_input, context)

        # 5. Reasoning
        reasoning_output = await self.reasoning.process(
            input_text=user_input,
            memory=memory_context,
            model=model,
            route=route
        )

        # 6. Correction
        corrected = await self.corrector.correct(
            user_input,
            reasoning_output,
            model
        )

        # 7. Improve
        score = self.scorer.evaluate(corrected)

        final = await self.improver.improve(
            user_input,
            corrected,
            score,
            model
        )

        # 8. Save memory
        await self.memory.store(user_id, user_input, final, score)

        # 9. Thread save
        self.threads.add_message(thread_id, "assistant", final)

        return {
            "response": final,
            "score": score,
            "route": route,
            "model": model.__class__.__name__,
            "thread_id": thread_id
        }