import asyncio
import json
import pickle

from data import BlockCMD
from transfer import Package, PackageId
from web import Client

if __name__ == '__main__':
    host = "localhost"
    port = 10005
    client = Client(host, port)

    filepath = "887bb084c63b053c897f4ee8606c9f02.jpg"
    asyncio.run(client.add_file(filepath))


