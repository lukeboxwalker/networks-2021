import hashlib
import os
import pickle
import threading
import zlib

from os import path
from typing import Dict, List

import constant
from exceptions import BlockInsertionError, BlockSectionInconsistentError


class BlockCMD:
    """
    Class that represents a Block that was send from a client.

    There is no hash as well as no hash previous because only the server
    should determine there values.
    """

    def __init__(self, index_all: int, ordinal: int, chunk: bytes, filename: str):
        self.__index_all = index_all
        self.__ordinal = ordinal
        self.__filename = filename
        self.__chunk = chunk

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

    def __init__(self, hashcode: str, hash_previous: str, block_cmd: BlockCMD):
        self.__hashcode = hashcode
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


class BlockSectionCMD:
    def __init__(self, blocks: List[BlockCMD]):
        self.__blocks: Dict[int, BlockCMD] = dict()
        self.__index_all = None
        self.__filename = None

        for block in blocks:
            if self.__blocks.__contains__(block.ordinal):
                raise BlockSectionInconsistentError("Duplicate block in section!")

            if self.index_all is not None and self.index_all != block.index_all:
                raise BlockSectionInconsistentError("Inconsistent blocks!")

            if self.filename is not None and self.filename != block.filename:
                raise BlockSectionInconsistentError("Inconsistent blocks!")

            self.__index_all = block.index_all
            self.__filename = block.filename
            self.__blocks[block.ordinal] = block

    @property
    def filename(self):
        return self.__filename

    @property
    def index_all(self):
        return self.__index_all

    def get_in_order(self) -> List[BlockCMD]:
        blocks = list(self.__blocks.values())
        blocks.sort(key=lambda x: x.ordinal)
        return blocks


class BlockChain:
    """
    Class that represents the BlockChain.
    All methods are thread safe, so multiple threads can operate on the BlockChain.
    """

    def __init__(self):
        self.__chain: FileDictionary = FileDictionary()
        self.__lock = threading.Lock()

    def contains(self, hashcode: str) -> bool:
        """
        Checks if there are Blocks in the BlockChain which match the given hash.
        Method performs a thread safe action on the BlockChain by acquiring a lock.

        :param hashcode: the hashcode to check
        :return: if the file for the given hash is already stored in the BlockChain.
        """
        with self.__lock:
            return self.__chain.contains(hashcode)

    def check(self, hashcode: str) -> bool:
        """
        Checks if the BlockChain is consistent up upon the given hash.
        Method performs a thread safe action on the BlockChain by acquiring a lock.

        :param hashcode: the hashcode to check
        :return: if the whole BlockChain consistent from the given hash.
        """

        def check_hash(file_hash: str) -> bool:
            # Checks if the hash is in the BlockChain at all
            if not self.__chain.contains(file_hash):
                return False

            # Fetching Blocks that represent the file of the hash
            blocks = self.__chain.get(file_hash)
            block = blocks[0]

            # Check if all Blocks needed for the file are present
            if block.index_all != len(blocks):
                return False

            # Check the previous Block by checking the hash previous until
            # the start of the chain is reached
            if block.hash_previous is not None:
                return check_hash(block.hash_previous)
            return True

        with self.__lock:
            return check_hash(hashcode)

    def add(self, new_blocks: List[BlockCMD]) -> str:
        """
        Adds a new Block to the BlockChain.
        Method performs a thread safe action on the BlockChain by acquiring a lock.

        Creates a new section of Blocks for a new file or add a Block to an existing
        Block section in the BlockChain.

        :param new_blocks: the blocks to insert into the BlockChain.
        :raises BlockInsertionError: when the File the new Blocks are representing are already
        part of the BlockChain.
        """
        with self.__lock:
            if not new_blocks:
                raise BlockInsertionError("There are no Blocks to insert!")

            hashcode = generate_hash(new_blocks)

            if self.__chain.contains(hashcode):
                raise BlockInsertionError("File already exists!")

            hash_previous = self.__chain.get_head()
            self.__chain.set(hashcode, [Block(hashcode, hash_previous, cmd) for cmd in new_blocks])
            self.__chain.update_head(hashcode)

            return hashcode

    def get(self, hashcode: str) -> List[Block]:
        """
        Gets the Blocks from the BlockChain with given hashcode.

        :return: list of Blocks for the given file hash. List is empty if the hash does not exist.
        """
        with self.__lock:
            return self.__chain.get(hashcode)


