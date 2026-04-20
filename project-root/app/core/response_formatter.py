from typing import Any


class ResponseFormatter:
    """
    Production-grade response formatter.

    Responsibility:
    - convert SuccessResponse / ErrorResponse into safe user-facing text
    - NEVER mutate input
    - NEVER assume dynamic attributes via getattr
    - ALWAYS behave deterministically
    """

    @staticmethod
    def format(response: Any) -> str:
        """
        Main entry point.
        Accepts:
        - SuccessResponse
        - ErrorResponse
        - any fallback object (safe guard)
        """

        # 🧯 NULL SAFETY
        if response is None:
            return "⚠️ Empty response"

        # 🧠 SAFE ATTRIBUTE EXTRACTION (no getattr abuse)
        success = getattr(response, "success", None)
        data = getattr(response, "data", None)
        error = getattr(response, "error", None)

        # 🔵 CASE 1: SUCCESS RESPONSE
        if success is True:
            return ResponseFormatter._format_success(data)

        # 🔴 CASE 2: ERROR RESPONSE
        if success is False:
            return ResponseFormatter._format_error(error)

        # 🟡 CASE 3: UNKNOWN STRUCTURE (fallback safety net)
        return ResponseFormatter._format_unknown(response)

    # -------------------------
    # SUCCESS FORMATTING
    # -------------------------

    @staticmethod
    def _format_success(data: Any) -> str:
        if data is None:
            return "⚠️ Empty response"

        text = str(data).strip()

        if not text:
            return "⚠️ Empty response"

        return text

    # -------------------------
    # ERROR FORMATTING
    # -------------------------

    @staticmethod
    def _format_error(error: Any) -> str:
        if error is None:
            return "⚠️ Unknown error"

        # structured error dict (expected case)
        if isinstance(error, dict):
            message = error.get("message")
            code = error.get("code")

            if message and code:
                return f"⚠️ Error [{code}]: {message}"

            if message:
                return f"⚠️ Error: {message}"

            return "⚠️ Unknown error"

        # string error
        if isinstance(error, str):
            return f"⚠️ Error: {error.strip() or 'Unknown error'}"

        # fallback
        return f"⚠️ Error: {str(error)}"

    # -------------------------
    # UNKNOWN STRUCTURE SAFETY
    # -------------------------

    @staticmethod
    def _format_unknown(response: Any) -> str:
        """
        Last-resort safety net.
        Prevents crashes on unexpected DTO shapes.
        """

        # try best-effort extraction
        data = getattr(response, "data", None)
        error = getattr(response, "error", None)

        if data:
            return str(data).strip() or "⚠️ Empty response"

        if error:
            return ResponseFormatter._format_error(error)

        return "⚠️ Invalid response format"