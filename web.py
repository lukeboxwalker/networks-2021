import asyncio
import pickle
import socket

from asyncio import StreamReader, StreamWriter
from typing import List, Dict, Callable
from data import Block, BlockChain
from exceptions import BlockAlreadyExistsError, BlockSectionAlreadyFullError
from logger import logger

ENCODING = "utf-8"

SEND_BLOCKS = b'1'
CHECK_HASH = b'2'


async def send(protocol_id: bytes, message: bytes, writer: StreamWriter):
    data = bytearray()
    data += protocol_id
    data += message

    writer.write(data)
    writer.write_eof()
    await writer.drain()


class Client:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    async def check_hash(self, hashcode: str):
        reader, writer = await asyncio.open_connection(self.host, self.port)
        await send(CHECK_HASH, bytes(hashcode, ENCODING), writer)

        writer.close()
        await writer.wait_closed()

    async def send_blocks(self, blocks: List[Block]):
        reader, writer = await asyncio.open_connection(self.host, self.port)
        await send(SEND_BLOCKS, pickle.dumps(blocks), writer)

        writer.close()
        await writer.wait_closed()


class Server:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.block_chain = BlockChain()
        self.protocol: Dict[bytes, Callable[[bytes], None]] = {
            SEND_BLOCKS: self.receive_blocks,
            CHECK_HASH: self.check_hash
        }

    async def handle_client(self, reader: StreamReader, writer: StreamWriter):
        host, port = writer.get_extra_info("peername")
        logger.info("Incoming connection from: " + str(host) + ":" + str(port))

        buffer = await reader.read()
        protocol_id = buffer[:1]
        if self.protocol.__contains__(protocol_id):
            data_handler = self.protocol.get(protocol_id)
            data = buffer[1:]
            data_handler(data)
        else:
            logger.warning("Invalid protocol id: " + protocol_id.hex())

        writer.close()
        logger.info("Closed connection with: " + str(host) + ":" + str(port))

    def check_hash(self, data: bytes):
        hashcode = data.decode(ENCODING)
        if not self.block_chain.contains(hashcode):
            logger.warning("Invalid hash to check '" + hashcode + "' does not exist")
            return

        if self.block_chain.check(hashcode):
            logger.info("Checking '" + hashcode + "' resolves in a consistent BlockChain")
        else:
            logger.error("Checking '" + hashcode + "' resolves in an inconsistent BlockChain")

    def receive_blocks(self, data: bytes):
        blocks: List[Block] = pickle.loads(data)
        try:
            for block in blocks:
                self.block_chain.add(block)
        except (BlockAlreadyExistsError, BlockSectionAlreadyFullError) as e:
            logger.warning("Error while adding a Block to the BlockChain: " + str(e))
            return

        hashcode = blocks[0].hash
        if self.block_chain.check(hashcode):
            logger.info("Successfully added blocks to section '" + hashcode + "'")
        else:
            logger.error("Problem after adding to blocks section '" + hashcode + "'")

    async def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        server_socket.bind((self.host, self.port))

        logger.info("Starting server")
        server = await asyncio.start_server(self.handle_client, sock=server_socket)
        logger.info("Server started listening to " + self.host + ":" + str(self.port))

        async with server:
            await server.serve_forever()
