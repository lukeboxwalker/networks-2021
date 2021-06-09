"""
Module to start client.
"""
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import closing

from web import Client

IP = "localhost"
PORT = 10005


def send_and_check(filepath):
    """
    Starts a client and adds a file to the server. Then checks if the file exists on the server.
    :param filepath: to add/check
    """
    with closing(Client(IP, PORT)) as client:
        client.add_file(filepath)
        client.check_file(filepath)


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.submit(send_and_check, "data.py")
        executor.submit(send_and_check, "web.py")
        executor.submit(send_and_check, "package.py")
        executor.submit(send_and_check, "logger.py")
        executor.submit(send_and_check, "server.py")
