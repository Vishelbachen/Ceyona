import re
from typing import Any


class ResponseFormatter:
    """
    Production-grade response formatter (v3 HARDENED FINAL).

    Goals:
    - deterministic output
    - safe LLM parsing
    - zero crash guarantee
    - Telegram-ready clean text
    - removes AI self-identification noise
    """

    # -------------------------
    # AI SELF PATTERNS (CLEANUP)
    # -------------------------
    AI_SELF_PATTERNS = [
        r"я\s*[-–—]\s*искусственн(ый|ого)\s*интеллект",
        r"i\s*am\s+an\s+ai",
        r"i\s*am\s+a\s+helpful\s+ai",
        r"as\s+an\s+ai\s+assistant",
        r"language\s+model",
        r"assistant\s+model",
    ]

    EMPTY_FALLBACK = "Empty response"

    # -------------------------
    # PUBLIC ENTRY
    # -------------------------
    @staticmethod
    def format(response: Any) -> str:

        if response is None:
            return ResponseFormatter.EMPTY_FALLBACK

        success = getattr(response, "success", None)
        data = getattr(response, "data", None)
        error = getattr(response, "error", None)

        # -------------------------
        # SUCCESS PATH
        # -------------------------
        if success is True:
            return ResponseFormatter._clean(
                ResponseFormatter._format_success(data)
            )

        # -------------------------
        # ERROR PATH
        # -------------------------
        if success is False:
            return ResponseFormatter._clean(
                ResponseFormatter._format_error(error)
            )

        # -------------------------
        # UNKNOWN STRUCTURE
        # -------------------------
        return ResponseFormatter._clean(
            ResponseFormatter._format_unknown(response)
        )

    # -------------------------
    # SUCCESS FORMAT
    # -------------------------
    @staticmethod
    def _format_success(data: Any) -> str:

        if data is None:
            return ResponseFormatter.EMPTY_FALLBACK

        if isinstance(data, dict):
            return str(
                data.get("text")
                or data.get("message")
                or data.get("data")
                or data
            )

        if isinstance(data, list):
            return "\n".join(str(x) for x in data if x is not None)

        text = str(data).strip()
        return text or ResponseFormatter.EMPTY_FALLBACK

    # -------------------------
    # ERROR FORMAT
    # -------------------------
    @staticmethod
    def _format_error(error: Any) -> str:

        if error is None:
            return "Unknown error"

        if isinstance(error, dict):
            code = error.get("code")
            message = error.get("message")

            if code and message:
                return f"[{code}] {message}"

            if message:
                return f"Error: {message}"

            return str(error)

        if isinstance(error, str):
            return error.strip() or "Unknown error"

        return str(error)

    # -------------------------
    # UNKNOWN STRUCTURE
    # -------------------------
    @staticmethod
    def _format_unknown(response: Any) -> str:

        data = getattr(response, "data", None)
        error = getattr(response, "error", None)

        if data is not None:
            return ResponseFormatter._format_success(data)

        if error is not None:
            return ResponseFormatter._format_error(error)

        return str(response)

    # -------------------------
    # CLEANING LAYER (SAFE PIPELINE OUTPUT)
    # -------------------------
    @staticmethod
    def _clean(text: str) -> str:

        if not text:
            return ResponseFormatter.EMPTY_FALLBACK

        cleaned = str(text)

        # normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # remove AI self-identification patterns
        for pattern in ResponseFormatter.AI_SELF_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        # final cleanup pass
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # safety fallback
        if not cleaned:
            return ResponseFormatter.EMPTY_FALLBACK

        return cleaned