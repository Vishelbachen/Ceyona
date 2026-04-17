class AgentSwarm:
    def __init__(self, agents):
        self.agents = agents

    async def run_all(self, task: str):

        results = []

        for agent in self.agents:
            result = await agent.run(task)
            results.append(result)

        return self.merge(results)

    def merge(self, results):
        return max(results, key=lambda x: len(str(x)))