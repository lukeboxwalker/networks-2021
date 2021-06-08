"""
Module to start client.
"""
from concurrent.futures.thread import ThreadPoolExecutor

from web import Client

if __name__ == '__main__':
    IP = "localhost"
    PORT = 10005
    client = Client(IP, PORT)

    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.submit(client.add_file, "data.py")
        executor.submit(client.add_file, "web.py")
        executor.submit(client.add_file, "logger.py")
        executor.submit(client.add_file, "package.py")
        executor.submit(client.add_file, "server.py")
