import asyncio
import socket

from asyncio import StreamReader, StreamWriter
from typing import List
from data import BlockChain, BlockCMD, load_file, generate_hash
from exceptions import BlockSectionInconsistentError, BlockInsertionError
from logger import logger, LogLevel
from transfer import PackageFactory, PackageHandler, PackageMode, Package, PackageId


async def read(package_handler: PackageHandler, reader: StreamReader, writer: StreamWriter):
    byte_buffer: bytes = await reader.read()
    out_package = package_handler.handle(byte_buffer)
    if out_package:
        await send(out_package, writer)


async def send(package: Package, writer: StreamWriter):
    writer.write(package.raw)
    writer.write_eof()
    await writer.drain()


class Client:
    def __init__(self, host: str, port: int):
        logger.info("Connecting to server " + str(host) + ":" + str(port))
        self.host = host
        self.port = port
        self.package_factory = PackageFactory(PackageMode.SERVER_MODE)
        self.package_handler = PackageHandler(PackageMode.CLIENT_MODE, self.package_factory)

        self.package_handler.install(PackageId.LOG_TEXT, logger.log)
        self.package_handler.install(PackageId.SEND_FILE, handle_get_file)

    async def get_file(self, hashcode: str):
        await self.__send_hash(PackageId.GET_FILE, hashcode)

    async def check_hash(self, hashcode: str):
        await self.__send_hash(PackageId.HASH_CHECK, hashcode)

    async def check_file(self, filepath: str):
        await self.__send_file(PackageId.FILE_CHECK, load_file(filepath))

    async def add_file(self, filepath: str):
        await self.__send_file(PackageId.SEND_FILE, load_file(filepath))

    async def __send_hash(self, package_id: PackageId, hashcode: str):
        reader, writer = await asyncio.open_connection(self.host, self.port)
        package = self.package_factory.create_from_object(package_id, hashcode)

        await send(package, writer)
        await read(self.package_handler, reader, writer)

        writer.close()
        await writer.wait_closed()

    async def __send_file(self, package_id: PackageId, blocks: List[BlockCMD]):
        reader, writer = await asyncio.open_connection(self.host, self.port)
        package = self.package_factory.create_from_object(package_id, blocks)

        logger.info("Sending " + str(len(blocks)) + " Block(s) to the server")
        await send(package, writer)
        await read(self.package_handler, reader, writer)

        writer.close()
        await writer.wait_closed()


class Server:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.block_chain = BlockChain()
        self.package_factory = PackageFactory(PackageMode.CLIENT_MODE)
        self.package_handler = PackageHandler(PackageMode.SERVER_MODE, self.package_factory)

        self.package_handler.install(PackageId.SEND_FILE, self.handle_add_file)
        self.package_handler.install(PackageId.HASH_CHECK, self.handle_check_hash)
        self.package_handler.install(PackageId.FILE_CHECK, self.handle_check_file)
        self.package_handler.install(PackageId.GET_FILE, self.handle_request_file)

    async def handle_client(self, reader: StreamReader, writer: StreamWriter):
        host, port = writer.get_extra_info("peername")
        logger.info("Incoming connection from: " + str(host) + ":" + str(port))

        await read(self.package_handler, reader, writer)

        writer.close()
        logger.info("Closed connection with: " + str(host) + ":" + str(port))

    async def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        server_socket.bind((self.host, self.port))

        logger.info("Starting server")
        server = await asyncio.start_server(self.handle_client, sock=server_socket)
        logger.info("Server started listening to " + self.host + ":" + str(self.port))

        async with server:
            await server.serve_forever()

    def handle_check_hash(self, hashcode: str):
        if not self.block_chain.contains(hashcode):
            message = "Invalid hash to check '" + hashcode + "' does not exist"
            return self.package_factory.create_log_package(LogLevel.WARNING, message)

        if self.block_chain.check(hashcode):
            message = "Checking '" + hashcode + "' resolves in a consistent BlockChain"
            return self.package_factory.create_log_package(LogLevel.INFO, message)

        message = "Checking '" + hashcode + "' resolves in an inconsistent BlockChain"
        return self.package_factory.create_log_package(LogLevel.ERROR, message)

    def handle_check_file(self, blocks: List[BlockCMD]):
        try:
            hashcode = generate_hash(blocks)
        except BlockSectionInconsistentError as e:
            message = "Error while generating hash for file: " + str(e)
            return self.package_factory.create_log_package(LogLevel.WARNING, message)

        if not self.block_chain.contains(hashcode):
            message = "File with hash '" + hashcode + "' does not exists in the BlockChain!"
            return self.package_factory.create_log_package(LogLevel.WARNING, message)

        if self.block_chain.check(hashcode):
            message = "File with hash '" + hashcode + "' exists in the BlockChain"
            return self.package_factory.create_log_package(LogLevel.INFO, message)

        message = "File with hash '" + hashcode + "' exists but the BlockChain is inconsistent!"
        return self.package_factory.create_log_package(LogLevel.INFO, message)

    def handle_add_file(self, blocks: List[BlockCMD]):
        try:
            hashcode = self.block_chain.add(blocks)
        except (BlockInsertionError, BlockSectionInconsistentError) as e:
            message = "Error while adding Blocks to the BlockChain: " + str(e)
            return self.package_factory.create_log_package(LogLevel.WARNING, message)

        message = "Added blocks with hash '" + hashcode + "'"
        return self.package_factory.create_log_package(LogLevel.INFO, message)

    def handle_request_file(self, hashcode: str):
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


def handle_get_file(blocks: List[BlockCMD]):
    logger.info("Received " + str(len(blocks)) + " Block(s) from the server")
    if not blocks:
        return
    logger.info("Creating file '" + blocks[0].filename + "'")
    blocks.sort(key=lambda x: x.ordinal)

    # write to file in binary mode
    with open(blocks[0].filename, "wb") as file:
        for block in blocks:
            file.write(block.chunk)





