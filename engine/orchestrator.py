import logging
from typing import Any

from engine.router import Router
from engine.tools import Tools

from engine.cognitive import Cognitive
from engine.reasoning import Reasoning
from engine.solver import Solver
from engine.score import Scorer
from engine.selfcorrection import SelfCorrection
from engine.selfimprove import SelfImprove
from engine.brain import Brain
from engine.proof import ProofEngine

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

        # ======================
        # CORE
        # ======================
        self.router = Router()
        self.tools = Tools(self.settings)

        # ======================
        # INTELLIGENCE
        # ======================
        self.brain = Brain() if Constants.ENABLE_BRAIN_LAYER else None
        self.cognitive = Cognitive()
        self.reasoning = Reasoning() if Constants.ENABLE_REASONING_LAYER else None

        self.solver = Solver()

        # ======================
        # SELF IMPROVE
        # ======================
        self.scorer = Scorer() if Constants.ENABLE_SELF_CORRECTION else None
        self.corrector = SelfCorrection() if Constants.ENABLE_SELF_CORRECTION else None
        self.improver = SelfImprove() if Constants.ENABLE_SELF_IMPROVE else None

        # ======================
        # PROOF ENGINE
        # ======================
        self.proof = ProofEngine()

        # ======================
        # MEMORY SAFE INIT
        # ======================
        self.memory_enabled = False
        self.memory_intelligence = None
        self.db = None

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

        # ======================
        # ACCESS SAFE INIT
        # ======================
        try:
            self.access = AccessControl(self.db)
        except Exception:
            self.access = None

    # =========================================================
    # MAIN PIPELINE
    # =========================================================
    async def process(self, user_id: int, text: str) -> str:
        try:
            text = (text or "").strip()
            if not text:
                return "Empty input."

            uid = str(user_id)

            # ======================
            # ACCESS CONTROL
            # ======================
            if self.access:
                try:
                    allowed, msg = self.access.require_access(uid)
                    if not allowed:
                        return msg
                except Exception:
                    logger.warning("[ACCESS FAILSAFE]")

            # ======================
            # ROUTING
            # ======================
            route = self.router.route(text)
            tool_type = route.get("type") or "llm"
            confidence = self._safe_float(route.get("confidence"))

            # ======================
            # TOOL FAST PATH
            # ======================
            if tool_type in ("weather", "maps", "search") and confidence >= 0.65:
                try:
                    tool_result = await self.tools.execute(route, text)

                    if self._valid_tool(tool_result):
                        return self._format_tool(tool_result)

                except Exception as e:
                    logger.warning(f"[TOOL FAILSAFE] {e}")

            # ======================
            # BRAIN
            # ======================
            brain = {"domain": "general"}

            if self.brain:
                try:
                    res = self.brain.analyze(text, route)
                    if isinstance(res, dict):
                        brain = res
                except Exception:
                    logger.warning("[BRAIN FAILSAFE]")

            # ======================
            # MEMORY
            # ======================
            memory = {"recent": [], "semantic": []}

            if self.memory_enabled and self.memory_intelligence:
                try:
                    memory = await self.memory_intelligence.build_context(
                        user_id=uid,
                        text=text
                    )
                except Exception:
                    logger.warning("[MEMORY FAILSAFE]")

            # ======================
            # CONTEXT
            # ======================
            try:
                context = await self.cognitive.build_context(
                    user_id=user_id,
                    text=text,
                    memory=memory,
                    brain=brain
                )
            except Exception:
                context = {
                    "user_id": uid,
                    "input": text,
                    "memory": memory,
                    "brain": brain
                }

            # ======================
            # REASONING
            # ======================
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
                    logger.warning("[REASONING FAILSAFE]")

            # ======================
            # SOLVER
            # ======================
            try:
                response = await self.solver.solve(
                    text=text,
                    context=context,
                    reasoning=reasoning,
                    route=route
                )
            except Exception as e:
                logger.error(f"[SOLVER ERROR] {e}")
                return self._fallback(text)

            response = response or "No response generated."

            # ======================
            # PROOF ENGINE
            # ======================
            try:
                response = self.proof.validate(
                    response,
                    brain.get("domain", "general")
                ) or response
            except Exception:
                pass

            # ======================
            # SELF IMPROVE
            # ======================
            if self.scorer and self.corrector and self.improver:
                try:
                    score = self.scorer.evaluate(response)

                    response = self.corrector.correct(response, score) or response
                    response = self.improver.improve(response, score) or response

                except Exception:
                    logger.warning("[SELF IMPROVE FAILSAFE]")

            # ======================
            # MEMORY SAVE
            # ======================
            if self.memory_enabled and self.memory_intelligence:
                try:
                    await self.memory_intelligence.update_memory(
                        user_id=uid,
                        text=text,
                        response=response
                    )
                except Exception:
                    logger.warning("[MEMORY SAVE FAILSAFE]")

            return str(response)

        except Exception as e:
            logger.exception(f"[ORCHESTRATOR FATAL] {e}")
            return self._fallback(text)

    # =========================================================
    # HELPERS (ANTI-CRASH CORE)
    # =========================================================
    def _safe_float(self, value: Any) -> float:
        try:
            return float(value)
        except Exception:
            return 0.5

    def _valid_tool(self, tool_result: Any) -> bool:
        return (
            isinstance(tool_result, dict)
            and tool_result.get("status") == "success"
            and tool_result.get("data") is not None
        )

    def _format_tool(self, tool_result: dict) -> str:
        try:
            tool = tool_result.get("tool", "tool")
            data = tool_result.get("data", "")

            if isinstance(data, dict):
                data = str(data)

            return f"[{tool.upper()} RESULT]\n{data}"

        except Exception:
            return "[TOOL RESULT]\n<format error>"

    def _fallback(self, text: str) -> str:
        return (
            "Ceyona AI system error occurred.\n"
            "Please retry.\n\n"
            f"Input: {text}"
        )