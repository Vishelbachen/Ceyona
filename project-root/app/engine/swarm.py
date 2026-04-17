class Swarm:
    def __init__(self, agents):
        self.agents = agents

    async def run(self, text: str):
        results = []

        for agent in self.agents:
            try:
                res = await agent.run(text)
                results.append(res)
            except Exception:
                continue

        return self.select_best(results)

    def select_best(self, results):
        if not results:
            return None

        def score(x):
            if isinstance(x, dict) and "error" in x:
                return 0
            return len(str(x))

        return max(results, key=score)