import re


_COLLAPSE_WHITESPACE = re.compile(r"\s+")
_MAX_QUERY_CHARS = 512


def preprocess(text: str) -> str:
    """
    Normalize query text for retrieval.
    Pure function. No I/O. No semantic inference.
    """
    text = text.strip()
    text = _COLLAPSE_WHITESPACE.sub(" ", text)
    text = text[:_MAX_QUERY_CHARS]
    return text