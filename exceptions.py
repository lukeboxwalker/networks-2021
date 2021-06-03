class BlockInsertionError(Exception):
    """
    Raised when a Block can not be inserted into the BlockChain.
    """


class BlockSectionInconsistentError(Exception):
    """
    Raised when a Blocks of a block section are inconsistent.
    """
