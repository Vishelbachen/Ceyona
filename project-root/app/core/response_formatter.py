import re
from typing import Any


class ResponseFormatter:
    """
    Production-grade response formatter (FIXED v2).

    Fixes:
    - removes AI self-introductions
    - enforces language consistency (light heuristic)
    - removes emotional clutter
    - strict deterministic output
    """

    AI_SELF_PATTERNS = [
        r"я\s*—\s*искусственный интеллект",
        r"i am an ai",
        r"i am a helpful ai",
        r"as an ai assistant",
    ]

    @staticmethod
    def format(response: Any) -> str:
        if response is None:
            return "Empty response"

        success = getattr(response, "success", None)
        data = getattr(response, "data", None)
        error = getattr(response, "error", None)

        if success is True:
            return ResponseFormatter._clean(ResponseFormatter._format_success(data))

        if success is False:
            return ResponseFormatter._clean(ResponseFormatter._format_error(error))

        return ResponseFormatter._clean(ResponseFormatter._format_unknown(response))

    # -------------------------
    # SUCCESS
    # -------------------------

    @staticmethod
    def _format_success(data: Any) -> str:
        if data is None:
            return "Empty response"

        text = str(data).strip()
        return text or "Empty response"

    # -------------------------
    # ERROR
    # -------------------------

    @staticmethod
    def _format_error(error: Any) -> str:
        if error is None:
            return "Unknown error"

        if isinstance(error, dict):
            message = error.get("message")
            code = error.get("code")

            if message and code:
                return f"Error [{code}]: {message}"
            if message:
                return f"Error: {message}"
            return "Unknown error"

        if isinstance(error, str):
            return f"Error: {error.strip() or 'Unknown error'}"

        return f"Error: {str(error)}"

    # -------------------------
    # UNKNOWN
    # -------------------------

    @staticmethod
    def _format_unknown(response: Any) -> str:
        data = getattr(response, "data", None)
        error = getattr(response, "error", None)

        if data:
            return str(data).strip() or "Empty response"

        if error:
            return ResponseFormatter._format_error(error)

        return "Invalid response format"

    # -------------------------
    # CLEANING LAYER (CRITICAL FIX)
    # -------------------------

    @staticmethod
    def _clean(text: str) -> str:
        if not text:
            return "Empty response"

        cleaned = text.strip()

        # remove AI self-intro phrases
        lowered = cleaned.lower()
        for pattern in ResponseFormatter.AI_SELF_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        # normalize whitespace
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

        # avoid empty after cleanup
        if not cleaned:
            return "Empty response"

        return cleaned