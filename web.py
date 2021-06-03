import asyncio
import pickle
import socket

from asyncio import StreamReader, StreamWriter
from typing import List, Dict, Callable

from data import BlockChain, BlockCMD, load_file, generate_hash
from exceptions import BlockSectionInconsistentError, BlockInsertionError
from logger import logger, INFO, WARNING, ERROR

# String encoding
ENCODING = "utf-8"

# Protocol ids
LOG_TEXT = b'0'
SEND_BLOCKS = b'1'
CHECK_HASH = b'2'
CHECK_FILE = b'3'


async def read(protocol: Dict[bytes, Callable], reader: StreamReader, writer: StreamWriter):
    buffer = await reader.read()
    protocol_id = buffer[:1]
    if protocol.__contains__(protocol_id):
        data_handler = protocol.get(protocol_id)
        data = buffer[1:]

        result = data_handler(data)
        if result:
            await send(LOG_TEXT, result, writer)
    else:
        message = "Invalid protocol id: " + protocol_id.hex()
        logger.warning(message)
        await send(LOG_TEXT, bytes(message, ENCODING), writer)


async def send(protocol_id: bytes, message: bytes, writer: StreamWriter):
    writer.write(protocol_id + message)
    writer.write_eof()
    await writer.drain()


class Client:
    def __init__(self, host: str, port: int):
        logger.info("Connecting to server " + str(host) + ":" + str(port))
        self.host = host
        self.port = port
        self.protocol: Dict[bytes, Callable[[bytes], None]] = {
            LOG_TEXT: log,
        }

    async def check_hash(self, hashcode: str):
        reader, writer = await asyncio.open_connection(self.host, self.port)
        await send(CHECK_HASH, bytes(hashcode, ENCODING), writer)

        await read(self.protocol, reader, writer)

        writer.close()
        await writer.wait_closed()

    async def check_file(self, filepath: str):
        await self.__send_file(CHECK_FILE, load_file(filepath))

    async def add_file(self, filepath: str):
        await self.__send_file(SEND_BLOCKS, load_file(filepath))

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
        self.protocol: Dict[bytes, Callable[[bytes], bytes]] = {
            SEND_BLOCKS: lambda data: receive_blocks(self.block_chain, data),
            CHECK_HASH: lambda data: check_hash(self.block_chain, data),
            CHECK_FILE: lambda data: check_file(self.block_chain, data)
        }

    async def handle_client(self, reader: StreamReader, writer: StreamWriter):
        host, port = writer.get_extra_info("peername")
        logger.info("Incoming connection from: " + str(host) + ":" + str(port))

        await read(self.protocol, reader, writer)

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


def __log_result(log_level: bytes, message: str):
    logger.log(log_level, message)
    return log_level + bytes(message, ENCODING)


def log(data: bytes):
    log_level = data[:1]
    message = data[1:]
    logger.log(log_level, message.decode(ENCODING))


def check_hash(block_chain: BlockChain, data: bytes) -> bytes:
    hashcode = data.decode(ENCODING)

    if not block_chain.contains(hashcode):
        message = "Invalid hash to check '" + hashcode + "' does not exist"
        return __log_result(WARNING, message)

    if block_chain.check(hashcode):
        message = "Checking '" + hashcode + "' resolves in a consistent BlockChain"
        return __log_result(INFO, message)

    message = "Checking '" + hashcode + "' resolves in an inconsistent BlockChain"
    return __log_result(ERROR, message)


def check_file(block_chain: BlockChain, data: bytes):
    blocks: List[BlockCMD] = pickle.loads(data)
    try:
        hashcode = generate_hash(blocks)
    except BlockSectionInconsistentError as e:
        message = "Error while generating hash for file: " + str(e)
        return __log_result(WARNING, message)

    if not block_chain.contains(hashcode):
        message = "File with hash '" + hashcode + "' does not exists in the BlockChain!"
        return __log_result(WARNING, message)

    if block_chain.check(hashcode):
        message = "File with hash '" + hashcode + "' exists in the BlockChain"
        return __log_result(INFO, message)

    message = "File with hash '" + hashcode + "' exists but the BlockChain is inconsistent!"
    return __log_result(INFO, message)


def receive_blocks(block_chain: BlockChain, data: bytes):
    blocks: List[BlockCMD] = pickle.loads(data)
    try:
        hashcode = block_chain.add(blocks)
    except (BlockInsertionError, BlockSectionInconsistentError) as e:
        message = "Error while adding Blocks to the BlockChain: " + str(e)
        return __log_result(WARNING, message)

    message = "Added blocks with hash '" + hashcode + "'"
    return __log_result(INFO, message)
