import pickle
from typing import List

import constant
from data import Block, BlockChain
from exceptions import BlockAlreadyExistsError, BlockSectionAlreadyFullError
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


def receive_blocks(block_chain: BlockChain, data: bytes):
    blocks: List[Block] = pickle.loads(data)
    try:
        for block in blocks:
            block_chain.add(block)
    except (BlockAlreadyExistsError, BlockSectionAlreadyFullError) as e:
        message = "Error while adding a Block to the BlockChain: " + str(e)
        return __log_result(constant.WARNING, message)

    hashcode = blocks[0].hash
    if block_chain.check(hashcode):
        message = "Successfully added blocks to section '" + hashcode + "'"
        return __log_result(constant.INFO, message)

    message = "Problem after adding to blocks section '" + hashcode + "'"
    return __log_result(constant.ERROR, message)
