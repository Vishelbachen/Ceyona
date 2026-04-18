import logging
import json
from datetime import datetime


class StructuredLogger:
    def __init__(self):
        self.logger = logging.getLogger("app")
        self.logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))

        if not self.logger.handlers:
            self.logger.addHandler(handler)

    def log(self, level: str, event: str, **data):
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "event": event,
            "data": data
        }
        self.logger.info(json.dumps(payload))


logger = StructuredLogger()