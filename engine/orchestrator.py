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
        # ================= CORE =================
        self.router = Router()
        self.reasoning = ReasoningEngine()
        self.corrector = SelfCorrection()
        self.improver = SelfImprove()
        self.scorer = ScoreEngine()

        # ================= MEMORY =================
        self.memory = MemoryIntelligence()
        self.selector = ModelSelector()

        # ================= THREADS =================
        self.threads = ThreadManager()

        # ================= TOOLS =================
        self.tool_router = ToolRouter()
        self.tool_chain = ToolChain()
        self.functions = FunctionCalling({})

        # ================= AGENT =================
        self.agent = Agent()

        # ================= STREAM =================
        self.streamer = Streamer()

        # ================= ADVANCED =================
        self.context_compressor = ContextCompressor()
        self.memory_ranker = MemoryRanker()
        self.multi_agent = MultiAgent()
        self.self_reflection = SelfReflection()
        self.autonomous_loop = AutonomousLoop()

    async def handle(
        self,
        user_input: str,
        user_id: str,
        thread_id: str = None,
        context: dict = None
    ):
        context = context or {}

        # ================= THREAD SAFETY =================
        if not thread_id:
            thread_id = self.threads.create_thread(user_id)

        self.threads.add_message(thread_id, "user", user_input)

        thread_data = self.threads.get_thread(thread_id) or {}
        messages = thread_data.get("messages") or []

        # ================= MEMORY =================
        memory_context = await self.memory.retrieve(user_id, user_input) or ""

        # ================= ROUTING =================
        route = self.router.route(user_input, context)

        # ================= AUTONOMOUS =================
        auto_tasks = self.autonomous_loop.decide_next_task(
            user_input,
            str(memory_context)
        ) or []

        # ================= AGENT =================
        actions = await self.agent.decide(user_input, route) or []

        model = self.selector.select(route, user_input, context)

        results = []
        final_response = ""
        score = 0
        mem_score = 0

        # ================= EXECUTION LOOP =================
        for action in actions:
            action_type = action.get("type")

            # ================= TOOL EXECUTION =================
            if action_type == "tool":

                tool_info = self.tool_router.route(user_input)

                tool_name = None
                if isinstance(tool_info, dict):
                    tool_name = tool_info.get("tool")
                elif isinstance(tool_info, str):
                    tool_name = tool_info

                if tool_name:
                    try:
                        tool_result = await self.tool_chain.execute_chain(
                            [tool_name],
                            user_input,
                            self.functions
                        )
                        results.append(tool_result)
                    except Exception as e:
                        results.append({
                            "tool_error": str(e),
                            "tool": tool_name
                        })

            # ================= REASONING =================
            elif action_type == "reason":

                compressed_memory = self.context_compressor.compress(messages)

                reasoning_output = await self.reasoning.process(
                    input_text=user_input,
                    memory=f"{memory_context}\n{compressed_memory}",
                    model=model,
                    route=route
                ) or ""

                corrected = await self.corrector.correct(
                    user_input,
                    reasoning_output,
                    model
                ) or reasoning_output

                score = self.scorer.evaluate(corrected) or 0

                improved = await self.improver.improve(
                    user_input,
                    corrected,
                    score,
                    model
                ) or corrected

                # ================= MULTI-MODEL VALIDATION =================
                validated = await self.multi_agent.run(
                    [model],
                    improved
                ) or improved

                if not isinstance(validated, str):
                    validated = str(validated)

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
                    ) or validated

                # ================= STREAMING =================
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

                if not isinstance(final_response, str):
                    final_response = str(final_response)

                # ================= MEMORY SCORE =================
                mem_score = self.memory_ranker.score(final_response) or 0

                # ================= STORE MEMORY =================
                await self.memory.store(
                    user_id,
                    user_input,
                    final_response,
                    mem_score
                )

                # ================= THREAD STORE =================
                self.threads.add_message(
                    thread_id,
                    "assistant",
                    final_response
                )

        # ================= FALLBACK =================
        if not final_response:
            final_response = str(results) if results else ""

        # ================= OUTPUT CONTRACT =================
        return {
            "response": final_response,
            "stream": bool(final_response),
            "score": score or 0,
            "memory_score": mem_score or 0,
            "route": route,
            "model": getattr(model, "__class__", type(model)).__name__,
            "thread_id": thread_id,
            "auto_tasks": auto_tasks,
            "actions": actions
        }