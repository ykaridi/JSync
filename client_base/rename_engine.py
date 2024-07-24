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
        raise NotImplementedError

    def _records_path(self, project):
        # type: (str) -> str
        return os.path.join(self._root, "%s" % project)

    def _records_for(self, project):
        # type: (str) -> dict[str, str]
        if project not in self._rename_records:
            path = self._records_path(project)
            if os.path.exists(path):
                self._rename_records[project] = load_renames(path)
            else:
                self._rename_records[project] = {}

        return self._rename_records[project]

    def get_symbol_latest_name(self, project, symbol):
        # type: (str, Symbol) -> str
        return self._records_for(project).get(symbol.canonical_signature, None)

    def is_symbol_synced(self, project, symbol):
        # type: (str, Symbol) -> bool
        return self.get_symbol_latest_name(project, symbol) == symbol.name

    def record_rename(self, project, symbol):
        # type: (str, Symbol) -> None
        with self._records_lock:
            self._records_for(project)[symbol.canonical_signature] = symbol.name
            self._dirty_projects.add(project)

    def dump_rename_records(self):
        # type: () -> None
        with self._records_lock:
            for project in self._dirty_projects:
                path = self._records_path(project)
                dump_renames(path, self._records_for(project))

            self._dirty_projects = set()

    @abstractmethod
    def _enqueue_rename(self, project, symbol):
        # type: (str, Symbol) -> bool
        raise NotImplementedError

    def enqueue_rename(self, project, symbol):
        # type: (str, Symbol) -> None
        old_name = self.get_symbol_latest_name(project, symbol)
        self.record_rename(project, symbol)
        if not self._enqueue_rename(project, symbol):
            self.record_rename(project, symbol.clone(name=old_name))
