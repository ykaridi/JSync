import itertools

from com.pnfsoftware.jeb.core.units.code.android.dex import IDexMethod
from com.pnfsoftware.jeb.core.units.code.android import IDexUnit
from com.pnfsoftware.jeb.core import IRuntimeProject


from client_base.connection import ConnectionABC
from client_base.rename_engine import RenameEngineABC
from java_common.sync_to_server import JavaSyncToServer
from .utils import project_id, encode_symbol, method_is_override, is_internal


class JEBSyncToServer(JavaSyncToServer):
    def __init__(self, ctx, connection, rename_engine, callback):
        # type: (IRuntimeProject, ConnectionABC, RenameEngineABC, callable) -> None
        super(JEBSyncToServer, self).__init__(connection)

        self._ctx = ctx
        self._rename_engine = rename_engine
        self._callback = callback

    def run(self):
        # type: () -> None
        for dex_unit in self._ctx.mainProject.findUnits(IDexUnit):
            project_symbols = {}
            for item in itertools.chain(dex_unit.fields, dex_unit.methods, dex_unit.classes):
                if not is_internal(item):
                    continue

                if not item.renamed:
                    # TODO: This actually is not good enough...
                    #       If user deleted symbol while JSync was off, we don't update the server!
                    continue

                project = project_id(item)
                symbol = encode_symbol(item)

                if self._rename_engine.is_symbol_synced(project, symbol, item.renamed):
                    continue

                if isinstance(item, IDexMethod) and method_is_override(item):
                    continue

                project_symbols.setdefault(project, []).append(symbol)

            for project, symbols in project_symbols.items():
                self.upload_symbols(project, symbols)

        self._callback()
