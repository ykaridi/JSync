from abc import ABCMeta

from common.symbol_store import SymbolStoreABC
from common.symbol import Symbol
from .sql_queries import (CLIENT_CREATE_SYMBOLS_TABLE_QUERY, CREATE_RENAME_RECORDS_TABLE_QUERY, PUSH_RENAME_QUERY,
                          DELETE_RENAME_QUERY, GET_RENAME_BY_CANONICAL_SIGNATURE_QUERY, GET_RENAMES_QUERY,
                          CLIENT_DELETE_SYMBOLS_QUERY)


class ClientSymbolStoreABC(SymbolStoreABC):
    __metaclass__ = ABCMeta

    def __init__(self, path):
        # type: (str) -> None
        SymbolStoreABC.__init__(self, path)

    def initialize_database(self):
        # type: () -> None
        self._conn.execute(CLIENT_CREATE_SYMBOLS_TABLE_QUERY)
        self._conn.execute(CREATE_RENAME_RECORDS_TABLE_QUERY)

    @property
    def latest_known_renames(self):
        # type: () -> dict[str, Symbol]
        results = self._conn.execute_query(GET_RENAMES_QUERY)
        return {canonical_signature: Symbol(symbol_type, canonical_signature, name)
                for canonical_signature, symbol_type, name in results}

    def get_latest_known_rename(self, canonical_signature):
        # type: (str) -> Symbol | None
        results = list(self._conn.execute_query(GET_RENAME_BY_CANONICAL_SIGNATURE_QUERY, canonical_signature))
        if len(results) == 0:
            return None
        else:
            name, symbol_type = results[0]
            return Symbol(symbol_type, canonical_signature, name)

    def record_latest_known_renames(self, symbols):
        # type: (list[Symbol]) -> None
        deleted_symbols = [symbol for symbol in symbols if symbol.name is None]
        changed_symbols = [symbol for symbol in symbols if symbol.name is not None]

        if len(deleted_symbols) > 0:
            self._conn.executemany(DELETE_RENAME_QUERY, [(symbol.canonical_signature, ) for symbol in deleted_symbols])
        if len(changed_symbols) > 0:
            self._conn.executemany(PUSH_RENAME_QUERY, [(symbol.canonical_signature, symbol.symbol_type, symbol.name)
                                                       for symbol in changed_symbols])

    def delete_symbols(self, symbols):
        batch = [(symbol.author, symbol.canonical_signature) for symbol in symbols]

        return self._conn.executemany(CLIENT_DELETE_SYMBOLS_QUERY, batch)
