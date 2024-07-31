from java.net import URL, URLClassLoader
from java.lang import Class, ClassLoader
from java.sql import DriverManager, PreparedStatement
from java.util import Properties
from java.sql import Types as SqlTypes

import os
import contextlib
from functools import partial

from client_base.config import JSYNC_ROOT
from client_base.client_symbol_store import ClientSymbolStoreABC
from common.sqlite_adapter import SqliteAdapterABC


jdbc_jar = URL("file:%s" % os.path.join(JSYNC_ROOT, 'jars', 'sqlite-jdbc.jar'))
slf4j_jar = URL("file:%s" % os.path.join(JSYNC_ROOT, 'jars', 'slf4j.jar'))


@contextlib.contextmanager
def auto_commit(connection, value):
    ac = connection.autoCommit
    connection.setAutoCommit(value)
    yield
    connection.setAutoCommit(ac)


class SqliteAdapter(SqliteAdapterABC):
    def __init__(self, path):
        # type: (str) -> None
        cl = URLClassLoader([jdbc_jar, slf4j_jar], ClassLoader.getSystemClassLoader())

        sqlite_driver = cl.loadClass('org.sqlite.JDBC')
        driver = sqlite_driver()

        self._conn = driver.connect('jdbc:sqlite:%s' % path, Properties())

    @staticmethod
    def push_arguments(prepared_statement, *arguments):
        # type: (PreparedStatement, *object) -> None
        funcs = {
            str: prepared_statement.setString,
            unicode: prepared_statement.setString,
            int: prepared_statement.setInt,
            float: prepared_statement.setFloat,
        }

        for i, arg in enumerate(arguments):
            if type(arg) not in funcs:
                raise TypeError('Unhandled type %s for Java SQLite parameter' % type(arg))

            funcs[type(arg)](i + 1, arg)

    def execute(self, statement, *arguments):
        # type: (str, *object) -> None
        stmt = self._conn.prepareStatement(statement)
        self.push_arguments(stmt, *arguments)
        stmt.execute()

    def execute_update(self, statement, *arguments):
        # type: (str, *object) -> int
        stmt = self._conn.prepareStatement(statement)
        self.push_arguments(stmt, *arguments)
        return stmt.executeUpdate()

    def execute_query(self, statement, *arguments):
        # type: (str, *object) -> list
        stmt = self._conn.prepareStatement(statement)
        self.push_arguments(stmt, *arguments)
        results = stmt.executeQuery()

        metadata = results.metaData
        funcs = {
            SqlTypes.VARCHAR: results.getString,
            SqlTypes.INTEGER: results.getInt,
            SqlTypes.FLOAT: results.getFloat,
            SqlTypes.NUMERIC: results.getFloat,
        }
        columns = [partial(funcs[metadata.getColumnType(i + 1)], i + 1) for i in range(metadata.columnCount)]

        while results.next():
            yield [column() for column in columns]

    def executemany(self, statement, rows):
        # type: (str, list) -> None
        with auto_commit(self._conn, False):
            stmt = self._conn.prepareStatement(statement)
            for row in rows:
                self.push_arguments(stmt, *row)
                stmt.addBatch()
            stmt.executeBatch()
            self._conn.commit()

    def close(self):
        # type: () -> None
        self._conn.close()


class JDBCClientSymbolStore(ClientSymbolStoreABC):
    def connect(self, path):
        # type: (str) -> SqliteAdapter
        return SqliteAdapter(path)
