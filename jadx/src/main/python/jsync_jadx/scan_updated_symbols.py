from jadx.api.data import IJavaNodeRef
from jadx.api.plugins import JadxPluginContext
from org.slf4j import Logger

from common.symbol import Symbol
from client_base.connection import ConnectionABC
from client_base.rename_engine import RenameEngineABC
from java_common.scan_updated_symbols import JavaScanUpdatedSymbols
from common.symbol import SYMBOL_TYPE_CLASS, SYMBOL_TYPE_METHOD, SYMBOL_TYPE_FIELD

from .utils import encode_symbol, project_id, get_internal_base_methods, get_node_by_class_type_and_short_id


NODE_REF_TYPE_TO_SYMBOL_TYPE = {
    IJavaNodeRef.RefType.CLASS: SYMBOL_TYPE_CLASS,
    IJavaNodeRef.RefType.METHOD: SYMBOL_TYPE_METHOD,
    IJavaNodeRef.RefType.FIELD: SYMBOL_TYPE_FIELD
}


class JADXScanUpdatedSymbols(JavaScanUpdatedSymbols):
    def __init__(self, context, logger, connection, rename_engine, projects, callback):
        # type: (JadxPluginContext, Logger, ConnectionABC, RenameEngineABC, list[str] callable) -> None
        JavaScanUpdatedSymbols.__init__(self, connection, rename_engine, projects)
        self._logger = logger
        self._context = context
        self._callback = callback
        self._renamed_symbols = None  # dict[str, dict[str, Symbol]]

    def is_symbol_reverted(self, project, symbol):
        # type: (str, Symbol) -> bool
        if symbol.canonical_signature in self.renamed_symbols.setdefault(project, {}):
            return False

        return not self._rename_engine.is_symbol_rename_known(project, symbol, True)

    @property
    def renamed_symbols(self):
        # type: () -> dict[str, set[str]]
        if self._renamed_symbols is None:
            self._renamed_symbols = {}
            code_data = self._context.args.codeData
            renames = code_data.renames

            for rename in renames:
                ref = rename.nodeRef

                node_type = NODE_REF_TYPE_TO_SYMBOL_TYPE.get(ref.type, None)
                if node_type is None:
                    continue

                _node = get_node_by_class_type_and_short_id(self._context, ref.declaringClass, node_type, ref.shortId)
                if node_type == SYMBOL_TYPE_METHOD:
                    nodes = get_internal_base_methods(_node)
                else:
                    nodes = [_node]

                for node in nodes:
                    project = project_id(node)
                    symbol = encode_symbol(node)

                    self._renamed_symbols.setdefault(project, {})[symbol.canonical_signature] = symbol

        return self._renamed_symbols

    def run(self):
        # type: () -> None
        self._logger.error("[JSync] Beginning updated symbol scan")
        
        self.handle_reverted_symbols()

        updated_symbols = {}
        for project, symbols in self.renamed_symbols.items():
            for symbol in symbols.values():
                if not self._rename_engine.is_symbol_rename_known(project, symbol, True):
                    updated_symbols.setdefault(project, []).append(symbol)

        for project, project_symbols in updated_symbols.items():
            self.report_renamed_symbols(project, project_symbols)

        self._logger.error("[JSync] Finished updated symbol scan")
        self._callback()
