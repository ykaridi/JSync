from pathlib import Path
from typing import Optional
from zipfile import ZipFile

from common.symbol_store import SymbolStoreABC
from .pysqlite_symbol_store import PySqliteSymbolStore
from .symbol_server import SymbolServer


class DefaultSymbolServer(SymbolServer):
    def __init__(self, host: str, port: int, store_directory: Path, resources: Path):
        super().__init__(host, port)
        self._store_directory = store_directory
        self._resources = resources

    def _get_resource(self, name: str) -> Optional[bytes]:
        if self._resources.is_dir():
            if not (self._resources / name).exists():
                return None
            return (self._resources / name).read_bytes()
        elif self._resources.is_file() and self._resources.suffix == '.zip':
            name = 'resources/' + name
            with ZipFile(self._resources, 'r') as zipfile:
                if name in zipfile.namelist():
                    return zipfile.read(name)
                else:
                    return None

    def _get_store(self, project: str) -> SymbolStoreABC:
        return PySqliteSymbolStore(str((self._store_directory / project).with_suffix('.db')))
