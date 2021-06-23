"""
Module that holds the classes and functions needed for the client server communication.
"""
import os
import signal
import socket
import threading
from threading import Thread

from contextlib import closing
from typing import List, Tuple
from data import BlockChain, load_file, generate_file_hash, Block
from exceptions import DuplicateBlockError
from logger import logger, LogLevel
from package import PackageFactory, PackageHandler, PackageMode, Package, PackageId

MAX_PACKAGE_SIZE = 2  # 2 bytes or 0xFFFF or 65535


class Client:
    """
    Class that represents the client. The client performs tasks by communicating to a server.
    The host and port the client is connecting to need to be specified.
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

        self.thread = None
        self.stopped = threading.Event()

        # create PackageFactory in SERVER_MODE (creates packages that only a serer accepts)
        # create PackageHandler in CLIENT_MODE (can only handle packages directed to a client)
        self.package_factory = PackageFactory(PackageMode.SERVER_MODE)
        self.package_handler = PackageHandler(PackageMode.CLIENT_MODE, self.package_factory)

        # install package handlers for incoming packages
        self.package_handler.install(PackageId.LOG_TEXT, logger.log)
        self.package_handler.install(PackageId.SEND_FILE, self.handle_get_file)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)

    def __send_hash(self, package_id: PackageId, hashcode: str):
        """
        Sends a hash to the server with given package id.

        :param package_id: package id for the package that will be send.
        :param hashcode: to send to server.
        """
        package = self.package_factory.create_from_object(package_id, hashcode)
        send(package, self.sock)

    def __send_file(self, package_id: PackageId, blocks: List[Block]):
        """
        Sends a file in form of blocks to the server with given package id.

        :param package_id: package id for the package that will be send.
        :param blocks: the blocks of a file to send.
        """

        length = len(blocks)

        for i in range(length):
            package = self.package_factory.create_from_object(package_id, blocks[i])
            send(package, self.sock)
            logger.load(i + 1, length)
        logger.info(
            "Done sending " + str(len(blocks)) + " Block(s) file hash: '" + blocks[0].hash + "'")

    def __connect(self):
        """
        The client receive loop.
        Closes the program when server disconnected.
        """

        logger.info("Starting listener")
        while not self.stopped.isSet():
            if read(self.package_handler, self.sock):
                return

        if self.stopped.isSet():
            logger.info("Lost connection")
            os.kill(os.getpid(), signal.SIGINT)
        else:
            logger.info("Connection closed")

    def connect(self):
        """
        Connect to the server. Starts the listener thread for the client.
        """

        logger.info("Connecting to server " + str(self.host) + ":" + str(self.port))
        self.sock.connect((self.host, self.port))

        self.thread = Thread(target=self.__connect, args=(), name="ClientThread")
        self.thread.start()

    def close(self):
        """
        Closes the socket.
        """
        self.stopped.set()
        self.sock.close()

    def get_file(self, hashcode: str):
        """
        Loads a file from the server by the given hash value.

        :param hashcode: the file hash to restore the file from.
        """
        logger.info("Requesting file '" + hashcode + "'")
        self.__send_hash(PackageId.GET_FILE, hashcode)

    def check_hash(self, hashcode: str):
        """
        Sends the hashcode to the server and requests a check on the hash.

        :param hashcode: to send to server and check.
        """
        logger.info("Checking file '" + hashcode + "'")
        self.__send_hash(PackageId.HASH_CHECK, hashcode)

    def check_file(self, filepath: str):
        """
        Loads a file by its given filepath, splits it into chunks/blocks
        and requests a check on the file.

        :param filepath: to the file to send to server and check.
        """
        blocks = load_file(filepath)
        self.__send_hash(PackageId.HASH_CHECK, generate_file_hash(blocks))

    def add_file(self, filepath: str):
        """
        Loads a file by its given filepath, splits it into chunks/blocks of data and sends it
        to the server to store it.

        :param filepath: to the file to send to server.
        """
        if os.path.isfile(filepath):
            self.__send_file(PackageId.SEND_FILE, load_file(filepath))
        else:
            logger.error("The file '" + filepath + "' does not exist!")

    @staticmethod
    def handle_get_file(block: Block) -> List[Package]:
        """
        Creates a file for the block if not exists and writes
        the chunk stored in the block to the file.

        :param block: the block to write to the file.
        """
        logger.load(block.ordinal + 1, block.index_all)

        # write to file in binary mode
        with open("test" + block.filename, "ab") as file:
            file.write(block.chunk)

        return []


class Server:
    """
    Class that represents a server instance. The server stores files in a BlockChain data structure
    and handles new incoming client connections, that operate on the BlockChain.
    """

    def __init__(self, host: str, port: int):
        self.address = (host, port)
        self.block_chain = BlockChain()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self.sock.bind(self.address)

        self.thread = None
        self.stopped = threading.Event()

        # create PackageFactory in CLIENT_MODE (creates packages that only a client accepts)
        # create PackageHandler in SERVER_MODE (can only handle packages directed to a server)
        self.package_factory = PackageFactory(PackageMode.CLIENT_MODE)
        self.package_handler = PackageHandler(PackageMode.SERVER_MODE, self.package_factory)

        # install package handlers for incoming packages
        self.package_handler.install(PackageId.SEND_FILE, self.handle_add_block)
        self.package_handler.install(PackageId.HASH_CHECK, self.handle_check_hash)
        # self.package_handler.install(PackageId.FILE_CHECK, self.handle_check_file)
        self.package_handler.install(PackageId.GET_FILE, self.handle_request_file)

    def __handle_client(self, sock: socket.socket, addr: Tuple):
        logger.info("Incoming connection from: " + str(addr[0]) + ":" + str(addr[1]))

        while not self.stopped.isSet():
            if read(self.package_handler, sock):
                break
        sock.close()

        logger.info("Connection closed by: " + str(addr[0]) + ":" + str(addr[1]))

    def __start(self):
        """
        Starts a TCP server. The server runs in an infinite loop to handle
        incoming client connections.
        """

        logger.info("Starting server...")
        self.sock.listen()
        host = self.address[0]
        port = self.address[1]
        logger.info("Server started listening to " + host + ":" + str(port))

        while True:
            sock, addr = self.sock.accept()
            if self.stopped.isSet():
                sock.close()
                logger.info("Shutdown server...")
                self.sock.close()
                break
            name = "Client-" + str(addr[1])
            thread = Thread(target=self.__handle_client, args=(sock, addr,), name=name)
            thread.start()

        logger.info("Shutdown complete")

    def start(self):
        """
        Start the server in its own thread. Blocking the Main Thread until user KeyboardInterrupt
        the process.
        """
        name = "ServerThread"
        self.thread = Thread(target=self.__start, args=(), name=name)
        self.thread.start()
        try:
            input()
        except KeyboardInterrupt:
            pass
        logger.info("KeyboardInterrupt start server shutdown")
        self.stop()

    def stop(self):
        """
        Stops the server if it is running and joins the server thread until it is finished.
        """
        if self.thread and self.thread.is_alive():
            self.stopped.set()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
            with closing(sock):
                sock.connect(self.address)

    def handle_check_hash(self, hashcode: str) -> [Package]:
        """
        Checks the hash of a file in the BlockChain. Checks if the file with given hash
        exists and if the BlockChain is consistent.

        :param hashcode: the hashcode to check.
        :return: package to send back to the client.
        """

        exists, num = self.block_chain.file_exists(hashcode)
        if exists:
            message = "File with hash '" + hashcode + "' is stored in the BlockChain " \
                                                      "as a total of " + str(num) + " Block(s)"
            return [self.package_factory.create_log_package(LogLevel.INFO, message)]

        message = "File with hash '" + hashcode + "' is not stored in the BlockChain"
        return [self.package_factory.create_log_package(LogLevel.WARNING, message)]

    def handle_add_block(self, block: Block) -> [Package]:
        """
        Adding a new block to the BlockChain.

        :param block: the block to add to the BlockChain.
        :return: package to send back to the client.
        """
        if not block:
            return []

        try:
            hashcode = self.block_chain.add(block)
            logger.info("Added block with hash '" + hashcode + "' from file '" + block.filename)
            return []
        except DuplicateBlockError as error:
            logger.error("Error while adding Blocks to the BlockChain: " + str(error))
        return []

    def handle_request_file(self, hashcode: str) -> [Package]:
        """
        Requests a file by its hash value. Server checks if the BlockChain contains the file and if
        so sends it back to the client.

        :param hashcode: the hash of a file to restore.
        :return: package to send back to the client containing the file.
        """

        logger.info("Loading data for file with hash '" + hashcode + "'")
        blocks = self.block_chain.get(hashcode)

        packages = []

        if blocks:
            logger.info("Sending " + str(len(blocks)) + " Block(s) to the client")
        else:
            message = "No Blocks found for file hash '" + hashcode + "'"
            return [self.package_factory.create_log_package(LogLevel.WARNING, message)]

        hashcode = blocks[0].hash
        index_all = blocks[0].index_all
        filename = blocks[0].filename

        for block in blocks:
            cmd = Block(hashcode, index_all, block.ordinal, block.chunk, filename)
            packages.append(self.package_factory.create_from_object(PackageId.SEND_FILE, cmd))

        return packages


def read(package_handler: PackageHandler, sock: socket.socket) -> bool:
    """
    Reading data from given socket. Handles the incoming package by given PackageHandler
    and sends a package back.

    :param package_handler: to handle incoming packages.
    :param sock: the socket to communicate to.
    :return: if client closed the connection.
    """
    try:
        buf = sock.recv(MAX_PACKAGE_SIZE)
        if not buf:
            return True
        package_size = int.from_bytes(buf, byteorder="big")
        byte_package = sock.recv(package_size)

        out_packages: List[Package] = package_handler.handle(byte_package)

        # if out packages is not empty send them back.
        if out_packages:
            for package in out_packages:
                send(package, sock)
    except socket.error:
        return True
    return False


def send(package: Package, sock: socket.socket):
    """
    Sends a package to the given socket.

    :param package: the package to send.
    :param sock: the socket to write to.
    """
    try:
        size = len(package.raw)
        sock.sendall(size.to_bytes(MAX_PACKAGE_SIZE, byteorder="big") + package.raw)
    except OverflowError:
        logger.error("Can't send package. Package size to large!")
