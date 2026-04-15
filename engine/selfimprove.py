class SelfImprove:
    async def improve(self, input_text: str, output: str, score: int, model):
        if score >= 3:
            return output

        prompt = f"""
Improve the following response.

User:
{input_text}

Response:
{output}

Make it more accurate, helpful and complete.
"""

        improved = await model.generate(prompt)
        return improved