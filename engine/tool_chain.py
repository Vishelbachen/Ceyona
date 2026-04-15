class ToolChain:
    """
    Allows tools to call other tools (agentic behavior)
    """

    async def execute_chain(self, tools, initial_input: str):
        results = []
        current_input = initial_input

        for tool in tools:
            result = await tool(current_input)

            results.append(result)

            # output becomes next input (chain behavior)
            current_input = str(result)

        return results