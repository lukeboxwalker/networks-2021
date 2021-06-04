import pickle
from typing import Callable, Dict, Tuple
from enum import IntEnum
from exceptions import PackageCreationError, PackageHandleError
from logger import LogResult, LogLevel, logger


class PackageMode(IntEnum):
    SERVER_MODE = 0x80  # server mode 1 at the first bit
    CLIENT_MODE = 0x00  # client mode 0 at the first bit


class PackageId(IntEnum):
    LOG_TEXT = 0x00  # send/receive text to console log
    SEND_FILE = 0x01  # send/receive blocks of a file
    HASH_CHECK = 0x02  # send/receive hash to check
    FILE_CHECK = 0x03  # send/receive blocks of a file to check
    GET_FILE = 0x04  # send/receive hash to get blocks of a file


class Package:
    def __init__(self, package_mode: int, package_id: int, payload: bytes):
        self.__package_mode = package_mode  # either 0x80 (server) or 0x00 (client)
        self.__package_id = package_id  # package id possible range from 0x00 to 0x7F
        self.__payload = payload

    @property
    def package_id(self):
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
        return self.__package_mode

    def get_object(self) -> object:
        return pickle.loads(self.__payload)


class PackageFactory:
    def __init__(self, package_mode: PackageMode):
        self.__package_mode = package_mode
        self.packages_ids = {packages_id.value for packages_id in PackageId}

    @property
    def package_mode(self):
        return self.__package_mode

    def create_log_package(self, log_level: LogLevel, message: str):
        log_result = LogResult(log_level, message)
        logger.log(log_result)
        return self.create_from_object(PackageId.LOG_TEXT, LogResult(log_level, message))

    def create_from_bytes(self, data: bytes):
        if not data:
            raise PackageCreationError("Bytearray is empty. Can't construct package!")

        header = int.from_bytes(data[:1], byteorder="little", signed=False)
        package_mode = 0x80 & header
        package_id = 0x7F & header

        if not self.packages_ids.__contains__(package_id):
            raise PackageCreationError("Package ID " + str(package_id) + "invalid!")

        return Package(package_mode, package_id, data[1:])

    def create_from_object(self, package_id: int, data: object) -> Package:
        if not self.packages_ids.__contains__(package_id):
            raise PackageCreationError("Package ID " + str(package_id) + "invalid!")

        return Package(self.package_mode, package_id, pickle.dumps(data))


class PackageHandler:
    def __init__(self, package_mode: PackageMode, package_factory: PackageFactory):
        self.__package_mode = package_mode
        self.__handlers: Dict[int, Callable[[object], Package]] = dict()
        self.__package_factory = package_factory

    def install(self, package_id: int, handler: Callable):
        self.__handlers[package_id] = handler

    def remove(self, package_id: int):
        del self.__handlers[package_id]

    def handle(self, byte_buffer: bytes) -> Package:
        package = self.__package_factory.create_from_bytes(byte_buffer)

        if package.package_mode != self.__package_mode:
            raise PackageHandleError("Package is not meant to be handled by this package handler!")

        if not self.__handlers.__contains__(package.package_id):
            raise PackageHandleError("There is no handler installed to handle package id "
                                     + str(package.package_id) + "!")

        handler = self.__handlers.get(package.package_id)
        return handler(package.get_object())

