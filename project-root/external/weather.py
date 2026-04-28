from typing import Any, Dict, Optional


class WeatherClient:
    """
    AI Platform v4.7 — Weather External Client

    RESPONSIBILITY:
    - Fetch current weather data
    - Fetch forecast data
    - Provide raw weather API response

    STRICT RULES:
    - No business logic
    - No formatting for UI
    - No decision-making
    - No LLM / retrieval / memory usage
    - No orchestration logic
    """

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url or "https://api.openweathermap.org/data/2.5"

    async def get_current_weather(
        self,
        location: str,
        units: str = "metric",
    ) -> Dict[str, Any]:
        """
        Returns current weather data (raw API response).
        """

        return {
            "location": location,
            "temperature": 0,
            "condition": "clear",
            "humidity": 0,
            "units": units,
            "source": "mock_openweather",
        }

    async def get_forecast(
        self,
        location: str,
        days: int = 5,
        units: str = "metric",
    ) -> Dict[str, Any]:
        """
        Returns forecast data (raw API response).
        """

        return {
            "location": location,
            "days": days,
            "forecast": [
                {
                    "day": i + 1,
                    "temperature": 0,
                    "condition": "clear",
                }
                for i in range(days)
            ],
            "units": units,
            "source": "mock_openweather",
        }