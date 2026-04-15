class Router:
    def route(self, text: str) -> dict:
        text_lower = text.lower()

        if any(word in text_lower for word in ["weather", "погода"]):
            return {"type": "weather"}

        if any(word in text_lower for word in ["map", "где", "location"]):
            return {"type": "maps"}

        if any(word in text_lower for word in ["search", "найди"]):
            return {"type": "search"}

        return {"type": "general"}