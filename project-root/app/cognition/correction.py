from typing import Any, List, Optional


class Corrector:
    """
    Repairs low-quality LLM outputs.

    IMPORTANT:
    - Does NOT change intent
    - Does NOT re-route model
    - Only improves existing answer quality
    """

    # -------------------------
    # DECISION GATE
    # -------------------------
    @staticmethod
    def should_correct(evaluation: Any) -> bool:
        """
        Safe evaluation gate.

        Supports:
        - dataclass EvaluationResult
        - dict fallback
        """
        if evaluation is None:
            return False

        is_valid = getattr(evaluation, "is_valid", None)

        if is_valid is None and isinstance(evaluation, dict):
            is_valid = evaluation.get("is_valid", True)

        return not bool(is_valid)

    # -------------------------
    # PROMPT BUILDER
    # -------------------------
    @staticmethod
    def build_repair_prompt(
        question: str,
        answer: str,
        issues: List[str],
        context: Optional[str] = None
    ) -> str:

        question = (question or "").strip()
        answer = (answer or "").strip()
        issues = issues or []

        context_block = ""
        if context:
            context_block = f"\nCONTEXT:\n{context.strip()}\n"

        return (
            "You are improving an existing answer.\n"
            "You MUST preserve original intent.\n"
            "You MUST fix errors without adding unnecessary content.\n\n"
            f"QUESTION:\n{question}\n\n"
            f"{context_block}"
            f"CURRENT ANSWER:\n{answer}\n\n"
            f"ISSUES:\n{', '.join(issues) if issues else 'general_quality_issue'}\n\n"
            "RULES:\n"
            "- fix logical errors\n"
            "- improve clarity\n"
            "- remove contradictions\n"
            "- keep answer concise\n"
            "- do NOT change topic\n"
        )