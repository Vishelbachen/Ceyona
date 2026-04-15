# engine/tools/weather_tool.py

from engine.services.weather import WeatherService


class WeatherTool:
    def __init__(self, settings):
        self.service = WeatherService(settings)

    def run(self, city: str, lang: str = "en") -> str:
        try:
            data = self.service.get_weather(city, lang)

            return (
                f"Weather in {data['city']}:\n"
                f"- Temperature: {data['temp']}°C\n"
                f"- Feels like: {data['feels_like']}°C\n"
                f"- Condition: {data['condition']}\n"
                f"- Humidity: {data['humidity']}%\n"
                f"- Wind: {data['wind']} m/s"
            )

        except Exception as e:
            return f"Weather service error: {str(e)}"