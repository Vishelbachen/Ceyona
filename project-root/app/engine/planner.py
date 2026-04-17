import json
from groq import Groq
import os


class Planner:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    async def parse(self, text: str):
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": """
You are an intent classifier.

Return ONLY valid JSON:
{
  "tool": "map | weather | none",
  "query": "extracted entity or location"
}

Rules:
- No explanations
- No extra text
- If unclear → tool = none
"""
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0
            )

            content = response.choices[0].message.content.strip()

            return json.loads(content)

        except Exception:
            return {
                "tool": "none",
                "query": None
            }