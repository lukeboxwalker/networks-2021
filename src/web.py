"""
Module that holds the classes and functions needed for the client server communication.
"""
import socket
import threading

from concurrent.futures.thread import ThreadPoolExecutor
from typing import List, Tuple
from src.data import BlockChain, BlockCMD, load_file, generate_hash
from src.exceptions import BlockSectionInconsistentError, BlockInsertionError
from src.logger import logger, LogLevel
from src.package import PackageFactory, PackageHandler, PackageMode, Package, PackageId

BUFF_SIZE = 1024


class Client:
    """
    Class that represents the client. The client performs tasks by communicating to a server.
    The host and port the client is connecting to need to be specified.
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

        # create PackageFactory in SERVER_MODE (creates packages that only a serer accepts)
        # create PackageHandler in CLIENT_MODE (can only handle packages directed to a client)
        self.package_factory = PackageFactory(PackageMode.SERVER_MODE)
        self.package_handler = PackageHandler(PackageMode.CLIENT_MODE, self.package_factory)

        # install package handlers for incoming packages
        self.package_handler.install(PackageId.LOG_TEXT, logger.log)
        self.package_handler.install(PackageId.SEND_FILE, handle_get_file)

    def __send_hash(self, package_id: PackageId, hashcode: str):
        """
        Sends a hash to the server with given package id.

        :param package_id: package id for the package that will be send.
        :param hashcode: to send to server.
        """
        logger.info("Connecting to server " + str(self.host) + ":" + str(self.port))
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        client_sock.connect((self.host, self.port))

        package = self.package_factory.create_from_object(package_id, hashcode)

        send(package, client_sock)
        read(self.package_handler, client_sock)

        client_sock.close()

    def __send_file(self, package_id: PackageId, blocks: List[BlockCMD]):
        """
        Sends a file in form of blocks to the server with given package id.

        :param package_id: package id for the package that will be send.
        :param blocks: the blocks of a file to send.
        """
        logger.info("Connecting to server " + str(self.host) + ":" + str(self.port))
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        client_sock.connect((self.host, self.port))

        package = self.package_factory.create_from_object(package_id, blocks)

        logger.info("Sending " + str(len(blocks)) + " Block(s) to the server")
        send(package, client_sock)
        read(self.package_handler, client_sock)

        client_sock.close()

    def get_file(self, hashcode: str):
        """
        Loads a file from the server by the given hash value.

        :param hashcode: the file hash to restore the file from.
        """
        self.__send_hash(PackageId.GET_FILE, hashcode)

    def check_hash(self, hashcode: str):
        """
        Sends the hashcode to the server and requests a check on the hash.

        :param hashcode: to send to server and check.
        """
        self.__send_hash(PackageId.HASH_CHECK, hashcode)

    def check_file(self, filepath: str):
        """
        Loads a file by its given filepath, splits it into chunks/blocks
        and requests a check on the file.

        :param filepath: to the file to send to server and check.
        """
        self.__send_file(PackageId.FILE_CHECK, load_file(filepath))

    def add_file(self, filepath: str):
        """
        Loads a file by its given filepath, splits it into chunks/blocks of data and sends it
        to the server to store it.

        :param filepath: to the file to send to server.
        """
        self.__send_file(PackageId.SEND_FILE, load_file(filepath))


class Server:
    """
    Class that represents a server instance. The server stores files in a BlockChain data structure
    and handles new incoming client connections, that operate on the BlockChain.
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.block_chain = BlockChain()

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self.server_socket.bind((self.host, self.port))

        self.thread = None

        # create PackageFactory in CLIENT_MODE (creates packages that only a client accepts)
        # create PackageHandler in SERVER_MODE (can only handle packages directed to a server)
        self.package_factory = PackageFactory(PackageMode.CLIENT_MODE)
        self.package_handler = PackageHandler(PackageMode.SERVER_MODE, self.package_factory)

        # install package handlers for incoming packages
        self.package_handler.install(PackageId.SEND_FILE, self.handle_add_file)
        self.package_handler.install(PackageId.HASH_CHECK, self.handle_check_hash)
        self.package_handler.install(PackageId.FILE_CHECK, self.handle_check_file)
        self.package_handler.install(PackageId.GET_FILE, self.handle_request_file)

    def __handle_client(self, sock: socket, addr: Tuple):
        logger.info("Incoming connection from: " + str(addr[0]) + ":" + str(addr[1]))
        read(self.package_handler, sock)
        sock.close()
        logger.info("Closed connection with: " + str(addr[0]) + ":" + str(addr[1]))

    def __start(self, max_workers: int = 1):
        """
        Starts a TCP server. The server runs in an infinite loop to handle
        incoming client connections. Clients are handle by a ThreadPoolExecutor so the server
        can accept a new client.

        :param max_workers: number of worker threads that will handle the client communication.
        """

        logger.info("Starting server")
        self.server_socket.listen()
        logger.info("Server started listening to " + self.host + ":" + str(self.port))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while True:
                try:
                    sock, addr = self.server_socket.accept()
                    executor.submit(self.__handle_client, sock, addr)
                except OSError:
                    executor.shutdown(wait=True)
                    logger.info("Shutdown server")
                    break

    def start(self,  max_workers: int = 1):
        """
        Start the server in its own thread.

        :param max_workers: number of worker threads that will handle the client communication.
        """
        name = "ServerThread"
        self.thread = threading.Thread(target=self.__start, args=(max_workers,), name=name)
        self.thread.start()

    def stop(self):
        """
        Stops the server if it is running and joins the server thread until it is finished.
        """
        if self.thread and self.thread.is_alive():
            self.server_socket.close()
            self.thread.join()

    def handle_check_hash(self, hashcode: str):
        """
        Checks the hash of a file in the BlockChain. Checks if the file with given hash
        exists and if the BlockChain is consistent.

        :param hashcode: the hashcode to check.
        :return: package to send back to the client.
        """

        if not self.block_chain.contains(hashcode):
            message = "Invalid hash to check '" + hashcode + "' does not exist"
            return self.package_factory.create_log_package(LogLevel.WARNING, message)

        if self.block_chain.check(hashcode):
            message = "Checking '" + hashcode + "' resolves in a consistent BlockChain"
            return self.package_factory.create_log_package(LogLevel.INFO, message)

        message = "Checking '" + hashcode + "' resolves in an inconsistent BlockChain"
        return self.package_factory.create_log_package(LogLevel.ERROR, message)

    def handle_check_file(self, blocks: List[BlockCMD]):
        """
        Checks the blocks of a file in the BlockChain. Checks if the file with given blocks
        exists and if the BlockChain is consistent.

        :param blocks: the blocks of a file to check.
        :return: package to send back to the client.
        """

        try:
            hashcode = generate_hash(blocks)
        except BlockSectionInconsistentError as error:
            message = "Error while generating hash for file: " + str(error)
            return self.package_factory.create_log_package(LogLevel.WARNING, message)

        return self.handle_check_hash(hashcode)

    def handle_add_file(self, blocks: List[BlockCMD]):
        """
        Adding a new file with given blocks to the BlockChain.

        :param blocks: to add to BlockChain.
        :return: package to send back to the client.
        """

        try:
            hashcode = self.block_chain.add(blocks)
        except (BlockInsertionError, BlockSectionInconsistentError) as error:
            message = "Error while adding Blocks to the BlockChain: " + str(error)
            return self.package_factory.create_log_package(LogLevel.WARNING, message)

        message = "Added blocks with hash '" + hashcode + "'"
        return self.package_factory.create_log_package(LogLevel.INFO, message)

    def handle_request_file(self, hashcode: str):
        """
        Requests a file by its hash value. Server checks if the BlockChain contains the file and if
        so sends it back to the client.

        :param hashcode: the hash of a file to restore.
        :return: package to send back to the client containing the file.
        """

        logger.info("Loading data for file '" + hashcode + "'")
        blocks = self.block_chain.get(hashcode)

        cmd_blocks = []
        for block in blocks:
            cmd_blocks.append(BlockCMD(block.index_all, block.ordinal, block.chunk, block.filename))

        if cmd_blocks:
            logger.info("Sending " + str(len(cmd_blocks)) + " Block(s) to the client")
        else:
            logger.warning("No Blocks found for file '" + hashcode + "'")

        return self.package_factory.create_from_object(PackageId.SEND_FILE, cmd_blocks)


