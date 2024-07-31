from abc import ABCMeta, abstractmethod

from common.sqlite_adapter import SqliteAdapterABC
from common.symbol import Symbol
from common.sql_queries import (CREATE_SYMBOLS_TABLE_QUERY, PUSH_SYMBOLS_QUERY, GET_SYMBOLS_QUERY,
                                GET_SYMBOLS_CANONICAL_SIGNATURE_QUERY, GET_SYMBOLS_AUTHOR_QUERY,
                                GET_SYMBOLS_CANONICAL_SIGNATURE_AUTHOR_QUERY, DELETE_SYMBOLS_QUERY)


class SymbolStoreABC(object):
    __metaclass__ = ABCMeta

    def __init__(self, path):
        # type: (str) -> None
        self._path = path
        self._conn = self.connect(path)
        self.initialize_database()

    def initialize_database(self):
        self._conn.execute(CREATE_SYMBOLS_TABLE_QUERY)

    @abstractmethod
    def connect(self, path):
        # type: (str) -> SqliteAdapterABC
        raise NotImplementedError

    def changed_symbols(self, symbols):
        # type: (iter[Symbol]) -> iter[Symbol]
        for symbol in symbols:
            existing_symbols = list(self.get_symbols(canonical_signature=symbol.canonical_signature,
                                                     author=symbol.author))

            if len(existing_symbols) == 0:
                yield symbol
            else:
                existing_symbol, = existing_symbols
                if symbol.name != existing_symbol.name:
                    yield symbol

    def push_symbol(self, symbol):
        # type: (Symbol) -> None
        row = (symbol.author, symbol.symbol_type, symbol.canonical_signature, symbol.name, symbol.timestamp)
        return self._conn.execute_update(PUSH_SYMBOLS_QUERY, *row)

    def push_symbols(self, symbols):
        # type: (iter[Symbol]) -> None
        batch = [(symbol.author, symbol.symbol_type, symbol.canonical_signature, symbol.name, symbol.timestamp)
                 for symbol in symbols]
        return self._conn.executemany(PUSH_SYMBOLS_QUERY, batch)

    def get_symbols(self, canonical_signature=None, author=None):
        # type: (str | None, str | None) -> iter[Symbol]
        if canonical_signature is None and author is None:
            results = self._conn.execute_query(GET_SYMBOLS_QUERY)
        elif canonical_signature is not None and author is None:
            results = self._conn.execute_query(GET_SYMBOLS_CANONICAL_SIGNATURE_QUERY, canonical_signature)
        elif canonical_signature is None and author is not None:
            results = self._conn.execute_query(GET_SYMBOLS_AUTHOR_QUERY, author)
        elif canonical_signature is not None and author is not None:
            results = self._conn.execute_query(GET_SYMBOLS_CANONICAL_SIGNATURE_AUTHOR_QUERY,
                                               canonical_signature, author)

        for row in results:  # noqa
            if all(x is None for x in row):
                continue

            author, symbol_type, canonical_signature, name, timestamp, _ = row
            yield Symbol(symbol_type, canonical_signature, name, timestamp=timestamp, author=author)

    def close(self):
        self._conn.close()
