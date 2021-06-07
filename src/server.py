"""
Module to start server.
"""
from typing import Callable

from web import Server


def wait_on_interrupt(callback: Callable):
    """
    Waits for a user input to call the given callback.

    :param callback: the callback to call in case of a user input.
    """
    try:
        input()
    except KeyboardInterrupt:
        pass
    callback()


if __name__ == '__main__':
    HOST = "localhost"
    PORT = 10005

    server = Server(HOST, PORT)
    server.start(max_workers=4)

    wait_on_interrupt(callback=server.stop)
