"""
Module that holds the classes and functions needed for the logger.
"""

import colorama
import logging

from enum import Enum
from typing import Callable, Dict
from colorama import Fore, Style


class LogLevel(Enum):
    """
    Enum to represent the different log levels.
    """
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LogResult:
    """
    Class to hold data for a log operation. Stores the log level on which the stored
    text should be logged.
    """
    def __init__(self, log_level: LogLevel, message: str):
        self.__log_level = log_level
        self.__message = message

    @property
    def log_level(self):
        """
        Property function to ensure that the log level is a read only variable.

        :return: the log level.
        """
        return self.__log_level

    @property
    def message(self):
        """
        Property function to ensure that the message is a read only variable.

        :return: the message as a string.
        """
        return self.__message


class ColorFormatter(logging.Formatter):
    """
    Class to format log text by applying color to the string.
    """

    def __init__(self, msg):
        logging.Formatter.__init__(self, msg)

        # color codes for different log levels
        self.colors = {
            "WARNING": Fore.LIGHTYELLOW_EX,
            "INFO": Fore.WHITE,
            "ERROR": Fore.LIGHTRED_EX
        }

    def format(self, record):
        """
        Formats a log record by adding color to it. The color is determined by the log level.
        The format ends with a color reset "\033[0m".

        :param record: the record to format
        :return: the formatted string.
        """
        name = record.levelname
        return self.colors[name] + logging.Formatter.format(self, record) + Style.RESET_ALL


class Logger:
    """
    Class to log text to the console.
    """
    def __init__(self):
        # Setup logger
        self.logger = logging.getLogger("Application")
        self.logger.setLevel(logging.INFO)

        # Init console stream handler
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)

        # Using colored formatter
        format_string = "%(asctime)s [%(levelname)-7s] [%(threadName)-22s]  %(message)s"
        console.setFormatter(ColorFormatter(format_string))

        self.logger.addHandler(console)

        # Init dictionary to log to different levels
        self.log_levels: Dict[LogLevel, Callable] = {
            LogLevel.INFO: self.logger.info,
            LogLevel.WARNING: self.logger.warning,
            LogLevel.ERROR: self.logger.error
        }

    def log(self, log_result: LogResult):
        """
        Logs a LogResult. Logs on the log level given by the LogResult.
        If the log level is unknown nothing will be logged.

        :param log_result: the LogResult log to the console.
        """
        if self.log_levels.__contains__(log_result.log_level):
            self.log_levels.get(log_result.log_level)(log_result.message)

    def info(self, message):
        """
        Logs a message with log level INFO to the console.

        :param message: message to log/print.
        """
        self.logger.info(message)

    def warning(self, message):
        """
        Logs a message with log level WARNING to the console.

        :param message: message to log/print.
        """
        self.logger.warning(message)

    def error(self, message):
        """
        Logs a message with log level ERROR to the console.

        :param message: message to log/print.
        """
        self.logger.error(message)


colorama.init()

# Logger object to log to console
logger = Logger()
