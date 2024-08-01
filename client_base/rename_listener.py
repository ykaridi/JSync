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
        if self._rename_engine.is_symbol_rename_known(project, symbol, True):
            return

        symbol = symbol.timestamped.authored(self._rename_engine.self_author)

        self._rename_engine.record_latest_known_renames(project, [symbol])
        self._rename_engine.record_symbols(project, [symbol])
        self._rename_engine.flush_all_symbols()

        command = UpstreamSymbols(project, [symbol], loggable=True)
        self._connection.send_packet(command.encode())

    @abstractmethod
    def start(self):
        raise NotImplementedError
