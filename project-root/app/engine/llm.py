import os
from groq import Groq


class LLM:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.1-8b-instant"

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

from groq import Groq

client = Groq()

models = client.models.list()

for model in models.data:
    print(model.id)
print("FILE EXECUTED")