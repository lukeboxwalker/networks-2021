import asyncio

from web import Client

if __name__ == '__main__':
    host = "localhost"
    port = 10005
    client = Client(host, port)

    filepath = "887bb084c63b053c897f4ee8606c9f02.jpg"
    asyncio.run(client.get_file("ae66f3e6d12c0b1f035ca587fa29de86d3a25fa4332fabad3bf3d40ffe575016"))
