from engine.reason import ReasonPlanner
from engine.solver import Solver
from engine.tools import Tools


class ReasoningEngine:
    def __init__(self):
        self.planner = ReasonPlanner()
        self.solver = Solver()
        self.tools = Tools()

    async def process(self, input_text: str, memory: str, model, route: str):
        # 1. Create plan
        plan = await self.planner.create_plan(input_text, memory, model)

        # safety fallback
        if not isinstance(plan, list):
            plan = [{"type": "reason", "content": input_text}]

        # 2. Execute plan
        toolset = self.tools.get_tools()
        results = await self.solver.solve(plan, model, toolset)

        # 3. Build final answer
        final_prompt = self._build_final_prompt(input_text, results, memory)

        final_answer = await model.generate(final_prompt)

        return final_answer

    def _build_final_prompt(self, input_text: str, results: list, memory: str):
        steps_summary = "\n".join(
            [f"Step: {r['step']} \nResult: {r['result']}" for r in results]
        )

        return f"""
You are an advanced AI.

Use context if relevant:
{memory}

User:
{input_text}

Steps:
{steps_summary}

Give final, accurate, clean answer.
"""