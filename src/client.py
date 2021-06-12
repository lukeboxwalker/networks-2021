"""
Module to start client.
"""
import argparse
import os
from typing import List

from logger import logger
from web import Client


class Terminal:

    def __init__(self, ip: str, port: int):
        self.client = Client(ip, port)
        commands = {
            "add": self.__add_file,
            "check": self.__check_file,
            "get": self.__get_file,
        }

        while True:
            try:
                text: str = input()
                command: List[str] = text.split(" ")
                if command[0] == "stop":
                    break
                if not commands.__contains__(command[0]):
                    logger.warning("Invalid command type 'help' for help!")
                else:
                    commands.get(command[0]).__call__(command)
            except KeyboardInterrupt:
                break
        self.client.close()

    def __add_file(self, command: List[str]):
        if len(command) != 2:
            logger.error("Command '" + command[0] + "' needs one second argument the filepath!")
        else:
            self.client.add_file(command[1])

    def __check_file(self, command: List[str]):
        if len(command) != 2:
            logger.error("Command '" + command[0] +
                         "' needs one second argument the filepath or file hash!")
        else:
            if os.path.isfile(command[1]):
                self.client.check_file(command[1])
            else:
                self.client.check_hash(command[1])

    def __get_file(self, command: List[str]):
        if len(command) != 2:
            logger.error("Command '" + command[0] + "' needs one second argument the file hash!")
        else:
            self.client.get_file(command[1])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Client for Blockchain server.')
    parser.add_argument('--ip', type=str, help='The ip to connect to', required=True)
    parser.add_argument('--port', type=int, help='The server port to connect to', required=True)

    # parsing args
    args = parser.parse_args()

    Terminal(args.ip, args.port)
