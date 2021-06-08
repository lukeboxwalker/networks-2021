"""
Module to start client.
"""

from web import Client

if __name__ == '__main__':
    IP = "localhost"
    PORT = 10005
    client = Client(IP, PORT)
    client.add_file("data.py")
    client.check_file("data.py")

    client.close()
