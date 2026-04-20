from dataclasses import dataclass
from typing import List


@dataclass
class EvaluationResult:
    is_valid: bool
    score: float
    issues: List[str]


class Evaluator:
    """
    Post-inference quality evaluator.
    Does NOT call LLM.
    """

    @staticmethod
    def evaluate(task_type: str, question: str, answer: str) -> EvaluationResult:
        issues = []

        if not answer or len(answer.strip()) < 5:
            return EvaluationResult(
                is_valid=False,
                score=0.0,
                issues=["empty_answer"]
            )

        text = answer.lower()

        score = 1.0

        # -------------------------
        # TASK-SPECIFIC CHECKS
        # -------------------------
        if task_type in ["math", "physics", "chemistry"]:
            if "=" not in text and "≈" not in text:
                issues.append("missing_result_expression")
                score -= 0.3

        if task_type in ["coding", "algorithm"]:
            if "def " not in text and "class " not in text:
                issues.append("no_code_structure")
                score -= 0.4

        if len(answer) < 30:
            issues.append("too_short")
            score -= 0.2

        score = max(0.0, score)

        return EvaluationResult(
            is_valid=(score >= 0.7),
            score=score,
            issues=issues
        )