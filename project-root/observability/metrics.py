class Metrics:
    """
    Simple in-memory metrics collector
    """

    def __init__(self):
        self.counters = {}

    def inc(self, metric: str, value: int = 1):
        self.counters[metric] = self.counters.get(metric, 0) + value

    def get(self, metric: str) -> int:
        return self.counters.get(metric, 0)