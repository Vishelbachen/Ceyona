from services.search import search
from services.weather import get_weather


class Tools:
    def get_tools(self):
        return {
            "search": search,
            "weather": get_weather
        }