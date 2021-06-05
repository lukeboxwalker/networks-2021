"""
Module to start client.
"""

import asyncio

from web import Client

if __name__ == '__main__':
    HOST = "localhost"
    PORT = 10005
    client = Client(HOST, PORT)

    FILEPATH = "data.py"
    asyncio.run(client.add_file(FILEPATH))
