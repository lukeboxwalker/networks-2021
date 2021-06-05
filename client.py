"""
Module to start client.
"""
from concurrent.futures.thread import ThreadPoolExecutor

from web import Client


if __name__ == '__main__':
    host = "localhost"
    port = 10005
    client = Client(host, port)

    filepath = "data.py"

    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.submit(client.add_file, filepath)
        executor.submit(client.add_file, filepath)
        executor.submit(client.add_file, filepath)
        executor.submit(client.add_file, filepath)
        executor.submit(client.add_file, filepath)
        executor.submit(client.add_file, filepath)
