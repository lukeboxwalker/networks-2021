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
    def test_equals_and_hash(self, hashcode, index_all, ordinal, chunk, filename):
        block1 = Block(hashcode, index_all, ordinal, chunk, filename)
        block2 = Block(hashcode, index_all, ordinal, chunk, filename)

        # should be equal
        self.assertTrue(block1.__eq__(block2))
        self.assertTrue(block2.__eq__(block1))
        self.assertEqual(block1.__hash__(), block2.__hash__())

        # the hash_previous should not be part of the equal
        block1 = Block(hashcode, index_all, ordinal, chunk, filename, "a51c23")
        block2 = Block(hashcode, index_all, ordinal, chunk, filename, None)

        # should be equal
        self.assertTrue(block1.__eq__(block2))
        self.assertTrue(block2.__eq__(block1))
        self.assertEqual(block1.__hash__(), block2.__hash__())


if __name__ == '__main__':
    unittest.main()
