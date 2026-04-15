class PromptTemplates:
    """
    Central prompt management system
    (ChatGPT-like prompt architecture layer)
    """

    @staticmethod
    def reasoning_prompt(memory: str, input_text: str):
        return f"""
You are an advanced AI reasoning system.

Memory:
{memory}

User Input:
{input_text}

Instructions:
- Think step by step
- Be accurate
- Use memory context if relevant
- Avoid hallucination

Return final answer only.
"""

    @staticmethod
    def tool_prompt(input_text: str):
        return f"""
Determine if tools are needed.

User Input:
{input_text}

Return:
- tool name OR "none"
"""