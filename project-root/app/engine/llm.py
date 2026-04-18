import os
from groq import Groq


class LLM:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "mixtral-8x7b-32768"

    async def __call__(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.3
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"LLM_ERROR: {str(e)}"