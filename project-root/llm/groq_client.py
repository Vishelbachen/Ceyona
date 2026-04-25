import os
import httpx

async def ask_groq(prompt: str):

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return {"error": "GROQ_API_KEY not set"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "llama-3.1-70b",
                    "messages": [{"role": "user", "content": prompt}]
                }
            )

        if r.status_code != 200:
            return {"error": f"Groq API error: {r.status_code}", "body": r.text}

        return r.json()

    except Exception as e:
        return {"error": f"Groq request failed: {str(e)}"}