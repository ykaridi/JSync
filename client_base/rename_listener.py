import time
from abc import ABCMeta, abstractmethod

from common.symbol import Symbol
from common.commands import UpstreamSymbols
from .connection import ConnectionABC


class RenameListenerABC(object):
    __metaclass__ = ABCMeta

    def __init__(self, connection):
        # type: (ConnectionABC) -> None
        self._connection = connection

    def on_rename(self, project, symbol):
        # type: (str, Symbol) -> None
        symbol = symbol.clone(timestamp=int(time.time()))
        command = UpstreamSymbols(project, [symbol], loggable=True)
        self._connection.send_packet(command.encode())

    @abstractmethod
    def start(self):
        raise NotImplemented
