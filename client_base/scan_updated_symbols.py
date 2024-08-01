from abc import ABCMeta, abstractmethod

from common.symbol import Symbol
from common.commands import UpstreamSymbols
from .connection import ConnectionABC
from .rename_engine import RenameEngineABC


class ScanUpdatedSymbols(object):
    __metaclass__ = ABCMeta

    def __init__(self, connection, rename_engine, projects):
        # type: (ConnectionABC, RenameEngineABC, list[str]) -> None
        self._connection = connection
        self._rename_engine = rename_engine
        self._projects = projects

    def report_renamed_symbols(self, project, symbols):
        # type: (str, list[Symbol]) -> None
        self._handle_updated_symbols(project, symbols)

    @abstractmethod
    def is_symbol_reverted(self, project, symbol):
        # type: (str, Symbol) -> bool
        raise NotImplementedError

    def _handle_reverted_symbols(self, project):
        # type: (str) -> None
        reverted_symbols = []
        for symbol in self._rename_engine.get_latest_known_renames(project):
            if not self.is_symbol_reverted(project, symbol.named(self._rename_engine.get_name(project, symbol))):
                continue

            reverted_symbols.append(symbol.named(self._rename_engine.get_original_name(project, symbol)))

        self._handle_updated_symbols(project, reverted_symbols)

    def _handle_updated_symbols(self, project, symbols):
        # type: (str, list[Symbol]) -> None
        if len(symbols) > 0:
            symbols = [symbol.timestamped.authored(self._rename_engine.self_author) for symbol in symbols]

            self._rename_engine.record_latest_known_renames(project, symbols)
            self._rename_engine.record_symbols(project, symbols)
            self._rename_engine.flush_all_symbols()

            command = UpstreamSymbols(project, symbols, loggable=False)
            self._connection.send_packet(command.encode())

    def handle_reverted_symbols(self):
        for project in self._projects:
            self._handle_reverted_symbols(project)

    @abstractmethod
    def run(self):
        # type: () -> None
        raise NotImplementedError
