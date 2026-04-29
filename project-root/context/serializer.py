from context.context_models import ContextChunk


def serialize(chunks: list[ContextChunk]) -> str:
    """
    Format context chunks into a single string for LLM injection.
    Deterministic. No inference. No summarization.
    """
    if not chunks:
        return ""

    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[{i}] {chunk.content.strip()}")

    return "\n\n".join(parts)