"""
Module to start server.
"""

from logger import logger
from web import Server

if __name__ == '__main__':
    HOST = "localhost"
    PORT = 10005

    server = Server(HOST, PORT)
    server.start(max_workers=4)

    while True:
        try:
            command = input()
            if command == "stop":
                server.stop()
                break
            else:
                logger.warning("Unknown command type 'help' for help!")
        except KeyboardInterrupt:
            server.stop()
            break
