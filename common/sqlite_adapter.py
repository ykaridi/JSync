from abc import ABCMeta, abstractmethod


class SqliteAdapterABC(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def execute(self, statement, *arguments):
        # type: (str, *object) -> None
        raise NotImplementedError

    def execute_update(self, statement, *arguments):
        # type: (str, *object) -> int
        raise NotImplementedError

    @abstractmethod
    def execute_query(self, statement, *arguments):
        # type: (str, *object) -> list
        raise NotImplementedError

    @abstractmethod
    def executemany(self, statement, rows):
        # type: (str, list) -> None
        raise NotImplementedError

    @abstractmethod
    def close(self):
        # type: () -> None
        raise NotImplementedError