class FileDictionary:
    """
    Class that stores the BlockChain in the filesystem in a 'git like' way.

    All Blocks of a file are stored in a single file. For example the
    file hash: 4c19f36a2221b34b4837b05a72bbf21f1ca65d61aca1c221dd41e77979a08d73 is
    resulting in a structure like:

    /.blockchain
    +-- ...
        +-- ...
    +-- /4c
        +-- /19f36a2221b34b4837b05a72bbf21f1ca65d61aca1c221dd41e77979a08d73
    +-- ...
        +-- ...

    The last Block added to the BLockChain is saved in a file 'head'. If there is no file called
    'head' in the folder /.blockchain there is no data inside the BlockChain.
    """

    def __init__(self):
        self.root = os.getcwd() + "/.blockchain"

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
        if not self.contains(hashcode):
            os.mkdir(self.root + "/" + hashcode[:2])

    def get_head(self):
        """
        Reading the hash previous stored in the head file.

        :return: the head or current 'hash previous', returns None if file does not exists.
        """
        if not path.isfile(self.head):
            return None
        with open(self.head, "r") as file:
            return file.readline()

    def update_head(self, hashcode: str):
        """
        Updates the head to given hash.

        :param hashcode: hash to update head with.
        """
        with open(self.head, "w") as file:
            file.write(hashcode)

    def contains(self, hashcode: str) -> bool:
        """
        Checks if the file path for the given hashcode exists.

        :param hashcode: hash to check.
        :return: if the hash is part of the BlockChain.
        """
        return path.isfile(self.__get_path(hashcode))

    def get(self, hashcode: str) -> List[Block]:
        """
        Loads all Blocks stored for the file hash.

        :param hashcode: hashcode to load Blocks for.
        :return: the Blocks saved under the given hashcode as a Dict. Where the key is
        the ordinal of a block.
        """
        if not self.contains(hashcode):
            return []

        with open(self.__get_path(hashcode), "rb") as file:
            data = file.read()
            return pickle.loads(zlib.decompress(data))

    def set(self, hashcode: str, blocks: List[Block]):
        """
        Stored all given Blocks back to the file.

        :param hashcode: to save Blocks under.
        :param blocks: to save.
        """
        self.__create_dir_if_not_exists(hashcode)
        with open(self.__get_path(hashcode), "wb") as file:
            data = pickle.dumps(blocks)
            file.write(zlib.compress(data))


def generate_hash(blocks: List[BlockCMD]):
    block_section = BlockSectionCMD(blocks)
    if not blocks:
        raise BlockSectionInconsistentError("No Blocks to create hash from!")

    sha256 = hashlib.sha256()
    for block in block_section.get_in_order():
        sha256.update(block.chunk)
    return sha256.hexdigest()


def load_file(filepath: str) -> List[BlockCMD]:
    filename: str = os.path.split(filepath)[1]
    chunks: List[bytes] = []
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(constant.CHUNK_SIZE)
            if not chunk:
                break
            chunks.append(chunk)
    index_all = len(chunks)
    return [BlockCMD(index_all, ordinal, chunks[ordinal], filename) for ordinal in range(index_all)]


def create_file_from_blocks(blocks: List[Block]):
    if not blocks:
        return
    blocks.sort(key=lambda x: x.ordinal)
    with open("test" + blocks[0].filename, "wb") as f:
        for block in blocks:
            f.write(block.chunk)