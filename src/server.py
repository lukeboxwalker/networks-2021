"""
Module to start server.
"""

from src.web import Server

if __name__ == '__main__':
    HOST = "localhost"
    PORT = 10005

    server = Server(HOST, PORT)
    server.start(max_workers=4)

    try:
        input()
        server.stop()
    except KeyboardInterrupt:
        server.stop()
