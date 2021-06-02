import asyncio
import os

from main import create_blocks, load_file
from web import Client

if __name__ == '__main__':
    host = "localhost"
    port = 10005
    client = Client(host, port)

    filepath = "web.py"
    name = os.path.split(filepath)
    hashcode, blocks = create_blocks(load_file(filepath), name[1])

    asyncio.run(client.send_blocks(blocks))

    asyncio.run(client.check_hash(hashcode))



