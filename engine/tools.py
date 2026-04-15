import requests


class Tools:
    def get_weather(self, api_key, city):
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}"
        return requests.get(url).json()

    def search(self, api_key, query):
        url = f"https://serpapi.com/search?q={query}&api_key={api_key}"
        return requests.get(url).json()