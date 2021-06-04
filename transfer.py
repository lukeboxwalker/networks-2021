import pickle
from typing import Callable, Dict

from exceptions import PackageCreationError, PackageHandleError

SERVER_MODE = 0x80
CLIENT_MODE = 0x00


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

    def is_server_package(self) -> bool:
        return self.__package_mode == SERVER_MODE

    def is_client_package(self) -> bool:
        return self.__package_mode == CLIENT_MODE

    def get_object(self) -> object:
        return pickle.loads(self.__payload)


class PackageFactory:
    def __init__(self):
        self.packages = {

        }

    def create_from_bytes(self, data: bytes):
        if not data:
            raise PackageCreationError("Bytearray is empty. Can't construct package!")

        header = int.from_bytes(data[:1], byteorder="little", signed=False)
        package_mode = 0x80 & header
        package_id = 0x7F & header

        if not self.packages.__contains__(package_id):
            raise PackageCreationError("Package ID " + str(package_id) + "invalid!")

        return Package(package_mode, package_id, data[1:])

    def create_from_object(self, package_id: int, package_mode: int, data: object) -> Package:
        if not self.packages.__contains__(package_id):
            raise PackageCreationError("Package ID " + str(package_id) + "invalid!")

        if package_mode != SERVER_MODE or package_mode != CLIENT_MODE:
            raise PackageCreationError("Unknown package mode " + str(package_mode) + "!")

        return Package(package_mode, package_id, pickle.dumps(data))

    def create_client_package(self, package_id: int, data: object) -> Package:
        return self.create_from_object(package_id, CLIENT_MODE, data)

    def create_server_package(self, package_id: int, data: object) -> Package:
        return self.create_from_object(package_id, SERVER_MODE, data)


class PackageHandler:
    def __init__(self, handler_mode: int = SERVER_MODE):
        if handler_mode != SERVER_MODE or handler_mode != CLIENT_MODE:
            raise ValueError("Unknown handler mode " + str(handler_mode) + "!")

        self.__handler_mode = handler_mode
        self.__handlers: Dict[int, Callable] = dict()

    def install_handler(self, package_id: int, handler: Callable):
        self.__handlers[package_id] = handler

    def remove_handler(self, package_id: int):
        del self.__handlers[package_id]

    def handle(self, package: Package):
        if package.package_mode != self.__handler_mode:
            raise PackageHandleError("Package is not meant to be handled by this package handler!")

        if not self.__handlers.__contains__(package.package_id):
            raise PackageHandleError("There is no handler installed to handle package id "
                                     + str(package.package_id) + "!")

        handler = self.__handlers.get(package.package_id)
        handler(package.get_object())
