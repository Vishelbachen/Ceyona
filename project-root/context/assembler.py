from context.context_models import Context


class ContextAssembler:
    """
    Converts retrieval output + user query into LLM-ready context
    """

    def build(self, user_id: str, query: str, docs: list[str]) -> Context:
        return Context(
            user_id=user_id,
            query=query,
            documents=docs
        )