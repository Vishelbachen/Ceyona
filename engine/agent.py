class Agent:
    """
    Решает: tool OR reasoning
    """

    async def decide(self, user_input: str, route: str):
        text = user_input.lower()

        tool_keywords = [
            "weather", "search", "map", "price", "crypto", "ton"
        ]

        if any(x in text for x in tool_keywords):
            return [{"type": "tool"}]

        return [{"type": "reason"}]