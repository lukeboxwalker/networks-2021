import time
import unittest

from web import Server, Client


class ServerTest(unittest.TestCase):
    ip = "localhost"
    port = 0

    def test_add_and_check_file(self):
        server = Server(self.ip, self.port)
        server.start()

        client = Client(self.ip, server.address[1])
        client.connect()

        try:
            self.assertEqual(server.block_chain.size(), 0)

            hash_value = "4e37d60eb59da9087a225efdebcefa522d0b10093b908c31c2bf41e126efda6a"
            client.add_file("ressources/example_file.txt")
            time.sleep(1)  # wait for server to read blocks

            # Blockchain should contain the file which consists of 8 blocks
            self.assertEqual(server.block_chain.check_hash(hash_value), (True, 8))

            # Blockchain should contain 1 complete file
            self.assertEqual(server.block_chain.check(), (True, 1))
        finally:
            server.stop()
            client.close()


if __name__ == '__main__':
    unittest.main()
