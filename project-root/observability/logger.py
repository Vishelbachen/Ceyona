import logging


class Logger:
    """
    Central logging service
    """

    def __init__(self):
        self.logger = logging.getLogger("v4_7")
        self.logger.setLevel(logging.INFO)

    def info(self, msg: str):
        self.logger.info(msg)

    def error(self, msg: str):
        self.logger.error(msg)