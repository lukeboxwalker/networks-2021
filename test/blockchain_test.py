import unittest
from typing import List

from data import BlockChain, load_file, BlockCMD, Block
from exceptions import DuplicateBlockError


def blocks_equals(test: unittest.TestCase, cmd_blocks: List[BlockCMD], blocks: List[Block]):
    cmd_blocks.sort(key=lambda x: x.ordinal)
    blocks.sort(key=lambda x: x.ordinal)

    for i in range(len(blocks)):
        loaded = blocks[i]
        original = cmd_blocks[i]

        test.assertEqual(original.hash, loaded.hash)
        test.assertEqual(original.filename, loaded.filename)
        test.assertEqual(original.index_all, loaded.index_all)
        test.assertEqual(original.ordinal, loaded.ordinal)
        test.assertEqual(original.chunk, loaded.chunk)


class BlockChainTest(unittest.TestCase):

    def test_init(self):
        hashcode = "eca493c3d7af03fc749e33809abf607dff49e3951b4741b5e3af30e637ebb07e"
        block_chain = BlockChain(in_memory=True)

        self.assertEqual(block_chain.size(), 0)  # initial length of blockchain should be 0
        self.assertEqual(block_chain.get(hashcode), [])  # should not contain any blocks
        self.assertEqual(block_chain.file_exists(hashcode), (False, 0))  # should not exits

    def test_add_blocks(self):
        block_chain = BlockChain(in_memory=True)

        original_blocks: List[BlockCMD] = load_file("ressources/example_file.txt")
        hashcode = original_blocks[0].hash

        for block in original_blocks:
            block_chain.add(block)

        # length should be len of blocks added
        self.assertEqual(block_chain.size(), len(original_blocks))

        # should exits
        self.assertEqual(block_chain.file_exists(hashcode), (True, len(original_blocks)))

        blocks_equals(self, original_blocks, block_chain.get(hashcode))

    def test_add_same_blocks_twice(self):
        block_chain = BlockChain(in_memory=True)

        original_blocks: List[BlockCMD] = load_file("ressources/example_file.txt")
        hashcode = original_blocks[0].hash

        for block in original_blocks:
            block_chain.add(block)
            # Cannot add same block again
            self.assertRaises(DuplicateBlockError, lambda: block_chain.add(block))

        # length should be len of blocks added
        self.assertEqual(block_chain.size(), len(original_blocks))

        # should exits
        self.assertEqual(block_chain.file_exists(hashcode), (True, len(original_blocks)))

        blocks_equals(self, original_blocks, block_chain.get(hashcode))


if __name__ == '__main__':
    unittest.main()
