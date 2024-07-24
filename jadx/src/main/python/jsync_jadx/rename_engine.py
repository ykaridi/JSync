import os
from threading import Lock

from java.lang import Thread
from java.lang import Runnable

from jadx.api.plugins import JadxPluginContext

from common.symbol import Symbol
from client_base.rename_engine import RenameEngineABC
from .utils import project_id, get_node
from .config import DATA_ROOT


class JADXRenameEngine(RenameEngineABC):
    def __init__(self, context):
        # type: (JadxPluginContext) -> None
        super(JADXRenameEngine, self).__init__(os.path.join(DATA_ROOT, 'rename_records'))
        self._context = context
        self.rename_future = None  # type: Thread
        self.rename_future_lock = Lock()

    def get_name(self, project, symbol):
        # type: (str, Symbol) -> str
        node = get_node(self._context, project, symbol)
        return node.alias

    def _enqueue_rename(self, project, symbol):
        # type: (str, Symbol) -> bool
        node = get_node(self._context, project, symbol)
        if node is None or project_id(node) != project:
            return False

        if node.alias == symbol.name:
            return False

        node.rename(symbol.name)

        with self.rename_future_lock:
            if self.rename_future is None:
                self.rename_future = ApplyRename(self._context, self)
                Thread(self.rename_future).start()

            self.rename_future.nodes.append(node)

        return True


class ApplyRename(Runnable):
    def __init__(self, context, rename_engine):
        # type: (JadxPluginContext, JADXRenameEngine) -> None
        super(ApplyRename, self).__init__()
        self._context = context
        self._rename_engine = rename_engine
        self.nodes = []

    def run(self):
        # type: () -> None
        with self._rename_engine.rename_future_lock:
            self._rename_engine.rename_future = None

        gui_context = self._context.guiContext
        if gui_context:
            gui_context.reloadAllTabs()
