import asyncio
import pickle
import socket

from asyncio import StreamReader, StreamWriter
from typing import List, Dict, Callable

import constant
import handler
from data import Block, BlockChain, BlockCMD, load_file
from logger import logger


async def read(protocol: Dict[bytes, Callable], reader: StreamReader, writer: StreamWriter):
    buffer = await reader.read()
    protocol_id = buffer[:1]
    if protocol.__contains__(protocol_id):
        data_handler = protocol.get(protocol_id)
        data = buffer[1:]

        result = data_handler(data)
        if result:
            await send(constant.LOG_TEXT, result, writer)
    else:
        message = "Invalid protocol id: " + protocol_id.hex()
        logger.warning(message)
        await send(constant.LOG_TEXT, bytes(message, constant.ENCODING), writer)


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
            constant.LOG_TEXT: handler.log,
        }

    async def check_hash(self, hashcode: str):
        reader, writer = await asyncio.open_connection(self.host, self.port)
        await send(constant.CHECK_HASH, bytes(hashcode, constant.ENCODING), writer)

        await read(self.protocol, reader, writer)

        writer.close()
        await writer.wait_closed()

    async def check_file(self, filepath: str):
        await self.__send_file(constant.CHECK_FILE, load_file(filepath))

    async def add_file(self, filepath: str):
        await self.__send_file(constant.SEND_BLOCKS, load_file(filepath))

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
            constant.SEND_BLOCKS: lambda data: handler.receive_blocks(self.block_chain, data),
            constant.CHECK_HASH: lambda data: handler.check_hash(self.block_chain, data),
            constant.CHECK_FILE: lambda data: handler.check_file(self.block_chain, data)
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
