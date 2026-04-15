class ReasonPlanner:
    async def create_plan(self, input_text: str, memory: str, model):
        prompt = f"""
You are a planning engine.

Break the task into steps.

Available step types:
- reason: think or generate text
- tool: use external tool

Return JSON list:
[
  {{"type": "reason", "content": "..."}},
  {{"type": "tool", "tool": "search", "input": "..."}}
]

User input:
{input_text}

Memory:
{memory}
"""

        response = await model.generate(prompt)

        try:
            import json
            return json.loads(response)
        except:
            return [{"type": "reason", "content": input_text}]