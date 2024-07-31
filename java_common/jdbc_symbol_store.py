from client_base.client_symbol_store import ClientSymbolStoreABC
from java_common.sqlite_adapter import SqliteAdapter


class JDBCClientSymbolStore(ClientSymbolStoreABC):
    def connect(self, path):
        # type: (str) -> SqliteAdapter
        return SqliteAdapter(path)
