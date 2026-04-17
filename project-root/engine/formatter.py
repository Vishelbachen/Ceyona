from groq import Groq
import os


class Formatter:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    async def format(self, intent: dict, tool_result: dict):
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": """
You are a response formatter for an AI assistant.

Your job:
- Convert tool output into a natural, helpful message
- Do NOT output JSON
- Be concise
- Match language of user input implicitly
- If it's a map result → describe location
- If it's weather → describe weather clearly

No extra commentary.
"""
                    },
                    {
                        "role": "user",
                        "content": f"""
Intent:
{intent}

Tool result:
{tool_result}
"""
                    }
                ],
                temperature=0.2
            )

            return response.choices[0].message.content.strip()

        except Exception:
            return str(tool_result)