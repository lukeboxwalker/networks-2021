import pickle
from typing import List

import constant
from data import BlockChain, BlockCMD, generate_hash
from exceptions import BlockInsertionError, BlockSectionInconsistentError
from logger import logger


def __log_result(log_level: bytes, message: str):
    logger.log(log_level, message)
    return log_level + bytes(message, constant.ENCODING)


def log(data: bytes):
    log_level = data[:1]
    message = data[1:]
    logger.log(log_level, message.decode(constant.ENCODING))


def check_hash(block_chain: BlockChain, data: bytes) -> bytes:
    hashcode = data.decode(constant.ENCODING)

    if not block_chain.contains(hashcode):
        message = "Invalid hash to check '" + hashcode + "' does not exist"
        return __log_result(constant.WARNING, message)

    if block_chain.check(hashcode):
        message = "Checking '" + hashcode + "' resolves in a consistent BlockChain"
        return __log_result(constant.INFO, message)

    message = "Checking '" + hashcode + "' resolves in an inconsistent BlockChain"
    return __log_result(constant.ERROR, message)


def check_file(block_chain: BlockChain, data: bytes):
    blocks: List[BlockCMD] = pickle.loads(data)
    try:
        hashcode = generate_hash(blocks)
    except BlockSectionInconsistentError as e:
        message = "Error while generating hash for file: " + str(e)
        return __log_result(constant.WARNING, message)

    if not block_chain.contains(hashcode):
        message = "File with hash '" + hashcode + "' does not exists in the BlockChain!"
        return __log_result(constant.WARNING, message)

    if block_chain.check(hashcode):
        message = "File with hash '" + hashcode + "' exists in the BlockChain"
        return __log_result(constant.INFO, message)

    message = "File with hash '" + hashcode + "' exists but the BlockChain is inconsistent!"
    return __log_result(constant.INFO, message)


def receive_blocks(block_chain: BlockChain, data: bytes):
    blocks: List[BlockCMD] = pickle.loads(data)
    try:
        hashcode = block_chain.add(blocks)
    except (BlockInsertionError, BlockSectionInconsistentError) as e:
        message = "Error while adding Blocks to the BlockChain: " + str(e)
        return __log_result(constant.WARNING, message)

    message = "Added blocks with hash '" + hashcode + "'"
    return __log_result(constant.INFO, message)
