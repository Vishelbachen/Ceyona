from dataclasses import dataclass
from typing import List


# -------------------------
# RESULT MODEL
# -------------------------
@dataclass
class EvaluationResult:
    is_valid: bool
    score: float
    issues: List[str]


class Evaluator:
    """
    Post-inference quality evaluator.

    IMPORTANT:
    - NO LLM calls
    - deterministic scoring
    - safe for retry loop gating
    """

    # -------------------------
    # MAIN ENTRY
    # -------------------------
    @staticmethod
    def evaluate(task_type: str, question: str, answer: str) -> EvaluationResult:

        issues: List[str] = []

        task_type = (task_type or "general").lower()
        question = (question or "").strip()
        answer = (answer or "").strip()

        # -------------------------
        # EMPTY CHECK (HARD FAIL)
        # -------------------------
        if not answer:
            return EvaluationResult(
                is_valid=False,
                score=0.0,
                issues=["empty_answer"]
            )

        score = 1.0
        text = answer.lower()

        # -------------------------
        # LENGTH SIGNAL
        # -------------------------
        if len(answer) < 30:
            issues.append("too_short")
            score -= 0.2

        # -------------------------
        # MATH / SCIENCE
        # -------------------------
        if task_type in ["math", "physics", "chemistry"]:

            has_math_signal = any(sym in text for sym in ["=", "≈", "+", "-", "∫", "√"])

            if not has_math_signal:
                issues.append("missing_math_signal")
                score -= 0.3

        # -------------------------
        # CODING
        # -------------------------
        if task_type in ["coding", "algorithm"]:

            code_signals = ["def ", "class ", "import ", "return ", "{", "}", "=>"]

            if not any(sig in text for sig in code_signals):
                issues.append("no_code_structure")
                score -= 0.4

        # -------------------------
        # REASONING QUALITY (LIGHT HEURISTIC)
        # -------------------------
        if task_type in ["reasoning", "logic", "proof"]:

            if len(answer) > 200 and "because" not in text:
                issues.append("weak_reasoning_signal")
                score -= 0.2

        # -------------------------
        # FINAL SCORE NORMALIZATION
        # -------------------------
        score = max(0.0, min(1.0, score))

        return EvaluationResult(
            is_valid=(score >= 0.7),
            score=score,
            issues=issues
        )