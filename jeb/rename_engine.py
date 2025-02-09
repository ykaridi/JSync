import os
from threading import Lock

from com.pnfsoftware.jeb.core.units.code.android import IDexUnit
from com.pnfsoftware.jeb.core.units.code.android.dex import IDexItem
from com.pnfsoftware.jeb.client.api import IClientContext

from common.symbol import SYMBOL_TYPE_FIELD, SYMBOL_TYPE_METHOD, SYMBOL_TYPE_CLASS
from common.symbol import Symbol
from java_common.rename_engine import JavaRenameEngineABC
from .utils import project_id, encode_symbol
from .config import JSYNC_JEB_ROOT


METADATA_GROUP_NAME = "jsync <%s>"


class JEBRenameEngine(JavaRenameEngineABC):
    def __init__(self, context, self_author):
        # type: (IClientContext, str) -> None
        JavaRenameEngineABC.__init__(self, self_author, os.path.join(JSYNC_JEB_ROOT, 'rename_records'))
        self._lock = Lock()
        self._jeb_project = context.mainProject
        self._projects = None

    def get_dex_item(self, project, symbol):
        # type: (str, Symbol) -> IDexItem
        dex_file = self.projects[project]
        unit = dex_file.ownerUnit

        if symbol.symbol_type == SYMBOL_TYPE_FIELD:
            return unit.getField(symbol.canonical_signature)
        elif symbol.symbol_type == SYMBOL_TYPE_METHOD:
            return unit.getMethod(symbol.canonical_signature)
        elif symbol.symbol_type == SYMBOL_TYPE_CLASS:
            return unit.getClass(symbol.canonical_signature)
        else:
            raise ValueError("Unknown symbol type")

    def get_name(self, project, symbol):
        # type: (str, Symbol) -> str
        item = self.get_dex_item(project, symbol)
        return item.getName(True) or item.getName(False)

    def get_original_name(self, project, symbol):
        # type: (str, Symbol) -> str
        item = self.get_dex_item(project, symbol)
        return item.getName(False)

    @property
    def projects(self):
        # type: () -> dict[str, IDexUnit]
        if self._projects is None:
            self._projects = {}
            for unit in self._jeb_project.findUnits(IDexUnit):
                for dex_file in unit.dexFiles:
                    self._projects[project_id(dex_file)] = dex_file

        return self._projects

    @property
    def locked(self):
        # type: () -> bool
        return self._lock.locked()

    def _enqueue_rename(self, project, symbol):
        # type: (str, Symbol) -> bool
        item = self.get_dex_item(project, symbol)
        if item is None or project_id(item) != project:
            return False

        with self._lock:
            if item.getName(True) != symbol.name:
                item.setName(symbol.name)

        return True
