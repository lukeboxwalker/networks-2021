from typing import Dict


class Block:

    def __init__(self, hashcode: str, index_all: int, ordinal: int, chunk: bytes, hash_previous: str = None):
        self.__hashcode = hashcode
        self.__index_all = index_all
        self.__ordinal = ordinal
        self.__chunk = chunk
        self.__hash_previous = hash_previous

    @property
    def hash(self):
        return self.__hashcode

    @property
    def index_all(self):
        return self.__index_all

    @property
    def ordinal(self):
        return self.__ordinal

    @property
    def chunk(self):
        return self.__chunk

    @property
    def hash_previous(self):
        return self.__hash_previous

    def init_with_previous(self, hash_previous: str):
        return Block(self.hash, self.index_all, self.ordinal, self.chunk, hash_previous)


class BlockChain:

    def __init__(self):
        self.__chain: Dict[str, Dict[int, Block]] = dict()
        self.__hash_tail = None

    def contains(self, hashcode: str) -> bool:
        return self.__chain.__contains__(hashcode)

    def check(self, hashcode: str) -> bool:
        if not self.contains(hashcode):
            return False
        blocks = self.__chain[hashcode]
        block = set(blocks.values()).pop()
        if block.index_all != len(blocks):
            return False
        if block.hash_previous is not None:
            return self.check(block.hash_previous)
        return True

    def add_block(self, block: Block) -> None:
        if self.contains(block.hash):
            blocks = self.__chain.get(block.hash)
            if blocks.__contains__(block.ordinal):
                raise ValueError("Block already exists!")
            existing_block = set(blocks.values()).pop()
            if existing_block.index_all == len(blocks):
                raise ValueError("The Blocks stored under the given hash are already full!")
            blocks[block.ordinal] = block.init_with_previous(existing_block.hash_previous)
        else:
            self.__chain[block.hash] = {block.ordinal: block.init_with_previous(self.__hash_tail)}
            self.__hash_tail = block.hash

