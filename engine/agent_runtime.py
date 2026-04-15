import asyncio


class AgentRuntime:
    """
    Runs multiple agents in parallel (ChatGPT multi-agent behavior layer)
    """

    async def run_agents(self, agents, input_text):
        tasks = [agent.run(input_text) for agent in agents]
        return await asyncio.gather(*tasks)