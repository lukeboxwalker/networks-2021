import logging


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


logger = logging.getLogger("Application")
logger.setLevel(logging.INFO)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(CustomFormatter("%(asctime)s [%(levelname)-8s]  %(message)s"))

logger.addHandler(console)
