import sqlite3
from contextlib import closing
from typing import Iterable

from common.symbol_store import SymbolStoreABC
from common.sqlite_adapter import SqliteAdapterABC


class SqliteAdapter(SqliteAdapterABC):
    def __init__(self, path: str):
        self._conn = sqlite3.connect(path)

    def execute(self, statement: str, *arguments) -> None:
        with closing(self._conn.cursor()) as cur:
            cur.execute(statement, arguments)
        self._conn.commit()

    def execute_update(self, statement: str, *arguments) -> int:
        with closing(self._conn.cursor()) as cur:
            cur.execute(statement, arguments)
            row_count = cur.rowcount
        self._conn.commit()
        return row_count

    def execute_query(self, statement, *arguments) -> Iterable:
        with closing(self._conn.cursor()) as cur:
            cur.execute(statement, arguments)
            yield from cur

    def executemany(self, statement: str, rows: list):
        with closing(self._conn.cursor()) as cur:
            cur.executemany(statement, rows)
        self._conn.commit()

    def close(self):
        # type: () -> None
        self._conn.close()


class PySqliteSymbolStore(SymbolStoreABC):
    def connect(self, path: str) -> SqliteAdapter:
        return SqliteAdapter(path)
