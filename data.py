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
        with self.__lock:
            # Checks if the hash is in the BlockChain at all
            if not self.__chain.contains(hashcode):
                return False

            # Fetching Blocks that represent the file of the hash
            blocks = self.__chain.get(hashcode)
            block = set(blocks.values()).pop()

            # Check if all Blocks needed for the file are present
            if block.index_all != len(blocks):
                return False

            # Check the previous Block by checking the hash previous until
            # the start of the chain is reached
            if block.hash_previous is not None:
                return self.check(block.hash_previous)
            return True

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

    def __init__(self):
        self.root = os.getcwd() + "/BlockChain"
        if not path.exists(self.root):
            os.mkdir(self.root)
        self.head = self.root + "/head"

    def get_head(self):
        if not path.isfile(self.head):
            return None
        with open(self.head, "r") as f:
            return f.readline()

    def update_head(self, head: str):
        with open(self.head, "w") as f:
            f.write(head)

    def create_dir_if_not_exists(self, hashcode: str):
        if not self.contains(hashcode):
            os.mkdir(self.root + "/" + hashcode[:2])

    def contains(self, hashcode: str) -> bool:
        return path.isfile(self.root + "/" + hashcode[:2] + "/" + hashcode[2:])

    def get_path(self, hashcode: str):
        return self.root + "/" + hashcode[:2] + "/" + hashcode[2:]

    def get(self, hashcode: str) -> Dict[int, Block]:
        self.create_dir_if_not_exists(hashcode)
        with open(self.get_path(hashcode), "rb") as f:
            return pickle.load(f)

    def set(self, hashcode: str, blocks: Dict[int, Block]):
        self.create_dir_if_not_exists(hashcode)
        with open(self.get_path(hashcode), "wb") as f:
            pickle.dump(blocks, f)


