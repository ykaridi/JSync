import itertools

from com.pnfsoftware.jeb.core.units.code.android.dex import IDexItem, IDexMethod
from com.pnfsoftware.jeb.core.units.code.android import IDexUnit
from com.pnfsoftware.jeb.core import IRuntimeProject

from common.symbol import Symbol
from client_base.connection import ConnectionABC
from java_common.scan_updated_symbols import JavaScanUpdatedSymbols
from .utils import project_id, encode_symbol, method_is_override, is_internal
from .rename_engine import JEBRenameEngine


class JEBScanUpdatedSymbols(JavaScanUpdatedSymbols):
    def __init__(self, ctx, connection, rename_engine, projects, callback):
        # type: (IRuntimeProject, ConnectionABC, JEBRenameEngine, list[str] callable) -> None
        JavaScanUpdatedSymbols.__init__(self, connection, rename_engine, projects)

        self._ctx = ctx
        self._callback = callback

    def is_symbol_reverted(self, project, symbol):
        # type: (str, Symbol) -> bool
        item = self._rename_engine.get_dex_item(project, symbol)  # IDexItem
        return item.getName(False) == item.getName(True)

    def run(self):
        # type: () -> None
        print("[JSync] Scanning for updated symbols")

        self.handle_reverted_symbols()

        for dex_unit in self._ctx.mainProject.findUnits(IDexUnit):
            project_symbols = {}
            for item in itertools.chain(dex_unit.fields, dex_unit.methods, dex_unit.classes):
                if not is_internal(item):
                    continue

                if not item.renamed:
                    continue

                project = project_id(item)
                symbol = encode_symbol(item)

                if isinstance(item, IDexMethod) and method_is_override(item):
                    continue

                if self._rename_engine.is_symbol_rename_known(project, symbol, item.renamed):
                    continue

                project_symbols.setdefault(project, []).append(symbol)

            for project, symbols in project_symbols.items():
                self.report_renamed_symbols(project, symbols)

        print("[JSync] Finished scanning for updated symbols")

        self._callback()
