"""
Module that holds the classes and functions needed for the BlockChain.
"""

import hashlib
import os
import pickle
import threading
import zlib

from os import path
from typing import List
from exceptions import BlockInsertionError, BlockSectionInconsistentError

# Chunk size for the data a single Block is holding.
# Size is defined by project specification.
CHUNK_SIZE = 500


class BlockCMD:
    """
    Class that represents a Block that was send from a client.

    There is no hash as well as no hash previous because only the server
    should determine there values in the real stored Block.
    """

    # Disable too many arguments. Doesnt make much sense to group the variables instead.
    # pylint: disable=too-many-arguments
    def __init__(self, hashcode: str, index_all: int, ordinal: int, chunk: bytes, filename: str):
        self.__hashcode = hashcode
        self.__index_all = index_all
        self.__ordinal = ordinal
        self.__filename = filename
        self.__chunk = chunk

    @property
    def hash(self) -> str:
        """
        Property function to ensure that the hash is a read only variable.
        :return: the hash value of the file as a string.
        """
        return self.__hashcode

    @property
    def index_all(self) -> int:
        """
        Property function to ensure that the number of Blocks is a read only variable.

        :return: the number of Blocks that represent the file as an integer.
        """
        return self.__index_all

    @property
    def ordinal(self) -> int:
        """
        Property function to ensure that the ordinal is a read only variable.
        If there are n blocks that represent a file, the ordinal value of a single block
        is between 0 and n - 1.

        :return: the ordinal of this block as an integer.
        """
        return self.__ordinal

    @property
    def chunk(self) -> bytes:
        """
        Property function to ensure that the chunk of data is a read only variable.
        The byte data is stored as a Block.BUF_SIZE large chunk in the each Block.

        :return: the chunk of data as bytes.
        """
        return self.__chunk

    @property
    def filename(self) -> str:
        """
        Property function to ensure that the filename is a read only variable.
        :return: the filename of the file as a string.
        """
        return self.__filename


class Block:
    """
    Class that represents a Block in a BlockChain.
    """

    def __init__(self, hash_previous: str, block_cmd: BlockCMD):
        self.__hashcode = block_cmd.hash
        self.__index_all = block_cmd.index_all
        self.__ordinal = block_cmd.ordinal
        self.__filename = block_cmd.filename
        self.__chunk = block_cmd.chunk
        self.__hash_previous = hash_previous

    @property
    def hash(self) -> str:
        """
        Property function to ensure that the hash is a read only variable.
        :return: the hash value of the file as a string.
        """
        return self.__hashcode

    @property
    def index_all(self) -> int:
        """
        Property function to ensure that the number of Blocks is a read only variable.

        :return: the number of Blocks that represent the file as an integer.
        """
        return self.__index_all

    @property
    def ordinal(self) -> int:
        """
        Property function to ensure that the ordinal is a read only variable.
        If there are n blocks that represent a file, the ordinal value of a single block
        is between 0 and n - 1.

        :return: the ordinal of this block as an integer.
        """
        return self.__ordinal

    @property
    def chunk(self) -> bytes:
        """
        Property function to ensure that the chunk of data is a read only variable.
        The byte data is stored as a Block.BUF_SIZE large chunk in the each Block.

        :return: the chunk of data as bytes.
        """
        return self.__chunk

    @property
    def filename(self) -> str:
        """
        Property function to ensure that the filename is a read only variable.
        :return: the filename of the file as a string.
        """
        return self.__filename

    @property
    def hash_previous(self) -> str:
        """
        Property function to ensure that the previous hash of a Block is a read only variable.

        :return: the hash of the previous Block in the BlockChain as a string.
        """
        return self.__hash_previous


