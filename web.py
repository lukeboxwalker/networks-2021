import asyncio
import pickle
import socket

from asyncio import StreamReader, StreamWriter
from typing import List, Dict, Callable, Tuple

from data import BlockChain, BlockCMD, load_file, generate_hash, create_file_from_blocks
from exceptions import BlockSectionInconsistentError, BlockInsertionError
from logger import logger, INFO, WARNING, ERROR

# String encoding
from transfer import PackageFactory, PackageHandler, CLIENT_MODE

ENCODING = "utf-8"

# Protocol ids
LOG_TEXT = b'0'
SEND_FILE = b'1'
CHECK_HASH = b'2'
CHECK_FILE = b'3'
GET_FILE = b'4'

package_factory = PackageFactory()


async def read(packages: Dict, reader: StreamReader, writer: StreamWriter):
    buffer = await reader.read()
    package_id = buffer[:1]
    if packages.__contains__(package_id):
        package_handler = packages.get(package_id)
        data = buffer[1:]

        result = package_handler(data)
        if result:
            await send(result[0], result[1], writer)
    else:
        message = "Invalid package id: " + package_id.hex()
        logger.error(message)
        await send(LOG_TEXT, bytes(message, ENCODING), writer)


async def send(protocol_id: bytes, message: bytes, writer: StreamWriter):
    if protocol_id is None:
        return

    writer.write(protocol_id + message)
    writer.write_eof()
    await writer.drain()


class Client:
    def __init__(self, host: str, port: int):
        logger.info("Connecting to server " + str(host) + ":" + str(port))
        self.host = host
        self.port = port

        self.package_handler = PackageHandler(CLIENT_MODE)
        self.protocol: Dict[bytes, Callable[[bytes], None]] = {
            LOG_TEXT: handle_log,
            SEND_FILE: handle_get_file
        }

    async def get_file(self, hashcode: str):
        reader, writer = await asyncio.open_connection(self.host, self.port)
        await send(GET_FILE, bytes(hashcode, ENCODING), writer)

        await read(self.protocol, reader, writer)

        writer.close()
        await writer.wait_closed()

    async def check_hash(self, hashcode: str):
        reader, writer = await asyncio.open_connection(self.host, self.port)
        await send(CHECK_HASH, bytes(hashcode, ENCODING), writer)

        await read(self.protocol, reader, writer)

        writer.close()
        await writer.wait_closed()

    async def check_file(self, filepath: str):
        await self.__send_file(CHECK_FILE, load_file(filepath))

    async def add_file(self, filepath: str):
        await self.__send_file(SEND_FILE, load_file(filepath))

    async def __send_file(self, protocol: bytes, blocks: List[BlockCMD]):
        reader, writer = await asyncio.open_connection(self.host, self.port)

        logger.info("Sending " + str(len(blocks)) + " Block(s) to the server")
        await send(protocol, pickle.dumps(blocks), writer)

        await read(self.protocol, reader, writer)

        writer.close()
        await writer.wait_closed()


class Server:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.block_chain = BlockChain()
        self.packages: Dict[bytes, Callable[[bytes], Tuple[bytes, bytes]]] = {
            SEND_FILE: lambda data: handle_add_file(self.block_chain, data),
            CHECK_HASH: lambda data: handle_check_hash(self.block_chain, data),
            CHECK_FILE: lambda data: handle_check_file(self.block_chain, data),
            GET_FILE: lambda data: handle_request_file(self.block_chain, data)
        }

    async def handle_client(self, reader: StreamReader, writer: StreamWriter):
        host, port = writer.get_extra_info("peername")
        logger.info("Incoming connection from: " + str(host) + ":" + str(port))

        await read(self.packages, reader, writer)

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


def log_result(log_level: bytes, message: str):
    logger.log(log_level, message)
    return log_level + bytes(message, ENCODING)


def handle_log(data: bytes):
    log_level = data[:1]
    message = data[1:]
    logger.log(log_level, message.decode(ENCODING))


def handle_check_hash(block_chain: BlockChain, data: bytes) -> Tuple[bytes, bytes]:
    hashcode = data.decode(ENCODING)

    if not block_chain.contains(hashcode):
        message = "Invalid hash to check '" + hashcode + "' does not exist"
        return LOG_TEXT, log_result(WARNING, message)

    if block_chain.check(hashcode):
        message = "Checking '" + hashcode + "' resolves in a consistent BlockChain"
        return LOG_TEXT, log_result(INFO, message)

    message = "Checking '" + hashcode + "' resolves in an inconsistent BlockChain"
    return LOG_TEXT, log_result(ERROR, message)


def handle_check_file(block_chain: BlockChain, data: bytes) -> Tuple[bytes, bytes]:
    blocks: List[BlockCMD] = pickle.loads(data)
    try:
        hashcode = generate_hash(blocks)
    except BlockSectionInconsistentError as e:
        message = "Error while generating hash for file: " + str(e)
        return LOG_TEXT, log_result(WARNING, message)

    if not block_chain.contains(hashcode):
        message = "File with hash '" + hashcode + "' does not exists in the BlockChain!"
        return LOG_TEXT, log_result(WARNING, message)

    if block_chain.check(hashcode):
        message = "File with hash '" + hashcode + "' exists in the BlockChain"
        return LOG_TEXT, log_result(INFO, message)

    message = "File with hash '" + hashcode + "' exists but the BlockChain is inconsistent!"
    return LOG_TEXT,log_result(INFO, message)


def handle_add_file(block_chain: BlockChain, data: bytes) -> Tuple[bytes, bytes]:
    blocks: List[BlockCMD] = pickle.loads(data)
    try:
        hashcode = block_chain.add(blocks)
    except (BlockInsertionError, BlockSectionInconsistentError) as e:
        message = "Error while adding Blocks to the BlockChain: " + str(e)
        return LOG_TEXT, log_result(WARNING, message)

    message = "Added blocks with hash '" + hashcode + "'"
    return LOG_TEXT, log_result(INFO, message)


def handle_get_file(data: bytes):
    blocks: List[BlockCMD] = pickle.loads(data)
    logger.info("Received " + str(len(blocks)) + " Block(s) from the server")
    if not blocks:
        return
    logger.info("Creating file '" + blocks[0].filename + "'")
    create_file_from_blocks(blocks)


def handle_request_file(block_chain: BlockChain, data: bytes) -> Tuple[bytes, bytes]:
    hashcode = data.decode(ENCODING)

    logger.info("Loading data for file '" + hashcode + "'")
    blocks = block_chain.get(hashcode)

    cmd_blocks = []
    for block in blocks:
        cmd_blocks.append(BlockCMD(block.index_all, block.ordinal, block.chunk, block.filename))

    if cmd_blocks:
        logger.info("Sending " + str(len(cmd_blocks)) + " Block(s) to the client")
    else:
        logger.warning("No Blocks found for file '" + hashcode + "'")

    return SEND_FILE, pickle.dumps(cmd_blocks)


