class BlockAlreadyExistsError(Exception):
    """
    Raised when a Block in the BlockChain already exists when trying to add the new Block.
    """
    pass


class BlockSectionAlreadyFullError(Exception):
    """
    Raised when a Block section of a file in the BlockChain is already full when
    trying to add the new Block.
    """
    pass
