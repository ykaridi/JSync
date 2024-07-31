from pathlib import Path

from common.symbol_store import SymbolStoreABC
from .pysqlite_symbol_store import PySqliteSymbolStore
from .symbol_server import SymbolServer


class DefaultSymbolServer(SymbolServer):
    def __init__(self, host: str, port: int, store_directory: Path):
        super().__init__(host, port)
        self._store_directory = store_directory

    def _get_store(self, project: str) -> SymbolStoreABC:
        return PySqliteSymbolStore(str((self._store_directory / project).with_suffix('.symbol_store')))
