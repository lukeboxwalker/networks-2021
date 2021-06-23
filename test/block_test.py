import random
import unittest

from parameterized import parameterized
from data import Block


class BlockTest(unittest.TestCase):

    @parameterized.expand([list(x) for x in zip(*[
        ["4e37d", "60eb59", "9087a2", "b22bce8", "2d0b10", "08c2bf", "af03fc", "49e395", "41b5e3"],
        [random.randint(0, 1024) for _ in range(9)],
        [random.randint(0, 1024) for _ in range(9)],
        [random.randint(0, 1024).to_bytes(2, byteorder="big") for _ in range(9)],
        ["test1", "test2", "test3", "test4", "test5", "test6", "test7", "test8", "test9"]
    ])])
    def test_unmodifiable(self, hashcode, index_all, ordinal, chunk, filename):
        unmodifiable_block = Block.no_previous("dff49e", 0, 0, b'0', "file")

        def set_hash():
            unmodifiable_block.hash = hashcode

        def set_index_all():
            unmodifiable_block.index_all = index_all

        def set_ordinal():
            unmodifiable_block.ordinal = ordinal

        def set_chunk():
            unmodifiable_block.chunk = chunk

        def set_filename():
            unmodifiable_block.filename = filename

        def set_hash_previous():
            unmodifiable_block.hash_previous = hashcode

        # should not be able to manipulate any of the fields
        self.assertRaises(AttributeError, set_hash)
        self.assertRaises(AttributeError, set_index_all)
        self.assertRaises(AttributeError, set_ordinal)
        self.assertRaises(AttributeError, set_chunk)
        self.assertRaises(AttributeError, set_filename)
        self.assertRaises(AttributeError, set_hash_previous)


if __name__ == '__main__':
    unittest.main()
