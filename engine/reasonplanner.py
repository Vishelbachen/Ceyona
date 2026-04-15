import json


class ReasonPlanner:
    async def create_plan(self, input_text: str, memory: str, model):
        prompt = f"""
You are a planning system.

Break task into steps.

Rules:
- Keep steps minimal
- Use "reason" or "tool"
- Only use tools if needed

Return JSON list.

User:
{input_text}

Memory:
{memory}
"""

        response = await model.generate(prompt)

        try:
            parsed = json.loads(response)

            if isinstance(parsed, list):
                return parsed

        except Exception:
            pass

        return [{"type": "reason", "content": input_text}]