import time
from abc import ABCMeta, abstractmethod

from common.symbol import Symbol
from common.commands import UpstreamSymbols
from .connection import ConnectionABC


class SyncToServerABC(object):
    __metaclass__ = ABCMeta

    def __init__(self, connection):
        # type: (ConnectionABC) -> None
        super(SyncToServerABC, self).__init__()
        self._connection = connection

    def upload_symbols(self, project, symbols):
        # type: (str, list[Symbol]) -> None
        if len(symbols) > 0:
            symbols = [symbol.clone(timestamp=time.time()) for symbol in symbols]
            command = UpstreamSymbols(project, symbols, loggable=False)
            self._connection.send_packet(command.encode())

    @abstractmethod
    def run(self):
        # type: () -> None
        raise NotImplemented
