from datetime import datetime
from typing import Dict, Any


class Reflection:
    """
    Stores inference experience for future learning.
    Ready for Supabase / DB integration.
    """

    @staticmethod
    def build_event(
        user_id: str,
        question: str,
        answer: str,
        model: str,
        task_type: str,
        evaluation: Any,
        trace_id: str | None = None
    ) -> Dict[str, Any]:

        return {
            "user_id": user_id,
            "question": question,
            "answer": answer,
            "model": model,
            "task_type": task_type,

            "score": getattr(evaluation, "score", 0.0),
            "is_valid": getattr(evaluation, "is_valid", False),
            "issues": getattr(evaluation, "issues", []),

            "trace_id": trace_id,
            "created_at": datetime.utcnow().isoformat()
        }