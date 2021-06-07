"""
Module to start server.
"""

from web import Server


if __name__ == '__main__':
    IP = "localhost"
    PORT = 10005

    server = Server(IP, PORT)
    server.start(max_workers=4)
