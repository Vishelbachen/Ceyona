import logging

from context.context_models import ContextBlock, ContextChunk
from contracts.context_contracts import AssembledContext, ContextRequest
from contracts.shared_types import RoutingProfile, TruthMode

logger = logging.getLogger(__name__)


def resolve_truth_mode(routing: RoutingProfile) -> TruthMode:
    """
    Read TruthMode from the RoutingProfile declared by _resolve_routing().

    Architecture contract (§10, §2.1):
    - TruthMode is declared once, in _resolve_routing() inside intent_engine.
    - assembler reads it — assembler does NOT derive it from Intent.
    - This eliminates the dual-authority problem: previously both
      assembler._STRICT_INTENTS and _resolve_routing would have to stay in sync.
      Now there is exactly one source of truth.

    Callers: orchestrator._build_messages(), orchestrator._run_heavy().
    These now pass intent_result.routing instead of intent_result.intent.
    """
    return routing.truth_mode


def assemble(req: ContextRequest) -> AssembledContext:
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


def assemble_chunks(chunks: list[ContextChunk], max_chars: int = 3000, separator: str = "\n\n---\n\n") -> ContextBlock:
    """
    Assemble ContextChunks into a ContextBlock, applying char-budget truncation.

    Use this when the caller has full ContextChunk provenance (source, metadata)
    and wants to pass a rich ContextBlock to the serializer.

    assemble() remains for compatibility with ContextRequest/RetrievedDocument callers.
    """
    accepted: list[ContextChunk] = []
    total = 0
    truncated = False

    for chunk in chunks:
        text = chunk.content.strip()
        if not text:
            continue
        addition = (separator + text) if accepted else text
        if total + len(addition) > max_chars:
            truncated = True
            break
        accepted.append(chunk)
        total += len(addition)

    logger.debug("ContextBlock assembled", extra={
        "chunks": len(accepted),
        "total_chars": total,
        "truncated": truncated,
    })

    return ContextBlock(
        chunks=accepted,
        total_chars=total,
        truncated=truncated,
    )