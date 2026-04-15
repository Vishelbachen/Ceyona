class Agent:
    """
    Agent mode = system can decide actions autonomously
    """

    async def decide(self, user_input: str, route: str):
        text = user_input.lower()

        actions = []

        # tool use
        if "weather" in text:
            actions.append({"type": "tool", "name": "weather"})

        if "search" in text:
            actions.append({"type": "tool", "name": "search"})

        # reasoning fallback
        if not actions:
            actions.append({"type": "reason"})

        return actions