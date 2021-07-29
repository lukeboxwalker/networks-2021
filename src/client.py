"""
Module to start client.
"""
import argparse
import os
import socket
from typing import List

from logger import logger
from web import Client


class Terminal:
    """
    Class to interact as a user with the client functions.
    """

    def __init__(self, ip: str, port: int):
        self.client = Client(ip, port)
        try:
            self.client.connect()
        except socket.error:
            logger.error("No connection found!")
            self.client.close()
            return
        commands = {
            "add": self.add_file,  # adding a new file
            "check": self.check,  # check if a file exists
            "get": self.get_file,  # getting a file back
        }

        if not self.client.running():
            return

        # Client main loop. Waiting for user commands
        while self.client.running():
            try:
                text: str = input()
                command: List[str] = text.split(" ")
                if command[0] == "stop":
                    break
                if command[0] == "help":
                    print("\n"
                          "stop                 | closes the client\n"
                          "help                 | returns this help page\n"
                          "add <file>           | sends the file to the server\n"
                          "check <file or hash> | checks if the file is stored in the Blockchain\n"
                          "check                | checks the consistency of the Blockchain\n"
                          "get <hash>           | loads the file stored for the hash\n")
                    continue
                if not commands.__contains__(command[0]):
                    logger.warning("Invalid command type 'help' for help!")
                else:
                    commands.get(command[0]).__call__(command)
            except KeyboardInterrupt:
                break
        self.client.close()

    def add_file(self, command: List[str]):
        """
        Adds a new file to the server

        :param command: command that contains the file to send.
        """
        if len(command) != 2:
            logger.error("Command '" + command[0] + "' needs one second argument the filepath!")
        else:
            self.client.add_file(command[1])

    def check(self, command: List[str]):
        """
        Checks if a file exists on the server.

        :param command: command that contains the hash or file to check.
        """
        if len(command) != 2:
            if len(command) == 1:
                self.client.full_check()
            else:
                logger.error("Command '" + command[
                    0] + "' needs one second argument the filepath or file hash!")
        else:
            if os.path.isfile(command[1]):
                self.client.check_file(command[1])
            else:
                self.client.check_hash(command[1])

    def get_file(self, command: List[str]):
        """
        Request a file from the server.

        :param command: command that contains the hash to request.
        """
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
