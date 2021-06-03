import logging
from typing import Callable, Dict

# Log levels
INFO = b'0'
WARNING = b'1'
ERROR = b'2'


class CustomFormatter(logging.Formatter):
    def __init__(self, msg):
        logging.Formatter.__init__(self, msg)
        self.colors = {
            "WARNING": "\033[33m",
            "INFO": "\033[2m",
            "ERROR": "\033[31m"
        }

    def format(self, record):
        name = record.levelname
        return self.colors[name] + logging.Formatter.format(self, record) + "\033[0m"


class Logger:
    def __init__(self):
        self.logger = logging.getLogger("Application")
        self.logger.setLevel(logging.INFO)

        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(CustomFormatter("%(asctime)s [%(levelname)-8s]  %(message)s"))

        self.logger.addHandler(console)

        self.log_levels: Dict[bytes, Callable] = {
            INFO: self.logger.info,
            WARNING: self.logger.warning,
            ERROR: self.logger.error
        }

    def log(self, log_level: bytes, message: str):
        if self.log_levels.__contains__(log_level):
            self.log_levels.get(log_level)(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)


logger = Logger()
