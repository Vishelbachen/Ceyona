from context.context_models import Context


class ContextSerializer:
    """
    Converts structured context into prompt string
    """

    def serialize(self, context: Context) -> str:
        docs_text = "\n".join(context.documents)
        return f"QUERY: {context.query}\n\nCONTEXT:\n{docs_text}"