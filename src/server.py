"""
Module to start server.
"""

import argparse
from web import Server

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='BlockChain server.')
    parser.add_argument('--ip', type=str, help='The ip of the server', required=True)
    parser.add_argument('--port', type=int, help='The port of the server', required=True)
    parser.add_argument('--fs', help='Server stores Blockchain in file system', action='store_true')

    # parsing args
    args = parser.parse_args()

    # start server
    server = Server(args.ip, args.port, in_memory=not args.fs)
    server.start()
    try:
        input()
    except KeyboardInterrupt:
        pass
    server.stop()
