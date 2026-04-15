from engine.reason import ReasonPlanner
from engine.solver import Solver
from engine.tools import Tools


class ReasoningEngine:
    def __init__(self):
        self.planner = ReasonPlanner()
        self.solver = Solver()
        self.tools = Tools()

    async def process(self, input_text: str, memory: str, model, route: str):
        # 1. Build plan
        plan = await self.planner.create_plan(input_text, memory, model)

        # 2. Execute plan
        toolset = self.tools.get_tools()
        results = await self.solver.solve(plan, model, toolset)

        # 3. Combine results
        final_prompt = self._build_final_prompt(input_text, results)

        final_answer = await model.generate(final_prompt)

        return final_answer

    def _build_final_prompt(self, input_text: str, results: list):
        steps_summary = "\n".join(
            [f"Step: {r['step']} \nResult: {r['result']}" for r in results]
        )

        return f"""
User question:
{input_text}

Steps and results:
{steps_summary}

Provide final clear answer.
"""