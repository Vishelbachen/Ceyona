from datetime import datetime, timezone
from typing import Dict, Any, Optional


class Reflection:
    """
    Stores inference experience for future learning.

    Role:
    - lightweight telemetry / cognition logging
    - Supabase-ready event builder
    - no side effects (pure function)
    """

    # -------------------------
    # EVENT BUILDER
    # -------------------------
    @staticmethod
    def build_event(
        user_id: str,
        question: str,
        answer: str,
        model: str,
        task_type: str,
        evaluation: Any,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:

        question = (question or "").strip()
        answer = (answer or "").strip()

        return {
            # -------------------------
            # CORE IDENTITY
            # -------------------------
            "user_id": user_id,
            "trace_id": trace_id,

            # -------------------------
            # INPUT / OUTPUT
            # -------------------------
            "question": question,
            "answer": answer,

            # -------------------------
            # MODEL METADATA
            # -------------------------
            "model": model,
            "task_type": task_type,

            # -------------------------
            # EVALUATION METRICS (SAFE EXTRACTION)
            # -------------------------
            "score": getattr(evaluation, "score", 0.0) if evaluation else 0.0,
            "is_valid": getattr(evaluation, "is_valid", False) if evaluation else False,
            "issues": getattr(evaluation, "issues", []) if evaluation else [],

            # -------------------------
            # TIMESTAMP (TIMEZONE SAFE)
            # -------------------------
            "created_at": datetime.now(timezone.utc).isoformat()
        }