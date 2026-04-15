class FunctionCalling:
    def __init__(self, tools: dict):
        self.tools = tools

    async def execute(self, tool_name: str, args: dict):
        tool = self.tools.get(tool_name)

        if not tool:
            return {"error": f"Tool {tool_name} not found"}

        try:
            result = await tool(args.get("query", ""))
            return {"tool": tool_name, "result": result}

        except Exception as e:
            return {"tool": tool_name, "error": str(e)}