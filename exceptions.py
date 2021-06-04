class BlockInsertionError(Exception):
    """
    Raised when a Block can not be inserted into the BlockChain.
    """


class BlockSectionInconsistentError(Exception):
    """
    Raised when Blocks of a block section are inconsistent.
    """


class PackageCreationError(Exception):
    """
    Raised when unable to create package.
    """


class PackageHandleError(Exception):
    """
    Raised when unable to handle package.
    """
