"""
Module to start client.
"""
import argparse

from web import Client


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='BlockChain server.')
    parser.add_argument('--ip', type=str, help='The ip to connect to', required=True)
    parser.add_argument('--port', type=int, help='The server port to connect to', required=True)

    # parsing args
    args = parser.parse_args()

    client = Client(args.ip, args.port)

    # pylint: disable=fixme
    # TODO implement interactive cli commands
    client.add_file("data.py")
    client.check_file("data.py")

    client.close()
