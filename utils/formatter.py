from typing import Dict, Any


class Formatter:
    @staticmethod
    def ai_response(text: str, meta: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Standard AI response format for all outputs
        """

        return {
            "response": text,
            "meta": meta or {},
            "status": "success"
        }

    @staticmethod
    def error(message: str) -> Dict[str, Any]:
        return {
            "response": None,
            "error": message,
            "status": "error"
        }