import asyncio

from web import Client

if __name__ == '__main__':
    host = "localhost"
    port = 10005
    client = Client(host, port)

    filepath = "data.py"
    asyncio.run(client.get_file("4c2a71bc93db6649d0aa0ba18b682833c939f53034fbc9e5d73b2e36661890fc"))
