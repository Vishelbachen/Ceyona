import re
from typing import Optional


class Helpers:

    @staticmethod
    def extract_city(text: str) -> Optional[str]:
        """
        Simple city extraction (used in tools layer)
        """
        words = text.split()
        return words[-1] if words else None

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Basic normalization for AI input
        """
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def safe_int(value, default=0) -> int:
        try:
            return int(value)
        except:
            return default