def read(package_handler: PackageHandler, sock: socket):
    """
    Reading data from given socket. Handles the incoming package by given PackageHandler
    and sends a package back.

    :param package_handler: to handle incoming packages.
    :param sock: the socket to communicate to.
    """

    byte_buffer = bytearray()
    while True:
        chunk = sock.recv(BUFF_SIZE)
        byte_buffer += chunk
        if len(chunk) < BUFF_SIZE:
            break

    out_package = package_handler.handle(byte_buffer)

    # if out package is not None send it back.
    if out_package:
        send(out_package, sock)


def send(package: Package, sock: socket):
    """
    Sends a package to the given socket.

    :param package: the package to send.
    :param sock: the socket to write to.
    """

    data = package.raw
    for i in range(0, len(data), BUFF_SIZE):
        sock.send(data[i:i + BUFF_SIZE])


def handle_get_file(blocks: List[BlockCMD]):
    """
    Creates a file from given blocks. Sorts the blocks by there ordinal and writes them
    chunk by chunk into a file.

    :param blocks: to create file from.
    """
    logger.info("Received " + str(len(blocks)) + " Block(s) from the server")
    if not blocks:
        return
    logger.info("Creating file '" + blocks[0].filename + "'")
    blocks.sort(key=lambda x: x.ordinal)

    # write to file in binary mode
    with open(blocks[0].filename, "wb") as file:
        for block in blocks:
            file.write(block.chunk)
