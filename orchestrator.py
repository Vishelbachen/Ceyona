""" FULL AI BACKEND SYSTEM (OpenAI-like architecture, simplified but scalable)

Includes:

LLM abstraction layer

Prompt builder

Memory (short + long)

Tool calling

Agent loop (planner/executor/critic)

Orchestrator integration


This is a SINGLE-FILE SYSTEM for portability. """

import asyncio from typing import Any, Dict, List

=========================

LLM LAYER

=========================

class BaseLLM: async def generate(self, prompt: str) -> str: raise NotImplementedError

class DummyLLM(BaseLLM): async def generate(self, prompt: str) -> str: return f"LLM_RESPONSE: {prompt[:100]}"

=========================

PROMPT BUILDER

=========================

class PromptBuilder: def build(self, task: str, input_text: str, memory: Dict[str, Any]) -> str: return f""" TASK: {task} INPUT: {input_text} MEMORY: {memory} """

=========================

MEMORY SYSTEM

=========================

class ShortTermMemory: def init(self): self.buffer = []

def add(self, message):
    self.buffer.append(message)
    if len(self.buffer) > 10:
        self.buffer.pop(0)

def get(self):
    return self.buffer

class LongTermMemory: def init(self): self.store = {}

def save(self, user_id: str, data: Any):
    self.store.setdefault(user_id, []).append(data)

def load(self, user_id: str):
    return self.store.get(user_id, [])

=========================

TOOL SYSTEM

=========================

class Tool: def init(self, name, func): self.name = name self.func = func

async def run(self, *args, **kwargs):
    return await self.func(*args, **kwargs)

class ToolRegistry: def init(self): self.tools = {}

def register(self, tool: Tool):
    self.tools[tool.name] = tool

async def call(self, name, *args, **kwargs):
    return await self.tools[name].run(*args, **kwargs)

=========================

AGENT SYSTEM

=========================

class Planner: async def plan(self, input_text: str) -> List[str]: return ["analyze", "respond"]

class Executor: def init(self, llm: BaseLLM): self.llm = llm

async def execute(self, step: str, prompt: str) -> str:
    return await self.llm.generate(prompt + f"\nSTEP: {step}")

class Critic: async def review(self, output: str) -> bool: return True

class Agent: def init(self, planner, executor, critic): self.planner = planner self.executor = executor self.critic = critic

async def run(self, input_text: str, prompt: str):
    steps = await self.planner.plan(input_text)
    result = None

    for step in steps:
        result = await self.executor.execute(step, prompt)

    approved = await self.critic.review(result)

    return result if approved else "Rejected"

=========================

ORCHESTRATOR

=========================

class Orchestrator: def init(self, llm: BaseLLM): self.llm = llm self.prompt_builder = PromptBuilder() self.short_memory = ShortTermMemory() self.long_memory = LongTermMemory()

self.agent = Agent(
        planner=Planner(),
        executor=Executor(llm),
        critic=Critic()
    )

async def handle(self, user_id: str, text: str):
    short_mem = self.short_memory.get()
    long_mem = self.long_memory.load(user_id)

    memory = {
        "short": short_mem,
        "long": long_mem
    }

    prompt = self.prompt_builder.build("general", text, memory)

    result = await self.agent.run(text, prompt)

    self.short_memory.add(text)
    self.long_memory.save(user_id, result)

    return {
        "response": result
    }

=========================

BOOTSTRAP

=========================

async def main(): llm = DummyLLM() orchestrator = Orchestrator(llm)

res = await orchestrator.handle("user1", "Explain AI")
print(res)

if name == "main": asyncio.run(main())