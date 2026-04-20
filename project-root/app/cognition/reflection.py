import json
from datetime import datetime


class Reflection:
    """
    Logs system behavior for future learning (Supabase-ready).
    """

    @staticmethod
    def build_log(
        user_id: str,
        question: str,
        answer: str,
        model: str,
        evaluation
    ) -> dict:

        return {
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "question": question,
            "answer": answer,
            "model": model,
            "score": evaluation.score,
            "issues": evaluation.issues,
        }

    @staticmethod
    def serialize(log: dict) -> str:
        return json.dumps(log, ensure_ascii=False)