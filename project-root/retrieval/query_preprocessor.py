from __future__ import annotations

import re
from typing import Dict, Any


# =========================
# QUERY PREPROCESSOR
# =========================
class QueryPreprocessor:
    """
    ROLE:
    - normalize raw user query for retrieval systems
    - prepare stable input for BM25 + embeddings

    STRICT RULES:
    - NO semantics
    - NO intent detection
    - NO rewriting meaning
    - NO summarization
    """

    def __init__(self):
        # basic cleanup rules only
        self._multi_space_pattern = re.compile(r"\s+")
        self._control_chars = re.compile(r"[\x00-\x1f\x7f]")

    # =========================
    # MAIN ENTRY
    # =========================
    def process(self, query: str) -> str:

        query = self._basic_cleanup(query)
        query = self._normalize_whitespace(query)

        return query.strip()

    # =========================
    # CLEAN CONTROL CHARS
    # =========================
    def _basic_cleanup(self, query: str) -> str:

        # remove non-printable chars only
        return self._control_chars.sub("", query)

    # =========================
    # WHITESPACE NORMALIZATION
    # =========================
    def _normalize_whitespace(self, query: str) -> str:

        return self._multi_space_pattern.sub(" ", query)

    # =========================
    # OPTIONAL DEBUG HOOK
    # =========================
    def explain(self, query: str) -> Dict[str, Any]:

        cleaned = self._basic_cleanup(query)
        normalized = self._normalize_whitespace(cleaned)

        return {
            "original": query,
            "cleaned": cleaned,
            "normalized": normalized,
        }