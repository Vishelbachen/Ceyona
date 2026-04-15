import os
import httpx


SERPAPI_KEY = os.getenv("SERPAPI_KEY")


async def search(query: str):
    url = "https://serpapi.com/search.json"

    params = {
        "q": query,
        "api_key": SERPAPI_KEY
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)

    data = response.json()

    results = []
    for item in data.get("organic_results", [])[:3]:
        results.append(item.get("snippet"))

    return "\n".join(results)