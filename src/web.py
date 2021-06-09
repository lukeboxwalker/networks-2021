"""
Module that holds the classes and functions needed for the client server communication.
"""
import socket
import threading

from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import closing
from typing import List, Tuple
from data import BlockChain, BlockCMD, load_file, generate_file_hash
from exceptions import BlockSectionInconsistentError, BlockInsertionError
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

        # create PackageFactory in SERVER_MODE (creates packages that only a serer accepts)
        # create PackageHandler in CLIENT_MODE (can only handle packages directed to a client)
        self.package_factory = PackageFactory(PackageMode.SERVER_MODE)
        self.package_handler = PackageHandler(PackageMode.CLIENT_MODE, self.package_factory)

        # install package handlers for incoming packages
        self.package_handler.install(PackageId.LOG_TEXT, logger.log)
        self.package_handler.install(PackageId.SEND_FILE, handle_get_file)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        logger.info("Connecting to server " + str(self.host) + ":" + str(self.port))
        self.sock.connect((self.host, self.port))

    def __send_hash(self, package_id: PackageId, hashcode: str):
        """
        Sends a hash to the server with given package id.

        :param package_id: package id for the package that will be send.
        :param hashcode: to send to server.
        """
        package = self.package_factory.create_from_object(package_id, hashcode)

        logger.info("Sending hash '" + hashcode + "' to the server")
        send(package, self.sock)
        read(self.package_handler, self.sock)

    def __send_file(self, package_id: PackageId, blocks: List[BlockCMD]):
        """
        Sends a file in form of blocks to the server with given package id.

        :param package_id: package id for the package that will be send.
        :param blocks: the blocks of a file to send.
        """

        logger.info("Sending " + str(len(blocks)) + " Block(s) to the server")
        for block in blocks:
            package = self.package_factory.create_from_object(package_id, block)
            send(package, self.sock)
            read(self.package_handler, self.sock)
        logger.info("Done")

    def close(self):
        """
        Closes the socket.
        """
        self.sock.close()

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
        blocks = load_file(filepath)
        self.__send_hash(PackageId.HASH_CHECK, generate_file_hash(blocks))

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
        with sock:
            while True:
                logger.info("Wait for client: " + str(addr[0]) + ":" + str(addr[1])
                            + " to receive data")
                if read(self.package_handler, sock):
                    break
        logger.info("Connection closed by: " + str(addr[0]) + ":" + str(addr[1]))

    def __start(self, max_workers: int = 1):
        """
        Starts a TCP server. The server runs in an infinite loop to handle
        incoming client connections. Clients are handle by a ThreadPoolExecutor so the server
        can accept a new client.

        :param max_workers: number of worker threads that will handle the client communication.
        """

        logger.info("Starting server...")
        self.sock.listen()
        host = self.address[0]
        port = self.address[1]
        logger.info("Server started listening to " + host + ":" + str(port))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while True:
                sock, addr = self.sock.accept()
                if self.stopped.isSet():
                    sock.close()
                    logger.info("Shutdown server...")
                    executor.shutdown(wait=True)
                    break
                executor.submit(self.__handle_client, sock, addr)
        self.sock.close()
        logger.info("Shutdown complete")

    def start(self,  max_workers: int = 1):
        """
        Start the server in its own thread. Blocking the Main Thread until user KeyboardInterrupt
        the process.

        :param max_workers: number of worker threads that will handle the client communication.
        """
        name = "ServerThread"
        self.thread = threading.Thread(target=self.__start, args=(max_workers,), name=name)
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

    def handle_check_hash(self, hashcode: str):
        """
        Checks the hash of a file in the BlockChain. Checks if the file with given hash
        exists and if the BlockChain is consistent.

        :param hashcode: the hashcode to check.
        :return: package to send back to the client.
        """

        if self.block_chain.file_exists(hashcode):
            message = "File with hash '" + hashcode + "' is stored in the BlockChain"
            return self.package_factory.create_log_package(LogLevel.INFO, message)

        message = "File with hash '" + hashcode + "' is not stored in the BlockChain"
        return self.package_factory.create_log_package(LogLevel.WARNING, message)

    # def handle_check_file(self, blocks: List[BlockCMD]):
    #     """
    #     Checks the blocks of a file in the BlockChain. Checks if the file with given blocks
    #     exists and if the BlockChain is consistent.
    #
    #     :param blocks: the blocks of a file to check.
    #     :return: package to send back to the client.
    #     """
    #
    #     try:
    #         hashcode = generate_file_hash(blocks)
    #         logger.info("Check file with hash '" + hashcode + "'")
    #     except BlockSectionInconsistentError as error:
    #         message = "Error while generating hash for file: " + str(error)
    #         return self.package_factory.create_log_package(LogLevel.WARNING, message)
    #
    #     return self.handle_check_hash(hashcode)

    def handle_add_block(self, block: BlockCMD):
        """
        Adding a new block to the BlockChain.

        :param block: the block to add to the BlockChain.
        :return: package to send back to the client.
        """
        if not block:
            message = "No block to add!"
            return self.package_factory.create_log_package(LogLevel.WARNING, message)

        try:
            hashcode = self.block_chain.add(block)
            message = "Added block with hash '" + hashcode + "' from file '" + block.filename
            return self.package_factory.create_log_package(LogLevel.INFO, message)
        except (BlockInsertionError, BlockSectionInconsistentError) as error:
            message = "Error while adding Blocks to the BlockChain: " + str(error)
            return self.package_factory.create_log_package(LogLevel.ERROR, message)

    def handle_request_file(self, hashcode: str):
        """
        Requests a file by its hash value. Server checks if the BlockChain contains the file and if
        so sends it back to the client.

        :param hashcode: the hash of a file to restore.
        :return: package to send back to the client containing the file.
        """

        logger.info("Loading data for file with hash '" + hashcode + "'")
        blocks = self.block_chain.get(hashcode)

        cmd_blocks = []
        for block in blocks:
            cmd = BlockCMD(block.hash, block.index_all, block.ordinal, block.chunk, block.filename)
            cmd_blocks.append(cmd)

        if cmd_blocks:
            logger.info("Sending " + str(len(cmd_blocks)) + " Block(s) to the client")
        else:
            logger.warning("No Blocks found for file '" + hashcode + "'")

        return self.package_factory.create_from_object(PackageId.SEND_FILE, cmd_blocks)


def read(package_handler: PackageHandler, sock: socket.socket) -> bool:
    """
    Reading data from given socket. Handles the incoming package by given PackageHandler
    and sends a package back.

    :param package_handler: to handle incoming packages.
    :param sock: the socket to communicate to.
    :return: if client closed the connection.
    """

    buf = sock.recv(MAX_PACKAGE_SIZE)
    if not buf:
        return True
    package_size = int.from_bytes(buf, byteorder="big")
    byte_package = sock.recv(package_size)

    out_package = package_handler.handle(byte_package)

    # if out package is not None send it back.
    if out_package:
        send(out_package, sock)

    return False


def send(package: Package, sock: socket.socket):
    """
    Sends a package to the given socket.

    :param package: the package to send.
    :param sock: the socket to write to.
    """
    try:
        size = len(package.raw)
        logger.info("Sending package with size: " + str(size))
        sock.sendall(size.to_bytes(MAX_PACKAGE_SIZE, byteorder="big") + package.raw)
    except OverflowError:
        logger.error("Can't send package. Package size to large!")


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
    with open("test" + blocks[0].filename, "wb") as file:
        for block in blocks:
            file.write(block.chunk)
