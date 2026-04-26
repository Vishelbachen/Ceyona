from __future__ import annotations

import logging
from typing import Optional, Dict, Any


# =========================
# LOGGER SETUP
# =========================
class Logger:
    """
    ROLE:
    - unified logging interface for system-wide observability
    - provide structured logs for debugging + tracing

    STRICT RULES:
    - no business logic
    - no decision making
    - no side effects beyond logging
    """

    def __init__(self, name: str = "app"):
        self._logger = logging.getLogger(name)
        self._configure()

    # =========================
    # CONFIGURATION
    # =========================
    def _configure(self) -> None:

        if not self._logger.handlers:
            handler = logging.StreamHandler()

            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            )

            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    # =========================
    # INFO
    # =========================
    def info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:

        self._logger.info(self._format(message, context))

    # =========================
    # WARNING
    # =========================
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:

        self._logger.warning(self._format(message, context))

    # =========================
    # ERROR
    # =========================
    def error(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:

        self._logger.error(self._format(message, context))

    # =========================
    # DEBUG
    # =========================
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:

        self._logger.debug(self._format(message, context))

    # =========================
    # FORMATTER
    # =========================
    def _format(self, message: str, context: Optional[Dict[str, Any]]) -> str:

        if not context:
            return message

        return f"{message} | context={context}"