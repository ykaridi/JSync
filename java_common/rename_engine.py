import os
from abc import ABCMeta

from client_base.rename_engine import RenameEngineABC
from .jdbc_symbol_store import JDBCClientSymbolStore


class JavaRenameEngineABC(RenameEngineABC):
    __metaclass__ = ABCMeta

    def __init__(self, self_author, root):
        # type: (str, str) -> None
        RenameEngineABC.__init__(self, self_author)

        self._root = root
        if not os.path.exists(self._root):
            os.makedirs(self._root)

    def get_client_symbol_store(self, project):
        # type: (str) -> JDBCClientSymbolStore
        return JDBCClientSymbolStore(os.path.join(self._root, "%s.db" % project))
