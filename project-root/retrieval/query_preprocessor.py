import re


def preprocess(text: str) -> str:
    """
    Normalize query text before embedding.
    Deterministic. No I/O.
    """
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = text[:512]   # hard cap for embedding models
    return text