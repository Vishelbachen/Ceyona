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

from payments.access import AccessControl

from config.settings import Settings

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self):
        self.settings = Settings()

        # ======================
        # CORE ENGINE
        # ======================
        self.router = Router()
        self.cognitive = Cognitive()
        self.reasoning = Reasoning()
        self.solver = Solver()
        self.scorer = Scorer()
        self.corrector = SelfCorrection()
        self.improver = SelfImprove()

        # ======================
        # MEMORY LAYER (SAFE INIT)
        # ======================
        try:
            self.db = SupabaseClient(self.settings)
            self.embeddings = Embeddings(self.settings)
            self.memory_graph = MemoryGraph(self.db, self.embeddings)
            self.memory_intelligence = MemoryIntelligence(
                self.memory_graph,
                self.embeddings
            )
            self.memory_enabled = True
        except Exception as e:
            logger.warning(f"[Memory INIT FAILED] running in SAFE MODE: {e}")
            self.memory_intelligence = None
            self.memory_enabled = False

        # ======================
        # ACCESS CONTROL
        # ======================
        try:
            self.access = AccessControl(self.db)
        except Exception as e:
            logger.warning(f"[AccessControl INIT FAILED] bypass mode: {e}")
            self.access = None

    async def process(self, user_id: int, text: str) -> str:
        try:
            user_id_str = str(user_id)

            # ======================
            # 0. ACCESS LAYER (SAFE)
            # ======================
            if self.access:
                try:
                    allowed, msg = self.access.require_access(user_id_str)
                    if not allowed:
                        return msg
                except Exception as e:
                    logger.warning(f"[AccessControl] bypass due to error: {e}")

            # ======================
            # 1. ROUTING
            # ======================
            route = self.router.route(text or "")

            # ======================
            # 2. MEMORY RETRIEVAL (SAFE MODE)
            # ======================
            memory_context = {"recent": [], "semantic": []}

            if self.memory_enabled:
                try:
                    memory_context = await self.memory_intelligence.build_context(
                        user_id=user_id_str,
                        text=text
                    )
                except Exception as e:
                    logger.warning(f"[Memory Retrieve FAILED]: {e}")

            # ======================
            # 3. COGNITIVE
            # ======================
            context = await self.cognitive.build_context(
                user_id=user_id,
                text=text,
                memory=memory_context
            )

            # ======================
            # 4. REASONING
            # ======================
            reasoning = await self.reasoning.analyze(
                text,
                context,
                route
            )

            # ======================
            # 5. SOLVER
            # ======================
            response = await self.solver.solve(
                text,
                context,
                reasoning,
                route
            )

            # ======================
            # 6. SCORE
            # ======================
            score = self.scorer.evaluate(response)

            # ======================
            # 7. SELF CORRECTION
            # ======================
            response = self.corrector.correct(response, score)

            # ======================
            # 8. SELF IMPROVEMENT
            # ======================
            response = self.improver.improve(response, score)

            # ======================
            # 9. MEMORY SAVE (SAFE)
            # ======================
            if self.memory_enabled:
                try:
                    await self.memory_intelligence.update_memory(
                        user_id=user_id_str,
                        text=text,
                        response=response
                    )
                except Exception as e:
                    logger.warning(f"[Memory Save FAILED]: {e}")

            return response

        except Exception as e:
            logger.exception(f"[Orchestrator FATAL]: {e}")
            return self._fallback(text)

    def _fallback(self, text: str) -> str:
        return (
            "Ceyona AI system error occurred.\n"
            "Please retry.\n\n"
            f"Input: {text}"
        )