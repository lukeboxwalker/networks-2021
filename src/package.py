"""
Module that holds the classes and functions needed for TCP package communication.
"""

import pickle
from typing import Callable, Dict
from enum import IntEnum
from src.exceptions import PackageCreationError, PackageHandleError
from src.logger import LogResult, LogLevel, logger


class PackageMode(IntEnum):
    """
    Enum of package mode ids to determine which if a package is meant to be handled by the
    client or server
    """

    SERVER_MODE = 0x80  # server mode, 1 at the first bit
    CLIENT_MODE = 0x00  # client mode, 0 at the first bit


class PackageId(IntEnum):
    """
    Enum of package ids to determine which function to call when receiving
    data from client or server.
    """

    LOG_TEXT = 0x00  # send/receive text to console log
    SEND_FILE = 0x01  # send/receive blocks of a file
    HASH_CHECK = 0x02  # send/receive hash to check
    FILE_CHECK = 0x03  # send/receive blocks of a file to check
    GET_FILE = 0x04  # send/receive hash to get blocks of a file


class Package:
    """
    Class to represent a Package (bytes) that are send or received.
    """

    def __init__(self, package_mode: int, package_id: int, payload: bytes):
        self.__package_mode = package_mode  # either 0x80 (server) or 0x00 (client)
        self.__package_id = package_id  # package id possible range from 0x00 to 0x7F
        self.__payload = payload

    @property
    def package_id(self):
        """
        Property function to ensure that the package id of the Package is a read only variable.

        :return: package id as an integer.
        """
        return self.__package_id

    @property
    def raw(self) -> bytes:
        """
        Gets the raw bytes of the package.

        The first byte of the data is the 'header' the rest is the actual payload
        the first bit is representing the 'package mode' whether the package is meant
        to be received from client (set to 0) or from server (set to 1) the rest
        of the header bits represents the package id.

        :return: raw bytes of the package.
        """
        return bytes([self.__package_mode | self.__package_id]) + self.__payload

    @property
    def package_mode(self):
        """
        Property function to ensure that the package mode of the Package is a read only variable.

        :return: package mode as an integer.
        """
        return self.__package_mode

    def get_object(self) -> object:
        """
        Loads the payload bytes with pickle back into a python object.

        :return: the payload object.
        """
        return pickle.loads(self.__payload)


class PackageFactory:
    """
    Class that is responsible to create packages.
    """

    def __init__(self, package_mode: PackageMode):
        self.__package_mode = package_mode
        self.packages_ids = {packages_id.value for packages_id in PackageId}

    @property
    def package_mode(self):
        """
        Property function to ensure that the package mode of the
        PackageFactory is a read only variable.

        The package mode determines if the factory constructs packages that should
        be send to the client or server.

        :return: package mode as an integer.
        """
        return self.__package_mode

    def create_log_package(self, log_level: LogLevel, message: str):
        """
        Create a log package and prints the message to the log.

        :param log_level: the log level of the message
        :param message: the message to log
        :return: the package that contains the log information.
        """
        log_result = LogResult(log_level, message)
        logger.log(log_result)
        return self.create_from_object(PackageId.LOG_TEXT, LogResult(log_level, message))

    def create_from_bytes(self, data: bytes):
        """
        Create a package form raw bytes.

        The first byte of the data is the 'header' the rest is the actual payload.
        The header determines the package mode as well as the package id.

        :param data:
        :raise PackageCreationError: if bytes are empty or package id is unknown.
        :return: a new package.
        """
        if not data:
            raise PackageCreationError("Bytearray is empty. Can't construct package!")

        # extracting header from data
        header = int.from_bytes(data[:1], byteorder="little", signed=False)
        package_mode = 0x80 & header
        package_id = 0x7F & header

        if not self.packages_ids.__contains__(package_id):
            raise PackageCreationError("Package ID " + str(package_id) + "invalid!")

        return Package(package_mode, package_id, data[1:])

    def create_from_object(self, package_id: int, data: object) -> Package:
        """
        Create a package with given package id and given object.

        :param package_id: the id of the package.
        :param data: the object to send with this package.
        :return: a new package.
        """
        if not self.packages_ids.__contains__(package_id):
            raise PackageCreationError("Package ID " + str(package_id) + "invalid!")

        return Package(self.package_mode, package_id, pickle.dumps(data))


class PackageHandler:
    """
    Class that is responsible for handling incoming packages (or bytes).
    """

    def __init__(self, package_mode: PackageMode, package_factory: PackageFactory):
        self.__package_mode = package_mode
        self.__handlers: Dict[int, Callable[[object], Package]] = dict()
        self.__package_factory = package_factory

    def install(self, package_id: int, handler: Callable):
        """
        Install a new handler for given package id. The handler is added to the handler dictionary.

        :param package_id: the package id the handler is bind to
        :param handler: to call if a package with given package id is received.
        """
        self.__handlers[package_id] = handler

    def remove(self, package_id: int):
        """
        Remove the handler bound to given package id form handler dictionary.

        :param package_id: the package id.
        """
        del self.__handlers[package_id]

    def handle(self, byte_buffer: bytes) -> Package:
        """
        Handling the given bytes as a package and call the installed handler.

        :param byte_buffer: raw package.
        :return: a package that should be sent back to the sender. Can be None.
        """

        # construct package from the given byte array
        package = self.__package_factory.create_from_bytes(byte_buffer)

        # if received package cant be handled by this handler mode an exception is raised
        if package.package_mode != self.__package_mode:
            raise PackageHandleError("Package is not meant to be handled by this package handler!")

        if not self.__handlers.__contains__(package.package_id):
            raise PackageHandleError("There is no handler installed to handle package id "
                                     + str(package.package_id) + "!")

        # calling the installed handler for the package.
        handler = self.__handlers.get(package.package_id)
        return handler(package.get_object())
