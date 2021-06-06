"""
Module to start server.
"""
import threading

from logger import logger
from web import Server


if __name__ == '__main__':
    HOST = "localhost"
    PORT = 10005

    server = Server(HOST, PORT)
    server_thread = threading.Thread(target=server.start, args=(4,), name="ServerThread")
    server_thread.start()

    while True:
        command = input()
        if command == "stop":
            server.stop()
            break
        else:
            logger.info("Unknown command type 'help' for help")

    if server_thread.is_alive():
        server_thread.join()


