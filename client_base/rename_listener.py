import time
from abc import ABCMeta, abstractmethod

from common.symbol import Symbol
from common.commands import UpstreamSymbols
from .connection import ConnectionABC
from .rename_engine import RenameEngineABC


class RenameListenerABC(object):
    __metaclass__ = ABCMeta

    def __init__(self, connection, rename_engine, name):
        # type: (ConnectionABC, RenameEngineABC, str) -> None
        self._connection = connection
        self._rename_engine = rename_engine
        self._name = name

    def on_rename(self, project, symbol):
        # type: (str, Symbol) -> None
        if self._rename_engine.is_symbol_synced(project, symbol, True):
            return

        symbol = symbol.clone(timestamp=int(time.time()))

        self._rename_engine.record_rename(project, symbol)
        self._rename_engine.record_symbols(project, [symbol.clone(author=self._name)])
        self._rename_engine.flush_symbols()

        command = UpstreamSymbols(project, [symbol], loggable=True)
        self._connection.send_packet(command.encode())

    @abstractmethod
    def start(self):
        raise NotImplementedError
