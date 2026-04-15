class FunctionCalling:
    def __init__(self, tools: dict):
        self.tools = tools

    async def execute(self, tool_name: str, args):
        tool = self.tools.get(tool_name)

        if not tool:
            return {"error": f"tool {tool_name} not found"}

        try:
            if isinstance(args, dict):
                return {"result": await tool(**args)}
            return {"result": await tool(args)}

        except Exception as e:
            return {"error": str(e)}