from abc import ABCMeta, abstractmethod


class ConnectionABC(object):
    __metaclass__ = ABCMeta

    def __init__(self, host, port):
        # type: (str, int) -> None
        self.host = host
        self.port = port

    @abstractmethod
    def send_packet(self, data):
        # type: (bytes) -> None
        raise NotImplementedError

    @abstractmethod
    def recv_packet(self):
        # type: () -> bytes
        raise NotImplementedError

    @abstractmethod
    def close(self):
        # type: () -> None
        raise NotImplementedError


class ConnectionError(Exception):
    pass
