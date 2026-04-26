from __future__ import annotations

from typing import Dict, Any, List, Optional


# =========================
# RESPONSE SYNTHESIZER
# =========================
class ResponseSynthesizer:
    """
    ROLE:
    - merge outputs from agents + consensus engine
    - format final response structure
    - normalize output for transport layer

    STRICT RULES:
    - no reasoning
    - no agent selection
    - no orchestration decisions
    - no LLM routing
    """

    # =========================
    # MAIN ENTRYPOINT
    # =========================
    def synthesize(
        self,
        consensus_result: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        return {
            "response": self._extract_response(consensus_result),
            "meta": self._build_meta(consensus_result, metadata or {}),
        }

    # =========================
    # RESPONSE EXTRACTION
    # =========================
    def _extract_response(self, consensus_result: Dict[str, Any]) -> Any:

        # safe fallback
        if not consensus_result:
            return {
                "text": "",
                "status": "empty_response",
            }

        return {
            "text": consensus_result.get("output"),
            "agent": consensus_result.get("agent"),
            "confidence": consensus_result.get("confidence"),
        }

    # =========================
    # META BUILDER
    # =========================
    def _build_meta(
        self,
        consensus_result: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:

        context = consensus_result.get("context", {})

        return {
            "status": consensus_result.get("status", "unknown"),
            "agents_used": context.get("agents_used", []),
            "agent_count": context.get("count", 0),
            "extra": metadata,
        }