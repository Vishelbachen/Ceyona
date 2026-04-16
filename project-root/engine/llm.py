import os
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


class LLMEngine:
    async def generate(self, user_text: str) -> str:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a universal AI assistant. "
                            "You must respond in the same language as the user. "
                            "Be helpful, accurate, and concise. "
                            "You can handle reasoning, math, coding, life advice, and explanations."
                        )
                    },
                    {"role": "user", "content": user_text}
                ]
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"LLM error: {str(e)}"