class BlockChain:
    """
    Class that represents the BlockChain.
    All methods are thread safe, so multiple threads can operate on the BlockChain.
    """

    def __init__(self):
        self.__chain: FileDictionary = FileDictionary()
        self.__lock = threading.Lock()  # lock to ensures adding as an atomic operation

    def __get_blocks_for_file(self, hashcode: str) -> List[Block]:
        """
        Collects all blocks that correspond to the given file hash.
        Method performs a thread safe action on the BlockChain no explicit locking needed.

        :param hashcode: the hashcode to collect blocks for.
        :return: list of blocks with given hash.
        """
        head = self.__chain.get_head()  # thread safe get_head() is using a lock
        if head is None:
            return []
        block = self.__chain.get(head)  # thread safe block can only be read
        blocks = []

        while block is not None:
            if block.hash == hashcode:
                blocks.append(block)

                if block.index_all == len(blocks):
                    break

            block = self.__chain.get(block.hash_previous)  # thread safe block can only be read
        return blocks

    def file_exists(self, hashcode: str) -> bool:
        """
        Checks if the given hash representing a file exists in the BlockChain.
        Method performs a thread safe action on the BlockChain no explicit locking needed.

        :param hashcode: the hashcode to check
        :return: if the whole BlockChain consistent from the given hash.
        """

        blocks = self.__get_blocks_for_file(hashcode)
        try:
            return generate_file_hash(blocks) == hashcode
        except BlockSectionInconsistentError:
            return False

    def add(self, block: BlockCMD) -> str:
        """
        Adds a new Block to the BlockChain.
        Method performs a thread safe action on the BlockChain by acquiring a lock.

        Creates a new section of Blocks for a new file or add a Block to an existing
        Block section in the BlockChain.

        :param block: the block to insert into the BlockChain.
        """

        with self.__lock:  # ensures atomic operation
            hash_previous = self.__chain.get_head()  # thread safe get_head() is using a lock
            hashcode = self.__chain.add(Block(hash_previous, block))
            self.__chain.update_head(hashcode)  # thread safe update_head() is using a lock
            return hashcode

    def get(self, hashcode: str) -> List[Block]:
        """
        Gets the Blocks from the BlockChain with given hashcode.
        Method performs a thread safe action on the BlockChain no explicit locking needed.

        :return: list of Blocks for the given file hash. List is empty if the hash does not exist.
        """
        return self.__get_blocks_for_file(hashcode)


class FileDictionary:
    """
    Class that stores the BlockChain in the filesystem in a 'git like' way.

    All Blocks of a file are stored in a single file. For example the
    file hash: 4c19f36a2221b34b4837b05a72bbf21f1ca65d61aca1c221dd41e77979a08d73 is
    resulting in a structure like:

    /.blockchain
    +-- /4c
        +-- /19f36a2221b34b4837b05a72bbf21f1ca65d61aca1c221dd41e77979a08d73

    Where the file names 19f36a2221b34b4837b05a72bbf21f1ca65d61aca1c221dd41e77979a08d73 contains
    all Blocks of the stored file.

    The last Block added to the BLockChain is saved in a file 'head'. If there is no file called
    'head' in the folder /.blockchain there is no data inside the BlockChain.
    """

    def __init__(self):
        self.root = os.getcwd() + "/.blockchain"
        self.__head_lock = threading.Lock()  # lock to ensures read write head is thread safe

        # creating root dir if not exists
        if not path.exists(self.root):
            os.mkdir(self.root)
        self.head = self.root + "/head"

    def __get_path(self, hashcode: str) -> str:
        """
        Construct the path for the given file hash.

        :param hashcode: the hash value to get the path for.
        :return: the path for the given file hash.
        """
        return self.root + "/" + hashcode[:2] + "/" + hashcode[2:]

    def __create_dir_if_not_exists(self, hashcode: str):
        """
        Creates a directory for a given file hash if not already exists.

        :param hashcode: the file hash
        """
        if not path.isdir(self.root + "/" + hashcode[:2]):
            os.mkdir(self.root + "/" + hashcode[:2])

    def get_head(self):
        """
        Reading the hash previous stored in the head file.

        :return: the head or current 'hash previous', returns None if file does not exists.
        """
        with self.__head_lock:
            if not path.isfile(self.head):
                return None
            with open(self.head, "r") as file:
                return file.readline()

    def update_head(self, hashcode: str):
        """
        Updates the head to given hash.

        :param hashcode: hash to update head with.
        """
        with self.__head_lock:
            with open(self.head, "w") as file:
                file.write(hashcode)

    def contains(self, block: Block) -> bool:
        """
        Checks if the file path for the given hashcode of the block exists.

        :param block: the block to check.
        :return: if the block is part of the BlockChain.
        """
        hashcode = hash_block(block)
        return path.isfile(self.__get_path(hashcode))

    def get(self, hashcode: str):
        """
        Loads all Blocks stored for the file hash.
        Decompresses the byte array stored to the file with zlib.

        :param hashcode: hashcode to load Blocks for.
        :return: the Block saved under the given hashcode. Returns None if hashcode is None or
        the file for the hashcode does not exists.
        """
        if not hashcode:
            return None

        filepath = self.__get_path(hashcode)
        if path.isfile(filepath):
            with open(filepath, "rb") as file:
                data = file.read()
                return pickle.loads(zlib.decompress(data))
        return None

    def add(self, block: Block) -> str:
        """
        Stores the given Block back to the file. Compresses the byte array stored to the file
        with zlib.

        :param block: the block to save.
        """
        hashcode = hash_block(block)
        self.__create_dir_if_not_exists(hashcode)

        filepath = self.__get_path(hashcode)
        if path.isfile(filepath):
            raise BlockInsertionError("Block already exists!")

        with open(filepath, "wb") as file:
            data = pickle.dumps(block)
            file.write(zlib.compress(data))
            return hashcode


