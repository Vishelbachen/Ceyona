import logging

logger = logging.getLogger(__name__)


class ToolEngine:
    """
    TOOL ENGINE V2++
    - executes tools based on router output
    - safe execution layer
    - zero crash guarantee
    """

    def __init__(self, tools):
        self.tools = tools

    async def run(self, route: dict, text: str) -> dict:
        try:
            if not route:
                return {"status": "no_route"}

            tool = (route.get("type") or "").lower()
            args = route.get("args")

            # ======================
            # WEATHER
            # ======================
            if tool == "weather":
                city = self._safe_city(args, text)
                data = self.tools.weather.get_weather(city)

                return {
                    "status": "success",
                    "tool": "weather",
                    "data": data
                }

            # ======================
            # MAPS
            # ======================
            if tool == "maps":
                data = self.tools.maps.geocode(text)

                return {
                    "status": "success",
                    "tool": "maps",
                    "data": data
                }

            # ======================
            # SEARCH
            # ======================
            if tool == "search":
                data = self.tools.search.search(text)

                return {
                    "status": "success",
                    "tool": "search",
                    "data": data
                }

            return {"status": "llm"}

        except Exception as e:
            logger.exception(f"[TOOL ENGINE ERROR] {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def _safe_city(self, args, text: str) -> str:
        if isinstance(args, str) and args.strip():
            return args
        return text.split()[-1] if text else "Tbilisi"