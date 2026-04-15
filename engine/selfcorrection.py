class SelfCorrection:
    async def correct(self, input_text: str, output: str, model):
        prompt = f"""
Check the following response for errors, improve clarity, correctness and usefulness.

User Input:
{input_text}

Response:
{output}

Return improved version only.
"""

        improved = await model.generate(prompt)
        return improved