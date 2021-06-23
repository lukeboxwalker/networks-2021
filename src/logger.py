"""
Module that holds the classes and functions needed for the logger.
"""

import threading
from datetime import datetime

from enum import Enum


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


class Logger:
    """
    Class to log text to the console.
    """

    @staticmethod
    def __format_print(msg, log_level, end="\n"):
        now = datetime.now()
        ctime = now.strftime("%Y-%m-%d %H:%M:%S")

        def spaces(max_n, string) -> str:
            return " " * ((max_n - len(string)) if len(string) < max_n else 0)

        name = log_level.name + spaces(7, log_level.name)
        thread = threading.current_thread().name + spaces(15, threading.current_thread().name)
        text = "{} [{}] [{}]  {}".format(ctime, name, thread, msg)
        print(text, end=end)

    def log(self, log_result: LogResult):
        """
        Logs a LogResult. Logs on the log level given by the LogResult.
        If the log level is unknown nothing will be logged.

        :param log_result: the LogResult log to the console.
        """
        self.__format_print(log_result.message, log_result.log_level)

    def info(self, message):
        """
        Logs a message with log level INFO to the console.

        :param message: message to log/print.
        """
        self.__format_print(message, LogLevel.INFO)

    def load(self, iteration, total, decimals=1):
        """
        Creates a loading bar. Print it to the console.

        :param iteration: the current position of the bar
        :param total: the total amount of the bar
        :param decimals: decimal places
        """
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filled_length = int(100 * iteration // total)
        tiles = '█' * filled_length + '-' * (100 - filled_length)
        if iteration == total:
            self.__format_print(f'\r{"Progress"} |{tiles}| {percent}% {"Complete"}', LogLevel.INFO)
        else:
            self.__format_print(f'\r{"Progress"} |{tiles}| {percent}% {"Complete"}', LogLevel.INFO,
                                end="")

    def warning(self, message):
        """
        Logs a message with log level WARNING to the console.

        :param message: message to log/print.
        """
        self.__format_print(message, LogLevel.WARNING)

    def error(self, message):
        """
        Logs a message with log level ERROR to the console.

        :param message: message to log/print.
        """
        self.__format_print(message, LogLevel.ERROR)


# Logger object to log to console
logger = Logger()
