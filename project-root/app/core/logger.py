import logging
import json
from datetime import datetime


class StructuredLogger:
    def __init__(self, name="app"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)

        if not self.logger.handlers:
            self.logger.addHandler(handler)

    def log(self, level: str, event: str, **kwargs):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "event": event,
            "data": kwargs
        }
        self.logger.info(json.dumps(log_entry))


logger = StructuredLogger()