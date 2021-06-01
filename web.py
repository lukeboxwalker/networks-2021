import socket
import threading
from typing import Tuple, Callable


class Client:
    def __init__(self, addr: Tuple[str, int]):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self.__socket.connect(addr)

    def receive(self) -> str:
        buf = self.__socket.recv(1024)
        result = ""
        while buf:
            result += buf.decode("utf-8")
            buf = self.__socket.recv(1024)
        return result

    def send(self, msg: str):
        self.__socket.send(bytes(msg, "utf-8"))

    def close(self):
        self.__socket.close()


class ClientSocket:
    def __init__(self, connection: Tuple, on_close: Callable):
        self.__connection = connection
        self.__on_close = on_close

    def close(self):
        try:
            self.__socket.close()
        finally:
            self.__on_close(self)

    def receive(self) -> str:
        buf = self.__socket.recv(1024)
        result = ""
        while buf:
            result += buf.decode("utf-8")
            buf = self.__socket.recv(1024)
        return result

    def send(self, msg: str):
        self.__socket.send(bytes(msg, "utf-8"))

    @property
    def __socket(self) -> socket:
        return self.__connection[0]

    @property
    def host(self):
        return self.__connection[1][0]

    @property
    def port(self):
        return self.__connection[1][1]

    @property
    def address(self) -> str:
        return str(self.host) + ":" + str(self.port)


class Server:
    def __init__(self, addr: Tuple[str, int], on_open_socket: Callable):
        self.__on_open_socket = on_open_socket

        # server socket
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self.__socket.bind(addr)

        # connected clients
        self.__client_sockets = set()

        # threading variables to accept connections
        self.__listener = threading.Thread(target=self.__listen, daemon=True)
        self.__lock = threading.Lock()
        self.__stopped = threading.Event()

    def __remove_socket(self, client_socket: ClientSocket):
        with self.__lock:
            self.__client_sockets.remove(client_socket)

    def __add_socket(self, client_socket: ClientSocket):
        with self.__lock:
            self.__client_sockets.add(client_socket)

    def __listen(self):
        while not self.__stopped.isSet():
            client_socket = ClientSocket(self.__socket.accept(), on_close=self.__remove_socket)
            self.__add_socket(client_socket)
            self.__on_open_socket(client_socket)

    def start(self):
        self.__socket.listen(socket.SOMAXCONN)
        self.__listener.start()

    def stop(self):
        self.__stopped.set()
        self.__socket.close()
