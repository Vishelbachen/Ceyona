import requests
import logging

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self, settings):
        self.api_key = settings.SERPAPI_KEY

    def search(self, query: str, num: int = 5) -> dict:
        if not query:
            return {"error": "empty_query"}

        try:
            url = "https://serpapi.com/search"

            params = {
                "q": query,
                "api_key": self.api_key,
                "num": num
            }

            res = requests.get(url, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()

            results = []

            for item in data.get("organic_results", []) or []:
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", "")
                })

            return {
                "query": query,
                "results": results
            }

        except requests.RequestException as e:
            logger.warning(f"[SEARCH API FAIL] {e}")
            return {"error": "api_failed", "results": []}

        except Exception as e:
            logger.exception(f"[SEARCH UNKNOWN ERROR] {e}")
            return {"error": "unknown", "results": []}