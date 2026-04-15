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

    async def handle(self, user_input: str, user_id: str, thread_id: str = None, context: dict = None):
        context = context or {}

        # THREAD
        if not thread_id:
            thread_id = self.threads.create_thread(user_id)

        self.threads.add_message(thread_id, "user", user_input)

        # MEMORY
        memory_context = await self.memory.retrieve(user_id, user_input)

        # ROUTE
        route = self.router.route(user_input, context)

        # AUTONOMOUS THINKING
        auto_tasks = self.autonomous_loop.decide_next_task(user_input, str(memory_context))

        # AGENT DECISION
        actions = await self.agent.decide(user_input, route)

        model = self.selector.select(route, user_input, context)

        results = []

        # EXECUTION LOOP
        for action in actions:

            # ================= TOOL PATH =================
            if action["type"] == "tool":
                tool_info = self.tool_router.route(user_input)

                if tool_info:

                    # TOOL CHAINING (future support)
                    result = await self.tool_chain.execute_chain(
                        [tool_info["tool"]],
                        user_input,
                        self.functions
                    )

                    results.append(result)

            # ================= REASONING PATH =================
            elif action["type"] == "reason":

                compressed_memory = self.context_compressor.compress(
                    self.threads.get_thread(thread_id)["messages"]
                )

                reasoning_output = await self.reasoning.process(
                    input_text=user_input,
                    memory=str(compressed_memory),
                    model=model,
                    route=route
                )

                corrected = await self.corrector.correct(
                    user_input,
                    reasoning_output,
                    model
                )

                score = self.scorer.evaluate(corrected)

                final = await self.improver.improve(
                    user_input,
                    corrected,
                    score,
                    model
                )

                # MULTI MODEL CHECK
                final = await self.multi_agent.run(
                    [model],
                    final
                )

                # SELF REFLECTION
                reflection = self.self_reflection.reflect(user_input, final)

                if reflection["needs_improvement"]:
                    final = await self.improver.improve(
                        user_input,
                        final,
                        score,
                        model
                    )

                # STREAM OUTPUT
                streamed = []
                async for chunk in self.streamer.stream_tokens(final):
                    streamed.append(chunk)

                final_text = "".join([c["token"] for c in streamed])

                # MEMORY SCORING (IMPORTANT)
                mem_score = self.memory_ranker.score(final_text)

                await self.memory.store(user_id, user_input, final_text, mem_score)

                self.threads.add_message(thread_id, "assistant", final_text)

                return {
                    "response": final_text,
                    "stream": True,
                    "score": score,
                    "memory_score": mem_score,
                    "route": route,
                    "model": model.__class__.__name__,
                    "thread_id": thread_id,
                    "auto_tasks": auto_tasks,
                    "actions": actions
                }

        return {
            "response": results,
            "stream": False,
            "route": route,
            "thread_id": thread_id,
            "auto_tasks": auto_tasks,
            "actions": actions
        }