def hash_block(block: Block) -> str:
    """
    Creating a sha256 hash for the given block.
    Dumps the pickle byte array of the object into a hash value.

    :param block: to generate hash for.
    :return: sha256 hash for the block.
    """
    sha256 = hashlib.sha256()
    sha256.update(pickle.dumps(block))
    return sha256.hexdigest()


def generate_file_hash(blocks: List) -> str:
    """
    Generates sha256 hash for given block list. If there is an error within the blocks no hash
    will be generated.

    :param blocks: the blocks of a file to generate the hash for.
    :raise BlockSectionInconsistentError: if there are no blocks to create a hash for, if there
    is a duplicate block identified by its ordinal, if the blocks contain different data regarding
    the filename or the index_all.
    :return: sha256 hash for the file.
    """
    if not blocks:
        raise BlockSectionInconsistentError("No Blocks to create hash from!")

    # check if each block is unique
    if len({block.ordinal for block in blocks}) != len(blocks):
        raise BlockSectionInconsistentError("Duplicate block in section!")

    # check if information shared by the blocks is consistent
    hashcode = blocks[0].hash
    index_all = blocks[0].index_all
    filename = blocks[0].filename

    for block in blocks:
        if hashcode != block.hash or index_all != block.index_all or filename != block.filename:
            raise BlockSectionInconsistentError("Inconsistent blocks!")

    # sort blocks in order to always generate the correct hash
    blocks.sort(key=lambda x: x.ordinal)

    # generate sha256 hash with python hashlib
    sha256 = hashlib.sha256()
    for block in blocks:
        sha256.update(block.chunk)
    return sha256.hexdigest()


def load_file(filepath: str) -> List[BlockCMD]:
    """
    Reading a file and converts it to a Block list by reading the file chunk by chunk.

    :param filepath: filepath for the file to read.
    :return: list of BlockCMD objects for transport.
    """
    filename: str = os.path.split(filepath)[1]
    chunks: List[bytes] = []
    sha256 = hashlib.sha256()

    # reading the file in binary mode
    with open(filepath, "rb") as file:
        while True:
            chunk = file.read(CHUNK_SIZE)
            if not chunk:
                break
            chunks.append(chunk)
            sha256.update(chunk)
    index_all = len(chunks)
    hashcode = sha256.hexdigest()

    blocks = []
    for ordinal, chunk in enumerate(chunks):
        blocks.append(BlockCMD(hashcode, index_all, ordinal, chunk, filename))
    return blocks
