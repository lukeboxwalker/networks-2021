import asyncio

from web import Client

if __name__ == '__main__':
    host = "localhost"
    port = 10005
    client = Client(host, port)

    filepath = "data.py"
    asyncio.run(client.add_file(filepath))
