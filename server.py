import asyncio

from web import Server

if __name__ == '__main__':
    host = "localhost"
    port = 10005
    server = Server(host, port)

    asyncio.run(server.start())
