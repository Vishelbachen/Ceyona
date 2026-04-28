from dataclasses import dataclass
from typing import List


@dataclass
class Context:
    user_id: str
    query: str
    documents: List[str]