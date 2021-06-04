import logging
from enum import Enum
from typing import Callable, Dict


# Log levels
class LogLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LogResult:
    def __init__(self, log_level: LogLevel, message: str):
        self.log_level = log_level
        self.message = message


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

        self.log_levels: Dict[LogLevel, Callable] = {
            LogLevel.INFO: self.logger.info,
            LogLevel.WARNING: self.logger.warning,
            LogLevel.ERROR: self.logger.error
        }

    def log(self, log_result: LogResult):
        if self.log_levels.__contains__(log_result.log_level):
            self.log_levels.get(log_result.log_level)(log_result.message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)


logger = Logger()
