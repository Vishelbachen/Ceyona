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