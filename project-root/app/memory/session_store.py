from collections import defaultdict


class SessionStore:
    """
    In-memory session storage (MVP safe).
    """

    def __init__(self):
        self._data = defaultdict(list)

    def append_message(self, user_id: str, role: str, text: str):
        self._data[user_id].append({
            "role": role,
            "text": text
        })

    def get_history(self, user_id: str):
        return self._data.get(user_id, [])