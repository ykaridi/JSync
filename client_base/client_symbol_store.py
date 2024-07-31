from abc import ABCMeta

from common.symbol_store import SymbolStoreABC
from .sql_queries import (CLIENT_CREATE_SYMBOLS_TABLE_QUERY, CREATE_RENAME_RECORDS_TABLE_QUERY, PUSH_RENAME_QUERY,
                          DELETE_RENAME_QUERY, GET_RENAME_QUERY, CLIENT_DELETE_SYMBOLS_QUERY)


class ClientSymbolStoreABC(SymbolStoreABC):
    __metaclass__ = ABCMeta

    def initialize_database(self):
        self._conn.execute(CLIENT_CREATE_SYMBOLS_TABLE_QUERY)
        self._conn.execute(CREATE_RENAME_RECORDS_TABLE_QUERY)

    def get_latest_rename(self, canonical_signature):
        # type: (str) -> str | None
        results = list(self._conn.execute_query(GET_RENAME_QUERY, canonical_signature))
        if len(results) == 0:
            return None
        else:
            return results[0][0]

    def record_rename(self, canonical_signature, name):
        # type: (str, str) -> None
        if name is None:
            self._conn.execute(DELETE_RENAME_QUERY, canonical_signature)
        else:
            self._conn.execute(PUSH_RENAME_QUERY, canonical_signature, name)

    def delete_symbols(self, symbols):
        batch = [(symbol.author, symbol.canonical_signature) for symbol in symbols]
        return self._conn.executemany(CLIENT_DELETE_SYMBOLS_QUERY, batch)
