from __future__ import annotations

from typing import List

from context.context_models import ContextDocument, ContextUnit


# =========================
# CONTEXT SERIALIZER
# =========================
class ContextSerializer:
    """
    ROLE:
    - convert structured context → flat text for LLM input
    - ensure deterministic formatting

    STRICT RULES:
    - NO reasoning
    - NO summarization
    - NO reordering
    - ONLY formatting
    """

    # =========================
    # MAIN ENTRY
    # =========================
    def serialize(self, document: ContextDocument) -> str:

        lines: List[str] = []

        for idx, unit in enumerate(document.units):

            lines.append(self._format_unit(idx, unit))

        return "\n".join(lines)

    # =========================
    # FORMAT SINGLE UNIT
    # =========================
    def _format_unit(self, idx: int, unit: ContextUnit) -> str:

        header = f"[CTX {idx}]"

        body = unit.text

        meta_parts = []

        if unit.source_id is not None:
            meta_parts.append(f"id={unit.source_id}")

        if unit.score is not None:
            meta_parts.append(f"score={unit.score:.4f}")

        if unit.metadata:
            meta_parts.append(f"meta={unit.metadata}")

        meta = ""
        if meta_parts:
            meta = " | " + " ".join(meta_parts)

        return f"{header}{meta}\n{body}"