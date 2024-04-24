from pathlib import Path

from .sqlite_symbol_store import SqliteSymbolStore
from .symbol_store import SymbolStore
from .symbol_server import SymbolServer


class DefaultSymbolServer(SymbolServer):
    def __init__(self, host: str, port: int, store_directory: Path):
        super().__init__(host, port)
        self._store_directory = store_directory

    def _get_store(self, project: str) -> SymbolStore:
        return SqliteSymbolStore((self._store_directory / project).with_suffix('.symbol_store'))
