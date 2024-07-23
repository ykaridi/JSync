import os
from abc import ABCMeta, abstractmethod
from threading import Lock

from .rename_store import load_renames, dump_renames
from common.symbol import Symbol


class RenameEngineABC(object):
    __metaclass__ = ABCMeta

    def __init__(self, root):
        # type: (str) -> None
        self._root = root
        self._rename_records = {}  # type: dict[str, dict[str, str]]
        self._dirty_projects = set()  # type: set[str]
        self._records_lock = Lock()

        if not os.path.exists(self._root):
            os.makedirs(self._root)

    @abstractmethod
    def get_name(self, project, symbol):
        # type: (str, Symbol) -> str
        raise NotImplemented

    def _records_path(self, project):
        # type: (str) -> str
        return os.path.join(self._root, "%s" % project)

    def _records_for(self, project):
        # type: (str) -> dict[str, str]
        if project not in self._rename_records:
            path = self._records_path(project)
            if os.path.exists(path):
                self._rename_records[project] = load_renames(path)
                print(self._rename_records[project])
            else:
                self._rename_records[project] = {}

        return self._rename_records[project]

    def is_symbol_synced(self, project, symbol):
        # type: (str, Symbol) -> bool
        saved_name = self._records_for(project).get(symbol.canonical_signature, None)
        if saved_name is None:
            return False

        return saved_name == symbol.name

    def record_rename(self, project, symbol):
        # type: (str, Symbol) -> None
        with self._records_lock:
            print("Renamed: %s" % symbol.canonical_signature)
            self._records_for(project)[symbol.canonical_signature] = symbol.name
            self._dirty_projects.add(project)

    def dump_rename_records(self):
        with self._records_lock:
            for project in self._dirty_projects:
                path = self._records_path(project)
                dump_renames(path, self._records_for(project))

            self._dirty_projects = set()

    @abstractmethod
    def _enqueue_rename(self, project, symbol):
        # type: (str, Symbol) -> bool
        raise NotImplemented

    def enqueue_rename(self, project, symbol):
        symbol = symbol.clone(name=symbol.name.replace('.', '$'))
        if self._enqueue_rename(project, symbol):
            self.record_rename(project, symbol)
