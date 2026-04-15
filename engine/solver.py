class Solver:
    async def solve(self, plan: list, model, tools: dict):
        results = []

        for step in plan[:5]:  # anti-loop limit
            step_type = step.get("type")

            try:
                if step_type == "reason":
                    content = step.get("content", "")
                    result = await model.generate(content)

                elif step_type == "tool":
                    tool_name = step.get("tool")
                    tool_input = step.get("input", "")

                    tool = tools.get(tool_name)

                    if tool:
                        result = await tool(tool_input)
                    else:
                        result = f"Tool {tool_name} not found"

                else:
                    result = "Invalid step"

            except Exception as e:
                result = f"Error: {str(e)}"

            results.append({
                "step": step,
                "result": result
            })

        return results