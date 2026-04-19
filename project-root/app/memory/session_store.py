from collections import defaultdict, deque
from typing import Dict, List


class Message:
    def __init__(self, role: str, text: str):
        self.role = role
        self.text = text


class SessionStore:
    """
    In-memory session storage (MVP version).
    No DB, no Redis — pure RAM state.
    """

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self.sessions: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_messages))

    def add_message(self, user_id: str, role: str, text: str):
        self.sessions[user_id].append(Message(role, text))

    def get_history(self, user_id: str) -> List[Message]:
        return list(self.sessions[user_id])

    def clear(self, user_id: str):
        self.sessions.pop(user_id, None)