import hashlib

from typing import List, Tuple

from data import Block, BlockChain

BUF_SIZE = 500


def create_blocks(chunks: List[bytes]) -> Tuple[str, List[Block]]:
    sha256 = hashlib.sha256()
    for chunk in chunks:
        sha256.update(chunk)
    size = len(chunks)
    hashcode = sha256.hexdigest()
    return hashcode, [Block(hashcode, size, i, chunks[i]) for i in range(size)]


def load_file(filename: str) -> List[bytes]:
    chunks: List[bytes] = []
    with open(filename, "rb") as f:
        while True:
            chunk = f.read(BUF_SIZE)
            if not chunk:
                break
            chunks.append(chunk)
    return chunks


if __name__ == '__main__':
    block_chain = BlockChain()

    hashcode, blocks = create_blocks(load_file("data.py"))

    for i in range(len(blocks)):
        block_chain.add_block(blocks[i])
