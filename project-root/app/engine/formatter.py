import json


class Formatter:
    def __init__(self):
        pass

    async def format(self, intent, result, raw_response=None):
        if raw_response:
            return self._clean_text(raw_response)

        if isinstance(result, dict):
            return self._format_tool_result(intent, result)

        if isinstance(result, str):
            return self._clean_text(result)

        return "I could not process your request."

    def _format_tool_result(self, intent, result):
        tool = intent.get("tool")

        if tool == "map":
            return self._format_map(result)

        if tool == "weather":
            return self._format_weather(result)

        return self._fallback(result)

    def _format_map(self, result):
        place = result.get("place_name", "")
        lat = result.get("latitude")
        lon = result.get("longitude")

        if not place:
            return "Location not found."

        return f"{place} ({lat}, {lon})"

    def _format_weather(self, result):
        city = result.get("city")
        temp = result.get("temp")
        desc = result.get("description")

        if not city:
            return "Weather data not available."

        return f"{city}: {temp}°C, {desc}"

    def _fallback(self, result):
        try:
            return json.dumps(result, ensure_ascii=False)
        except:
            return str(result)

    def _clean_text(self, text: str):
        if not text:
            return ""

        return text.strip()