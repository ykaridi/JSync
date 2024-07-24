from abc import ABCMeta, abstractmethod


class ConnectionABC(object):
    __metaclass__ = ABCMeta

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
