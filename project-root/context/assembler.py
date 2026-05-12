import logging

from contracts.context_contracts import AssembledContext, ContextRequest
from contracts.shared_types import TruthMode
from cognition.intent_engine import Intent

logger = logging.getLogger(__name__)

# ─── INTENT → TRUTH MODE MAPPING ─────────────────────────────────────────────

# Intents that MUST have grounded data — no context = block
_STRICT_INTENTS = {
    Intent.SEARCH,
    Intent.WEATHER,
    Intent.MAPS,
    Intent.MAPS_POI,
}

# Intents that benefit from context but can generate freely
_HYBRID_INTENTS = {
    Intent.INSTRUCTION,
    Intent.CODE,
    Intent.ANALYSIS,
    Intent.EXAM,
    Intent.MATH,
}

# Intents that generate freely — no grounding needed
_GENERATIVE_INTENTS = {
    Intent.CREATIVE,
    Intent.CONVERSATION,
    Intent.EMOTIONAL,
    Intent.UNKNOWN,
}


def resolve_truth_mode(intent: Intent | None) -> TruthMode:
    if intent is None:
        return TruthMode.HYBRID
    if intent in _STRICT_INTENTS:
        return TruthMode.STRICT
    if intent in _GENERATIVE_INTENTS:
        return TruthMode.GENERATIVE
    return TruthMode.HYBRID


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
