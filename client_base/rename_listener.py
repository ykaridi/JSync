import time
from abc import ABCMeta, abstractmethod

from common.symbol import Symbol
from common.commands import UpstreamSymbols
from .connection import ConnectionABC
from .rename_engine import RenameEngineABC


class RenameListenerABC(object):
    __metaclass__ = ABCMeta

    def __init__(self, connection, rename_engine):
        # type: (ConnectionABC, RenameEngineABC) -> None
        self._connection = connection
        self._rename_engine = rename_engine

    def on_rename(self, project, symbol):
        # type: (str, Symbol) -> None
        self._rename_engine.record_rename(project, symbol)

        symbol = symbol.clone(timestamp=int(time.time()))
        command = UpstreamSymbols(project, [symbol], loggable=True)
        self._connection.send_packet(command.encode())

    @abstractmethod
    def start(self):
        raise NotImplemented
