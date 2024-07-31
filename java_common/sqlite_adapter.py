import base64

from java.net import URL, URLClassLoader
from java.lang import Class, ClassLoader
from java.sql import DriverManager, PreparedStatement
from java.util import Properties
from java.sql import Types as SqlTypes

import os
import contextlib
from functools import partial

from client_base.config import JSYNC_ROOT
from java_common.connection import JavaConnection
from common.sqlite_adapter import SqliteAdapterABC
from common.commands import Command, ResourceRequest, ResourceResponse


SQLITE_JDBC_PATH = os.path.join(JSYNC_ROOT, 'resources', 'sqlite-jdbc.jar')
SLF4J_PATH = os.path.join(JSYNC_ROOT, 'resources', 'slf4j.jar')

SQLITE_JDBC_JAR = URL("file:%s" % SQLITE_JDBC_PATH)
SLF4J_JAR = URL("file:%s" % SLF4J_PATH)


@contextlib.contextmanager
def auto_commit(connection, value):
    ac = connection.autoCommit
    connection.setAutoCommit(value)
    yield
    connection.setAutoCommit(ac)


class SqliteAdapter(SqliteAdapterABC):
    def __init__(self, path):
        # type: (str) -> None
        self.ensure_jars(None)
        cl = URLClassLoader([SQLITE_JDBC_JAR, SLF4J_JAR], ClassLoader.getSystemClassLoader())

        sqlite_driver = cl.loadClass('org.sqlite.JDBC')
        driver = sqlite_driver()

        self._conn = driver.connect('jdbc:sqlite:%s' % path, Properties())

    @staticmethod
    def ensure_jars(connection):
        # type: (JavaConnection) -> None
        targets = [SQLITE_JDBC_PATH, SLF4J_PATH]
        if all(os.path.exists(path) for path in targets):
            return

        resource_dir = os.path.join(JSYNC_ROOT, 'resources')
        if not os.path.exists(resource_dir):
            os.makedirs(resource_dir)

        connection = JavaConnection(connection.host, connection.port, connection.name)

        for path in targets:
            if not os.path.exists(path):
                if connection is None:
                    raise EnvironmentError("Couldn't find JARs required for SQLite Driver")

                base_name = os.path.basename(path)
                print("[JSync] Downloading %s" % base_name)

                connection.send_packet(ResourceRequest(base_name).encode())
                command = Command.decode(connection.recv_packet())
                if not isinstance(command, ResourceResponse) or command.name != base_name:
                    raise TypeError("Unexpected response for ResourceRequest")

                if command.content is None:
                    raise EnvironmentError("Couldn't find JARs required for SQLite Driver")

                content = base64.b64decode(command.content)
                with open(path, 'wb') as f:
                    f.write(content)

                print("[JSync] Download of %s is complete!" % base_name)

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
