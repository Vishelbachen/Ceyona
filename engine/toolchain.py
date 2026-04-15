class ToolChain:
    """
    Executes tools in sequence (tool → tool → reasoning)
    """

    async def execute_chain(self, tools, input_text: str, function_executor):
        result = input_text

        for tool in tools:
            result = await function_executor.execute(
                tool,
                {"query": result}
            )

        return result