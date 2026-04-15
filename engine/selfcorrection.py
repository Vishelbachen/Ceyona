class SelfCorrection:
    async def correct(self, input_text: str, output: str, model):
        if len(output) < 20:
            return output

        prompt = f"""
Check response for hallucinations or incorrect facts.

User:
{input_text}

Response:
{output}

If correct, return as is.
If incorrect, fix it.
"""

        return await model.generate(prompt)