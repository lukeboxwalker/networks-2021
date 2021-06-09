"""
Module to start server.
"""

import argparse
from web import Server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='BlockChain server.')
    parser.add_argument('--ip', type=str, help='The ip of the server', required=True)
    parser.add_argument('--port', type=int, help='The port of the server', required=True)
    parser.add_argument('--workers', type=int, help='Number of worker threads running', default=1)

    # parsing args
    args = parser.parse_args()

    # start server
    server = Server(args.ip, args.port)
    server.start(max_workers=args.workers)
