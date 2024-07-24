import itertools
import os
import sqlite3
from contextlib import closing
from typing import Iterable, Optional, List

from common.symbol import Symbol
from .symbol_store import SymbolStore

MAXIMAL_TRANSACTION_SIZE = 10000


class SqliteSymbolStore(SymbolStore):
    def __init__(self, path: os.PathLike):
        self._conn = sqlite3.connect(path)
        self._conn.execute("""
        CREATE TABLE IF NOT EXISTS symbols (
            author TEXT,
            symbol_type INTEGER,
            canonical_signature TEXT,
            name TEXT,
            timestamp INTEGER,
            PRIMARY KEY (author, canonical_signature, timestamp)
        );
        """)

    @staticmethod
    def _symbol_to_row(symbol: Symbol) -> List[str | int]:
        return [symbol.author, symbol.symbol_type, symbol.canonical_signature, symbol.name, symbol.timestamp]

    def push_symbols(self, symbols: Iterable[Symbol], only_changed: bool = True):
        symbols = iter(self.changed_symbols(symbols) if only_changed else symbols)
        with closing(self._conn.cursor()) as cur:
            while batch := [self._symbol_to_row(row) for row in itertools.islice(symbols, MAXIMAL_TRANSACTION_SIZE)]:
                cur.executemany("INSERT OR IGNORE INTO symbols(author, symbol_type, canonical_signature, name, timestamp)"
                                " VALUES (?, ?, ?, ?, ?)", batch)
        self._conn.commit()

    def get_symbols(self, canonical_signature: Optional[str] = None, author: Optional[str] = None) -> Iterable[Symbol]:
        with closing(self._conn.cursor()) as cur:
            if canonical_signature is None and author is None:
                cur.execute("SELECT *, max(timestamp) FROM symbols GROUP BY canonical_signature, author;")
            elif canonical_signature is not None and author is None:
                cur.execute("SELECT *, max(timestamp) FROM symbols WHERE canonical_signature = ? GROUP BY author;",
                            [canonical_signature])
            elif canonical_signature is None and author is not None:
                cur.execute("SELECT *, max(timestamp) FROM symbols WHERE author = ? GROUP BY canonical_signature;",
                            [author])
            elif canonical_signature is not None and author is not None:
                cur.execute("SELECT *, max(timestamp) FROM symbols WHERE canonical_signature = ? AND author = ?",
                            [canonical_signature, author])

            for row in cur:
                if all(x is None for x in row):
                    continue

                author, symbol_type, canonical_signature, name, timestamp, _ = row
                yield Symbol(symbol_type, canonical_signature, name, timestamp=timestamp, author=author)

    def get_latest_symbols(self, canonical_signature: Optional[str] = None) -> Iterable[Symbol]:
        with closing(self._conn.cursor()) as cur:
            if canonical_signature is None:
                cur.execute("SELECT author, symbol_type, canonical_signature, name, timestamp , max(timestamp) "
                            "FROM symbols GROUP BY canonical_signature;")
            elif canonical_signature is not None:
                cur.execute("SELECT author, symbol_type, canonical_signature, name, timestamp, max(timestamp) FROM symbols WHERE canonical_signature = ?;",
                            [canonical_signature])

            for row in cur:
                author, symbol_type, canonical_signature, name, timestamp, _ = row
                yield Symbol(symbol_type, canonical_signature, name, timestamp=timestamp, author=author)

    def close(self):
        self._conn.close()
