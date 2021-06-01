import hashlib
import os
from typing import List, Tuple
from data import Block, BlockChain


def create_blocks(chunks: List[bytes], filename: str) -> Tuple[str, List[Block]]:
    sha256 = hashlib.sha256()
    for chunk in chunks:
        sha256.update(chunk)
    size = len(chunks)
    hashcode = sha256.hexdigest()
    return hashcode, [Block(hashcode, size, i, chunks[i], filename) for i in range(size)]


def create_file_from_blocks(blocks: List[Block]):
    if not blocks:
        return
    blocks.sort(key=lambda x: x.ordinal)
    with open("test" + blocks[0].filename, "wb") as f:
        for block in blocks:
            f.write(block.chunk)


def load_file(filepath: str) -> List[bytes]:
    chunks: List[bytes] = []
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(Block.CHUNK_SIZE)
            if not chunk:
                break
            chunks.append(chunk)
    return chunks


if __name__ == '__main__':
    filepath = "data.py"
    name = os.path.split(filepath)

    block_chain = BlockChain()

    hashcode, blocks = create_blocks(load_file(filepath), name[1])
    for block in blocks:
        block_chain.add(block)

    create_file_from_blocks(block_chain.get(hashcode))