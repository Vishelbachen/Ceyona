class PromptBuilder:
    def build(self, text, context, reasoning):
        return f"""
User input: {text}

Context: {context}

Reasoning: {reasoning}

Generate a clear, helpful, intelligent response.
"""