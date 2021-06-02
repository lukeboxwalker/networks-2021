import os
import pickle
import threading

from os import path
from typing import Dict, List
from exceptions import BlockAlreadyExistsError, BlockSectionAlreadyFullError


class Block:
    """
    Class that represents a Block in a BlockChain.
    """

    def __init__(self,
                 hashcode: str,
                 index_all: int,
                 ordinal: int,
                 chunk: bytes,
                 filename: str,
                 hash_previous=None):
        self.__hashcode = hashcode
        self.__index_all = index_all
        self.__ordinal = ordinal
        self.__filename = filename
        self.__chunk = chunk
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

    def init_with_previous(self, hashcode: str):
        """
        Initializes a new Block with given previous hashcode of a previous Block. Because fields of
        a Block should stay immutable. Therefore a new Block is created.

        :return: a completely new Block object with the new given previous hashcode.
        """
        return Block(self.hash, self.index_all, self.ordinal, self.chunk, self.filename, hashcode)


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
            block = set(blocks.values()).pop()

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

    def add(self, block: Block) -> None:
        """
        Adds a new Block to the BlockChain.
        Method performs a thread safe action on the BlockChain by acquiring a lock.

        Creates a new section of Blocks for a new file or add a Block to an existing
        Block section in the BlockChain.

        :param block: the block to insert into the BlockChain.
        :raises BlockAlreadyExistsError: when a Block in the BlockChain already
        exists when trying to add the new Block.
        :raises BlockSectionAlreadyFullError: when a Block section of a file in the BlockChain
        is already full when trying to add the new Block.
        """
        with self.__lock:
            if self.__chain.contains(block.hash):
                blocks = self.__chain.get(block.hash)

                # if the block to insert into the BlockChain has the same ordinal
                # as an existing block, the block already exists and an Error is raised
                if blocks.__contains__(block.ordinal):
                    raise BlockAlreadyExistsError("Block already exists!")
                existing_block = set(blocks.values()).pop()

                # if the block section for the file of the block hash given is already
                # full or rather there are no more blocks needed to store the file and
                # an Error is raised
                if existing_block.index_all == len(blocks):
                    raise BlockSectionAlreadyFullError("The block section is already full!")
                blocks[block.ordinal] = block.init_with_previous(existing_block.hash_previous)
                self.__chain.set(block.hash, blocks)
            else:
                # if the file has yet no existing block, a new section of Blocks is inserted into
                # the BlockChain and the hash_tail is updated
                hash_previous = self.__chain.get_head()
                self.__chain.set(block.hash, {
                    block.ordinal: block.init_with_previous(hash_previous)
                })
                self.__chain.update_head(block.hash)

    def get(self, hashcode: str) -> List[Block]:
        """
        Gets the Blocks from the BlockChain with given hashcode.

        :return: list of Blocks for the given file hash. List is empty if the hash does not exist.
        """
        with self.__lock:
            if not self.__chain.contains(hashcode):
                return []
            blocks = self.__chain.get(hashcode)
            return list(blocks.values())


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
        with open(self.head, "r") as f:
            return f.readline()

    def update_head(self, hashcode: str):
        """
        Updates the head to given hash.

        :param hashcode: hash to update head with.
        """
        with open(self.head, "w") as f:
            f.write(hashcode)

    def contains(self, hashcode: str) -> bool:
        """
        Checks if the file path for the given hashcode exists.

        :param hashcode: hash to check.
        :return: if the hash is part of the BlockChain.
        """
        return path.isfile(self.__get_path(hashcode))

    def get(self, hashcode: str) -> Dict[int, Block]:
        """
        Loads all Blocks stored for the file hash.

        :param hashcode: hashcode to load Blocks for.
        :return: the Blocks saved under the given hashcode as a Dict. Where the key is
        the ordinal of a block.
        """
        self.__create_dir_if_not_exists(hashcode)
        with open(self.__get_path(hashcode), "rb") as f:
            return pickle.load(f)

    def set(self, hashcode: str, blocks: Dict[int, Block]):
        """
        Stored all given Blocks back to the file.

        :param hashcode: to save Blocks under.
        :param blocks: to save.
        """
        self.__create_dir_if_not_exists(hashcode)
        with open(self.__get_path(hashcode), "wb") as f:
            pickle.dump(blocks, f)
