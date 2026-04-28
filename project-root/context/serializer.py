from typing import Any, Dict, List, Optional
import json


class ContextSerializer:
    """
    AI Platform v4.7 — Context Serializer

    RESPONSIBILITY:
    - Convert structured context into LLM-ready serialized format
    - Ensure deterministic formatting (JSON / text)
    - Preserve all context content without modification

    STRICT RULES:
    - No summarization
    - No filtering or prioritization
    - No semantic interpretation
    - No LLM / memory / retrieval reasoning
    - No orchestration decisions
    """

    def __init__(self, format_type: str = "json"):
        self.format_type = format_type

    def _to_text(self, context: Dict[str, Any]) -> str:
        """
        Converts context into plain text format.
        """

        lines = [f"QUERY: {context.get('query', '')}"]

        for item in context.get("context", []):
            lines.append(
                f"[{item.get('source', 'unknown')}] {item.get('content', '')}"
            )

        return "\n".join(lines)

    def _to_json(self, context: Dict[str, Any]) -> str:
        """
        Converts context into JSON string.
        """

        return json.dumps(context, ensure_ascii=False)

    def serialize(self, context: Dict[str, Any]) -> str:
        """
        Serializes context for LLM input.
        """

        if self.format_type == "text":
            return self._to_text(context)

        return self._to_json(context)