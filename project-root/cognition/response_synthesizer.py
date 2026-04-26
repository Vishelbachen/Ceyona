from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class SynthesizerInput:
    """
    Fully prepared data from upstream layers.
    NO raw reasoning here.
    """
    user_message: str
    intent: str
    llm_output: Optional[Any]
    context: Dict[str, Any]
    reasoning: Dict[str, Any]
    mode: str = "normal"


@dataclass(frozen=True)
class SynthesizedResponse:
    """
    Final structured response container.
    """
    text: str
    metadata: Dict[str, Any]


# =========================
# 🧠 RESPONSE SYNTHESIZER
# =========================
class ResponseSynthesizer:
    """
    FINAL assembly layer.

    RULES:
    - NO LLM calls
    - NO reasoning
    - NO retrieval
    - NO decisions
    - ONLY formatting + merging outputs
    """

    def synthesize(self, input: SynthesizerInput) -> SynthesizedResponse:

        # =========================
        # 1. EXTRACT CORE DATA
        # =========================
        llm_output = input.llm_output
        intent = input.intent
        context = input.context
        reasoning = input.reasoning

        # =========================
        # 2. BASE TEXT SELECTION
        # =========================
        if llm_output is None:
            base_text = "No response generated."
        else:
            base_text = self._extract_text(llm_output)

        # =========================
        # 3. MODE ADJUSTMENTS
        # =========================
        if input.mode == "safe_minimal":
            base_text = self._safe_trim(base_text)

        if intent == "system":
            base_text = self._system_format(base_text)

        # =========================
        # 4. OPTIONAL CONTEXT INJECTION
        # =========================
        if context.get("retrieval"):
            base_text = self._inject_retrieval_hint(base_text, context)

        # =========================
        # 5. METADATA BUILD
        # =========================
        metadata = {
            "intent": intent,
            "mode": input.mode,
            "has_llm_output": llm_output is not None,
            "retrieval_used": bool(context.get("retrieval")),
            "reasoning_confidence": reasoning.get("confidence"),
        }

        # =========================
        # 6. FINAL OUTPUT
        # =========================
        return SynthesizedResponse(
            text=base_text,
            metadata=metadata,
        )

    # =========================
    # 🔧 INTERNAL HELPERS
    # =========================
    def _extract_text(self, llm_output: Any) -> str:
        """
        Normalizes different LLM response formats.
        """
        if isinstance(llm_output, str):
            return llm_output

        if isinstance(llm_output, dict):
            return llm_output.get("text", str(llm_output))

        return str(llm_output)

    def _safe_trim(self, text: str) -> str:
        """
        Minimal safe mode response.
        """
        return text[:500]

    def _system_format(self, text: str) -> str:
        """
        System message formatting layer.
        """
        return f"[SYSTEM] {text}"

    def _inject_retrieval_hint(self, text: str, context: Dict[str, Any]) -> str:
        """
        Lightweight augmentation (NOT reasoning).
        """
        retrieval = context.get("retrieval", [])
        if not retrieval:
            return text

        return text + "\n\n(Additional context available)"