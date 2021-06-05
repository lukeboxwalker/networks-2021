"""
Module to start server.
"""

import asyncio

from web import Server

if __name__ == '__main__':
    HOST = "localhost"
    PORT = 10005
    server = Server(HOST, PORT)

    asyncio.run(server.start())
