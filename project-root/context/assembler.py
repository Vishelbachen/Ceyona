import logging
from contracts.context_contracts import AssembledContext, ContextRequest

logger = logging.getLogger(__name__)


def assemble(req: ContextRequest) -> AssembledContext:
    """
    Deterministic context assembly.
    Concatenates retrieved documents up to max_chars limit.
    No ranking. No inference. Formatting only.
    """
    parts: list[str] = []
    total = 0
    truncated = False

    for doc in req.documents:
        chunk = doc.content.strip()
        if not chunk:
            continue

        addition = (req.separator + chunk) if parts else chunk
        if total + len(addition) > req.max_chars:
            truncated = True
            break

        parts.append(chunk)
        total += len(addition)

    text = req.separator.join(parts)

    logger.debug("Context assembled", extra={
        "doc_count": len(parts),
        "chars": total,
        "truncated": truncated,
    })

    return AssembledContext(
        text=text,
        document_count=len(parts),
        truncated=truncated,
    )