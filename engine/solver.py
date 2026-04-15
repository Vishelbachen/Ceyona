class Solver:
    async def solve(self, plan: list, model, tools: dict):
        results = []

        for step in plan:
            step_type = step.get("type")
            content = step.get("content")

            if step_type == "reason":
                result = await model.generate(content)

            elif step_type == "tool":
                tool_name = step.get("tool")
                tool_input = step.get("input")

                tool = tools.get(tool_name)
                if tool:
                    result = await tool(tool_input)
                else:
                    result = f"Tool {tool_name} not found"

            else:
                result = "Unknown step"

            results.append({
                "step": step,
                "result": result
            })

        return results