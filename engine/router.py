class Router:
    def route(self, text: str) -> dict:
        text_lower = text.lower()

        # =========================
        # MATH / ANALYTICAL MODE (CRITICAL)
        # =========================
        if any(x in text_lower for x in [
            "prove", "theorem", "f(", "=", "derive", "limit", "integral",
            "solve", "function", "доказать", "уравнение"
        ]):
            return {
                "type": "analysis",
                "domain": "math"
            }

        # =========================
        # WEATHER
        # =========================
        if any(word in text_lower for word in ["weather", "погода"]):
            return {
                "type": "weather",
                "domain": "api"
            }

        # =========================
        # MAPS / LOCATION
        # =========================
        if any(word in text_lower for word in ["map", "где", "location", "near"]):
            return {
                "type": "maps",
                "domain": "api"
            }

        # =========================
        # SEARCH
        # =========================
        if any(word in text_lower for word in ["search", "найди", "find"]):
            return {
                "type": "search",
                "domain": "api"
            }

        # =========================
        # DEFAULT LLM MODE
        # =========================
        return {
            "type": "general",
            "domain": "llm"
        }