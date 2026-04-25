import os
import httpx

async def ask_groq(prompt: str):

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return {"error": "missing GROQ_API_KEY"}

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama-3.1-70b-versatile",
                "messages": [{"role": "user", "content": prompt}]
            }
        )

    return r.json()