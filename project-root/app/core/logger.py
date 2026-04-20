import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional, Literal


LogLevel = Literal["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]


class StructuredLogger:
    """
    Production-grade structured logger for AI pipeline.
    Safe for Railway, uvicorn workers, async systems.
    """

    def __init__(self):
        self.logger = logging.getLogger("app")

        # IMPORTANT: avoid duplicate handlers in Railway / uvicorn reload
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)

        self.logger.setLevel(logging.INFO)

    # -------------------------
    # LEVEL MAPPING (FIXED)
    # -------------------------
    def _log_by_level(self, level: LogLevel, message: str):
        match level:
            case "DEBUG":
                self.logger.debug(message)
            case "INFO":
                self.logger.info(message)
            case "WARN":
                self.logger.warning(message)
            case "ERROR":
                self.logger.error(message)
            case "CRITICAL":
                self.logger.critical(message)
            case _:
                self.logger.info(message)

    # -------------------------
    # SAFE SERIALIZER
    # -------------------------
    def _safe_json(self, obj: Any) -> Any:
        try:
            json.dumps(obj)
            return obj
        except Exception:
            return str(obj)

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
            "data": {
                k: self._safe_json(v)
                for k, v in (data or {}).items()
            }
        }

        self._log_by_level(level, json.dumps(payload, ensure_ascii=False))