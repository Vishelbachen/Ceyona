import time


class Tracer:
    """
    Simple execution tracer
    """

    def __init__(self):
        self.spans = []

    def start_span(self, name: str):
        span = {"name": name, "start": time.time()}
        self.spans.append(span)
        return span

    def end_span(self, span: dict):
        span["end"] = time.time()
        span["duration"] = span["end"] - span["start"]