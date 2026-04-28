class Sentry:
    """
    Error capture abstraction (mock)
    """

    def capture_exception(self, error: Exception):
        print(f"[SENTRY] {type(error).__name__}: {str(error)}")