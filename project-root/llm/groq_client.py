import os
import httpx

async def ask_groq(prompt: str):

    api_key = os.getenv("GROQ_API_KEY")

    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama-3.1-70b",
                "messages": [{"role": "user", "content": prompt}]
            }
        )

    return r.json()