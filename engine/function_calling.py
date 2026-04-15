class FunctionCalling:
    def __init__(self, tools: dict):
        self.tools = tools

    async def execute(self, function_name: str, args: dict):
        tool = self.tools.get(function_name)

        if not tool:
            return {"error": "tool_not_found"}

        try:
            result = await tool(**args)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}