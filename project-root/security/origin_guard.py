class OriginGuard:
    """
    Controls allowed request origins
    """

    def __init__(self):
        self.allowed_origins = {"localhost", "127.0.0.1"}

    def is_allowed(self, origin: str) -> bool:
        return origin in self.allowed_origins