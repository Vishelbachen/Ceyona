import asyncio


class AgentSwarm:
    """
    Multiple specialized agents working in parallel (OpenAI-style architecture)
    """

    def __init__(self, agents):
        self.agents = agents

    async def run(self, input_text: str):
        tasks = [agent.run(input_text) for agent in self.agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [r for r in results if not isinstance(r, Exception)]