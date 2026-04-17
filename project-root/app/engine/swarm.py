class Swarm:
    def __init__(self, agents):
        self.agents = agents

    async def run(self, text: str):

        results = []

        for agent in self.agents:
            try:
                res = await agent.run(text)
                results.append(res)
            except:
                continue

        return self.select_best(results)

    def select_best(self, results):
        if not results:
            return None

        # простая эвристика качества
        return max(results, key=lambda x: len(str(x)))