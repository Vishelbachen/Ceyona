import re


def preprocess(query: str) -> str:
    """
    Clean and normalize query text before retrieval.
    Deterministic. No I/O. No semantic inference.
    """
    query = query.strip()
    query = re.sub(r"\s+", " ", query)
    query = re.sub(r"[^\w\s\?\!\.\,\-]", "", query)
    return query[:512]