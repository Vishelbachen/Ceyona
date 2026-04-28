from typing import Any, Dict, Optional, List
from datetime import datetime


class Logger:
    """
    AI Platform v4.7 — Logger

    RESPONSIBILITY:
    - Record system logs
    - Store structured events
    - Provide traceability for debugging and observability

    STRICT RULES:
    - No analytics or insights generation
    - No decision-making
    - No LLM / retrieval / memory usage
    - No filtering or interpretation of logs
    - No orchestration influence
    """

    def __init__(self):
        self._logs: List[Dict[str, Any]] = []

    def log(
        self,
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Appends a log entry.
        """

        log_id = f"log_{len(self._logs) + 1}"

        entry = {
            "id": log_id,
            "level": level,  # info | warning | error | debug
            "message": message,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._logs.append(entry)

        return log_id

    def get_logs(self, level: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns logs, optionally filtered by level.
        """

        if level is None:
            return self._logs

        return [
            log for log in self._logs
            if log["level"] == level
        ]

    def clear(self) -> None:
        """
        Clears all logs (admin/debug use only).
        """

        self._logs = []