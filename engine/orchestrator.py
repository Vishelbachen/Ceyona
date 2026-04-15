from engine.router import Router
from engine.reasoning import ReasoningEngine
from engine.selfcorrection import SelfCorrection
from engine.selfimprove import SelfImprove
from engine.score import ScoreEngine

from engine.thread_manager import ThreadManager
from engine.functioncalling import FunctionCalling
from engine.tool_router import ToolRouter
from engine.agent import Agent
from engine.streamer import Streamer

from engine.context_compressor import ContextCompressor
from engine.memory_ranker import MemoryRanker
from engine.multi_agent import MultiAgent
from engine.tool_chain import ToolChain
from engine.selfreflection import SelfReflection
from engine.autonomous_loop import AutonomousLoop

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

        self.tool_router = ToolRouter()
        self.agent = Agent()
        self.streamer = Streamer()

        self.context_compressor = ContextCompressor()
        self.memory_ranker = MemoryRanker()
        self.multi_agent = MultiAgent()

        self.tool_chain = ToolChain()
        self.self_reflection = SelfReflection()
        self.autonomous_loop = AutonomousLoop()

        self.functions = FunctionCalling({})

    async def handle(
        self,
        user_input: str,
        user_id: str,
        thread_id: str = None,
        context: dict = None
    ):
        context = context or {}

        # =========================
        # THREAD MANAGEMENT (SAFE)
        # =========================
        if not thread_id:
            thread_id = self.threads.create_thread(user_id)

        self.threads.add_message(thread_id, "user", user_input)

        thread_data = self.threads.get_thread(thread_id) or {}
        messages = thread_data.get("messages", [])

        # =========================
        # MEMORY RETRIEVAL (SAFE)
        # =========================
        memory_context = await self.memory.retrieve(user_id, user_input)
        memory_context = memory_context or ""

        # =========================
        # ROUTING (INTENT LAYER)
        # =========================
        route = self.router.route(user_input, context)

        # =========================
        # AUTONOMOUS SIGNALS
        # =========================
        auto_tasks = self.autonomous_loop.decide_next_task(
            user_input,
            str(memory_context)
        ) or []

        # =========================
        # AGENT DECISION LAYER
        # =========================
        actions = await self.agent.decide(user_input, route) or []

        model = self.selector.select(route, user_input, context)

        results = []
        final_response = ""

        score = 0
        mem_score = 0

        # =========================
        # EXECUTION ENGINE
        # =========================
        for action in actions:

            action_type = action.get("type")

            # ---------------- TOOL PATH ----------------
            if action_type == "tool":

                tool_info = self.tool_router.route(user_input)

                tool_name = None
                if isinstance(tool_info, dict):
                    tool_name = tool_info.get("tool")

                if tool_name:

                    try:
                        tool_result = await self.tool_chain.execute_chain(
                            [tool_name],
                            user_input,
                            self.functions
                        )
                        results.append(tool_result)
                    except Exception as e:
                        results.append({"tool_error": str(e)})

            # ---------------- REASONING PATH ----------------
            elif action_type == "reason":

                compressed_memory = self.context_compressor.compress(messages)

                reasoning_output = await self.reasoning.process(
                    input_text=user_input,
                    memory=f"{memory_context}\n{compressed_memory}",
                    model=model,
                    route=route
                )

                corrected = await self.corrector.correct(
                    user_input,
                    reasoning_output,
                    model
                )

                score = self.scorer.evaluate(corrected) or 0

                improved = await self.improver.improve(
                    user_input,
                    corrected,
                    score,
                    model
                )

                # ================= MULTI MODEL VALIDATION =================
                validated = await self.multi_agent.run(
                    [model],
                    improved
                )

                validated = validated or improved

                # ================= SELF REFLECTION =================
                reflection = self.self_reflection.reflect(
                    user_input,
                    validated
                ) or {}

                if reflection.get("needs_improvement"):
                    validated = await self.improver.improve(
                        user_input,
                        validated,
                        score,
                        model
                    )

                # ================= STREAM OUTPUT =================
                streamed_chunks = []

                try:
                    async for chunk in self.streamer.stream_tokens(validated):
                        if isinstance(chunk, dict):
                            streamed_chunks.append(chunk.get("token", ""))
                        else:
                            streamed_chunks.append(str(chunk))
                except Exception:
                    streamed_chunks = [str(validated)]

                final_response = "".join(streamed_chunks).strip()

                # ================= MEMORY SCORING =================
                mem_score = self.memory_ranker.score(final_response) or 0

                # ================= MEMORY STORAGE =================
                await self.memory.store(
                    user_id,
                    user_input,
                    final_response,
                    mem_score
                )

                self.threads.add_message(
                    thread_id,
                    "assistant",
                    final_response
                )

        # ================= FALLBACK (STRICT) =================
        if not final_response:
            if results:
                final_response = str(results)
            else:
                final_response = ""

        # ================= FINAL RESPONSE =================
        return {
            "response": final_response,
            "stream": bool(final_response),
            "score": score,
            "memory_score": mem_score,
            "route": route,
            "model": getattr(model, "__class__", type(model)).__name__,
            "thread_id": thread_id,
            "auto_tasks": auto_tasks,
            "actions": actions
        }