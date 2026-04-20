import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional, Literal


LogLevel = Literal["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]


class StructuredLogger:
    """
    Cognitive-grade structured logger.

    Designed for:
    - reasoning pipelines
    - model routing systems
    - self-healing loops
    - observability + debugging + analytics
    """

    def __init__(self):
        self.logger = logging.getLogger("app")
        self.logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))

        if not self.logger.handlers:
            self.logger.addHandler(handler)

    # -------------------------
    # CORE LOG METHOD
    # -------------------------
    def log(
        self,
        level: LogLevel,
        event: str,
        trace_id: Optional[str] = None,
        step: Optional[str] = None,
        model: Optional[str] = None,
        **data: Any
    ):
        payload: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "event": event,
            "trace_id": trace_id,
            "step": step,
            "model": model,
            "data": data
        }

        # 🧠 normalize empty payloads
        payload["data"] = payload["data"] or {}

        self.logger.info(json.dumps(payload, ensure_ascii=False))


# singleton
logger = StructuredLogger()