from context.context_models import ContextBlock
from contracts.context_contracts import AssembledContext


def to_prompt_string(ctx: AssembledContext) -> str:
    """Convert assembled context to a prompt-ready string."""
    if not ctx.text:
        return ""
    return ctx.text


def to_dict(ctx: AssembledContext) -> dict:
    return {
        "text": ctx.text,
        "document_count": ctx.document_count,
        "truncated": ctx.truncated,
    }


def block_to_prompt_string(block: ContextBlock, separator: str = "\n\n---\n\n") -> str:
    """
    Convert a ContextBlock to a prompt-ready string.

    Preserves chunk order from assembler. Skips empty chunks.
    Use this when callers have full ContextBlock provenance.
    """
    parts = [c.content.strip() for c in block.chunks if c.content.strip()]
    return separator.join(parts)


def block_to_dict(block: ContextBlock) -> dict:
    """
    Serialize ContextBlock to dict — useful for logging, debug endpoints,
    or future explainability features (source attribution per chunk).
    """
    return {
        "total_chars": block.total_chars,
        "truncated": block.truncated,
        "chunk_count": len(block.chunks),
        "chunks": [
            {
                "content": c.content,
                "score": round(c.score, 4),
                "source": c.source,
                "metadata": c.metadata,
            }
            for c in block.chunks
        ],
    }