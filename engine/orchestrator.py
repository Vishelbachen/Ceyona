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
from engine.proofengine import ProofEngine

from memory.supabase_client import SupabaseClient
from memory.memorygraph import MemoryGraph
from memory.memoryintelligence import MemoryIntelligence
from memory.embeddings import Embeddings

from payments.access import AccessControl
from config.settings import Settings
from config.constants import Constants

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self):
        self.settings = Settings()

        self.router = Router()

        self.brain = Brain() if Constants.ENABLE_BRAIN_LAYER else None
        self.cognitive = Cognitive()
        self.reasoning = Reasoning() if Constants.ENABLE_REASONING_LAYER else None
        self.solver = Solver()

        self.scorer = Scorer() if Constants.ENABLE_SELF_CORRECTION else None
        self.corrector = SelfCorrection() if Constants.ENABLE_SELF_CORRECTION else None
        self.improver = SelfImprove() if Constants.ENABLE_SELF_IMPROVE else None

        # 🧠 NEW: PROOF ENGINE
        self.proof = ProofEngine()

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
            logger.warning(f"[MEMORY DISABLED] {e}")
            self.memory_intelligence = None
            self.memory_enabled = False

        try:
            self.access = AccessControl(self.db)
        except Exception:
            self.access = None

    async def process(self, user_id: int, text: str) -> str:
        try:
            text = (text or "").strip()
            if not text:
                return "Empty input."

            user_id_str = str(user_id)

            # ACCESS
            if self.access:
                try:
                    allowed, msg = self.access.require_access(user_id_str)
                    if not allowed:
                        return msg
                except Exception:
                    pass

            # ROUTE
            route = self.router.route(text)

            # BRAIN SAFE
            brain = {"domain": "general"}
            if self.brain:
                try:
                    result = self.brain.analyze(text, route)
                    if isinstance(result, dict):
                        brain = result
                except Exception:
                    pass

            # MEMORY
            memory_context = {"recent": [], "semantic": []}

            if self.memory_enabled:
                try:
                    memory_context = await self.memory_intelligence.build_context(
                        user_id=user_id_str,
                        text=text
                    )
                except Exception:
                    pass

            # CONTEXT
            context = await self.cognitive.build_context(
                user_id=user_id,
                text=text,
                memory=memory_context,
                brain=brain
            )

            # REASONING
            reasoning = {}

            if self.reasoning:
                try:
                    reasoning = await self.reasoning.analyze(
                        text=text,
                        context=context,
                        route=route,
                        brain=brain
                    )
                except Exception:
                    pass

            # SOLVER
            try:
                response = await self.solver.solve(
                    text=text,
                    context=context,
                    reasoning=reasoning,
                    route=route
                )
            except Exception:
                return self._fallback(text)

            if not response:
                response = "No response generated."

            # BRAIN VERIFY
            if self.brain:
                try:
                    response = self.brain.verify(
                        response,
                        brain.get("domain", "general")
                    )
                except Exception:
                    pass

            # 🧠 PROOF ENGINE (NEW LAYER)
            try:
                response = self.proof.validate(
                    response,
                    brain.get("domain", "general")
                )
            except Exception:
                pass

            # SCORE + IMPROVE
            if self.scorer and self.corrector and self.improver:
                try:
                    score = self.scorer.evaluate(response)
                    response = self.corrector.correct(response, score)
                    response = self.improver.improve(response, score)
                except Exception:
                    pass

            # MEMORY SAVE
            if self.memory_enabled:
                try:
                    await self.memory_intelligence.update_memory(
                        user_id=user_id_str,
                        text=text,
                        response=response
                    )
                except Exception:
                    pass

            return str(response)

        except Exception as e:
            logger.exception(f"[ORCHESTRATOR FATAL] {e}")
            return self._fallback(text)

    def _fallback(self, text: str) -> str:
        return (
            "Ceyona AI system error occurred.\n"
            "Please retry.\n\n"
            f"Input: {text}"
        )