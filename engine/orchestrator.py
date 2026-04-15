import logging
from typing import Dict, Any

from engine.router import Router
from engine.cognitive import Cognitive
from engine.reasoning import Reasoning
from engine.solver import Solver
from engine.score import Scorer
from engine.selfcorrection import SelfCorrection
from engine.selfimprove import SelfImprove
from engine.brain import Brain

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

        self.router = Router()
        self.brain = Brain()
        self.cognitive = Cognitive()
        self.reasoning = Reasoning()
        self.solver = Solver()
        self.scorer = Scorer()
        self.corrector = SelfCorrection()
        self.improver = SelfImprove()

        # MEMORY SAFE INIT
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
            logger.warning(f"[Memory INIT FAILED] SAFE MODE: {e}")
            self.memory_intelligence = None
            self.memory_enabled = False

        # ACCESS CONTROL
        try:
            self.access = AccessControl(self.db)
        except Exception as e:
            logger.warning(f"[AccessControl INIT FAILED] BYPASS MODE: {e}")
            self.access = None

    async def process(self, user_id: int, text: str) -> str:
        try:
            user_id_str = str(user_id)
            text = (text or "").strip()

            # ACCESS
            if self.access:
                allowed, msg = self.access.require_access(user_id_str)
                if not allowed:
                    return msg

            # ROUTE
            route = self.router.route(text)

            # BRAIN
            brain = self.brain.analyze(text, route)

            # MEMORY
            memory_context = {"recent": [], "semantic": []}
            if self.memory_enabled:
                memory_context = await self.memory_intelligence.build_context(
                    user_id=user_id_str,
                    text=text
                )

            # CONTEXT
            context = await self.cognitive.build_context(
                user_id=user_id,
                text=text,
                memory=memory_context,
                brain=brain
            )

            # REASONING
            reasoning = await self.reasoning.analyze(
                text=text,
                context=context,
                route=route,
                brain=brain
            )

            # SOLVER
            response = await self.solver.solve(
                text=text,
                context=context,
                reasoning=reasoning,
                route=route
            )

            # VERIFY
            response = self.brain.verify(response, brain["domain"])

            # MEMORY SAVE
            if self.memory_enabled:
                await self.memory_intelligence.update_memory(
                    user_id=user_id_str,
                    text=text,
                    response=response
                )

            return response

        except Exception as e:
            logger.exception(f"[Orchestrator] Fatal: {e}")
            return self._fallback(text)

    def _fallback(self, text: str) -> str:
        return (
            "Ceyona AI system error occurred.\n"
            "Please retry.\n\n"
            f"Input: {text}"
        )