import threading
from typing import Dict, Tuple


class Block:
    """
    Class that represents a Block in a BlockChain.
    """

    # Chunk size for the data a single Block is holding.
    CHUNK_SIZE = 500

    def __init__(self, hashcode: str, index: Tuple[int, int], chunk: bytes, hash_previous=None):
        self.__hashcode = hashcode
        self.__index_all = index[0]
        self.__ordinal = index[1]
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
    def hash_previous(self) -> str:
        """
        Property function to ensure that the previous hash of a Block is a read only variable.

        :return: the hash of the previous Block in the BlockChain as a string.
        """
        return self.__hash_previous

    def init_with_previous(self, hash_previous: str):
        """
        Initializes a new Block with given previous hash of a previous Block. Because fields of
        a Block should stay imputable. Therefore a new Block is created.

        :return: a completely new Block object with the new given previous hash.
        """
        return Block(self.hash, (self.index_all, self.ordinal), self.chunk, hash_previous)


class BlockChain:
    """
    Class that represents the BlockChain.
    All methods are thread safe, so multiple threads can operate on the BlockChain.
    """

    def __init__(self):
        self.__chain: Dict[str, Dict[int, Block]] = dict()
        self.__hash_tail = None
        self.__lock = threading.Lock()

    def contains(self, hashcode: str) -> bool:
        with self.__lock:
            return self.__chain.__contains__(hashcode)

    def check(self, hashcode: str) -> bool:
        with self.__lock:
            if not self.__chain.__contains__(hashcode):
                return False
            blocks = self.__chain[hashcode]
            block = set(blocks.values()).pop()
            if block.index_all != len(blocks):
                return False
            if block.hash_previous is not None:
                return self.check(block.hash_previous)
            return True

    def add(self, block: Block) -> None:
        with self.__lock:
            if self.__chain.__contains__(block.hash):
                blocks = self.__chain.get(block.hash)
                if blocks.__contains__(block.ordinal):
                    raise ValueError("Block already exists!")
                existing_block = set(blocks.values()).pop()
                if existing_block.index_all == len(blocks):
                    raise ValueError("The Blocks stored under the given hash are already full!")
                blocks[block.ordinal] = block.init_with_previous(existing_block.hash_previous)
            else:
                self.__chain[block.hash] = {
                    block.ordinal: block.init_with_previous(self.__hash_tail)
                }
                self.__hash_tail = block.hash
