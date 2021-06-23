import unittest
from concurrent.futures.thread import ThreadPoolExecutor
from typing import List

from data import BlockChain, load_file, Block
from exceptions import DuplicateBlockError


class BlockChainTest(unittest.TestCase):

    def test_init(self):
        hashcode = "eca493c3d7af03fc749e33809abf607dff49e3951b4741b5e3af30e637ebb07e"
        block_chain = BlockChain(in_memory=True)

        self.assertEqual(block_chain.size(), 0)  # initial length of blockchain should be 0
        self.assertEqual(block_chain.get(hashcode), [])  # should not contain any blocks
        self.assertEqual(block_chain.file_exists(hashcode), (False, 0))  # should not exits

    def test_add_blocks(self):
        block_chain = BlockChain(in_memory=True)

        original_blocks: List[Block] = load_file("ressources/example_file.txt")
        hashcode = original_blocks[0].hash

        for block in original_blocks:
            block_chain.add(block)

        # length should be len of blocks added
        self.assertEqual(block_chain.size(), len(original_blocks))

        # should exits and be equal
        self.assertEqual(block_chain.file_exists(hashcode), (True, len(original_blocks)))
        self.assertEqual(original_blocks, block_chain.get(hashcode))

    def test_add_same_blocks_twice(self):
        block_chain = BlockChain(in_memory=True)

        blocks: List[Block] = load_file("ressources/example_file.txt")
        hashcode = blocks[0].hash

        for block in blocks:
            block_chain.add(block)
            # Cannot add same block again
            self.assertRaises(DuplicateBlockError, lambda: block_chain.add(block))

        # length should be len of blocks added
        self.assertEqual(block_chain.size(), len(blocks))

        # should exits and be equal
        self.assertEqual(block_chain.file_exists(hashcode), (True, len(blocks)))
        self.assertEqual(blocks, block_chain.get(hashcode))

    def test_concurrent_add_same_file(self):
        block_chain = BlockChain(in_memory=True)

        blocks: List[Block] = load_file("ressources/example_image.jpg")
        hashcode = blocks[0].hash

        def add():
            try:
                for block in blocks:
                    block_chain.add(block)
            except DuplicateBlockError:
                pass

        futures = []

        with ThreadPoolExecutor(max_workers=8) as executor:
            for _ in range(16):
                futures.append(executor.submit(add))

        for future in futures:
            future.result()

        # length should be len of blocks added
        self.assertEqual(block_chain.size(), len(blocks))

        # should exits and be equal
        self.assertEqual(block_chain.file_exists(hashcode), (True, len(blocks)))
        self.assertEqual(blocks, block_chain.get(hashcode))


if __name__ == '__main__':
    unittest.main()
