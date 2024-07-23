from abc import ABCMeta, abstractmethod


class ConnectionABC(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def send_packet(self, data):
        # type: (bytes) -> None
        raise NotImplemented

    @abstractmethod
    def recv_packet(self):
        # type: () -> bytes
        raise NotImplemented

    @abstractmethod
    def close(self):
        raise NotImplemented


class ConnectionError(Exception):
    pass
