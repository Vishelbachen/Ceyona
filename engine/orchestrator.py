import logging
from typing import Dict, Any

from engine.router import Router
from engine.cognitive import Cognitive
from engine.reasoning import Reasoning
from engine.solver import Solver
from engine.score import Scorer
from engine.selfcorrection import SelfCorrection
from engine.selfimprove import SelfImprove

from memory.supabase_client import SupabaseClient
from memory.memorygraph import MemoryGraph
from memory.memoryintelligence import MemoryIntelligence
from memory.embeddings import Embeddings

from config.settings import Settings


logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self):
        self.settings = Settings()

        # CORE ENGINE
        self.router = Router()
        self.cognitive = Cognitive()
        self.reasoning = Reasoning()
        self.solver = Solver()
        self.scorer = Scorer()
        self.corrector = SelfCorrection()
        self.improver = SelfImprove()

        # MEMORY LAYER (CRITICAL)
        self.db = SupabaseClient(self.settings)
        self.embeddings = Embeddings(self.settings)
        self.memory_graph = MemoryGraph(self.db, self.embeddings)
        self.memory_intelligence = MemoryIntelligence(
            self.memory_graph,
            self.embeddings
        )

    async def process(self, user_id: int, text: str) -> str:
        """
        Full AI pipeline:
        router → memory → cognitive → reasoning → solver → score → correction → improve → memory save
        """

        try:
            # 1. ROUTING (intent)
            route = self.router.route(text)

            # 2. MEMORY CONTEXT (NEW 🔥)
            memory_context = await self.memory_intelligence.build_context(
                user_id=str(user_id),
                text=text
            )

            # 3. COGNITIVE (merge context)
            context = await self.cognitive.build_context(
                user_id=user_id,
                text=text,
                memory=memory_context
            )

            # 4. REASONING
            reasoning = await self.reasoning.analyze(
                text,
                context,
                route
            )

            # 5. SOLVER (AI)
            response = await self.solver.solve(
                text,
                context,
                reasoning,
                route
            )

            # 6. SCORE
            score = self.scorer.evaluate(response)

            # 7. SELF-CORRECTION
            response = self.corrector.correct(response, score)

            # 8. SELF-IMPROVEMENT
            response = self.improver.improve(response, score)

            # 9. SAVE MEMORY (CRITICAL 🔥)
            await self.memory_intelligence.update_memory(
                user_id=str(user_id),
                text=text,
                response=response
            )

            return response

        except Exception as e:
            logger.exception(f"[Orchestrator] Critical failure: {e}")
            return self._fallback(text)

    def _fallback(self, text: str) -> str:
        return (
            "Ceyona AI encountered a system error.\n"
            "Please try again.\n\n"
            f"Input: {text}"
        )