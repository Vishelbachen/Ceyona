class Router:
    def route(self, user_input: str, context: dict):
        text = user_input.lower()

        if any(x in text for x in ["code", "python", "bug", "error"]):
            return "coding"

        if any(x in text for x in ["weather", "temperature"]):
            return "weather"

        if any(x in text for x in ["map", "location"]):
            return "maps"

        if any(x in text for x in ["who", "what", "why", "how"]):
            return "knowledge"

        return "general"