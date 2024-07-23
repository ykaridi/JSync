from jadx.api.data import IJavaNodeRef
from jadx.api.plugins import JadxPluginContext
from org.slf4j import Logger

from client_base.connection import ConnectionABC
from client_base.rename_engine import RenameEngineABC
from java_common.sync_to_server import JavaSyncToServer
from common.symbol import SYMBOL_TYPE_CLASS, SYMBOL_TYPE_METHOD, SYMBOL_TYPE_FIELD

from .utils import encode_symbol, project_id, get_base_methods, get_node_by_class_type_and_short_id


QUICK = False

NODE_REF_TYPE_TO_SYMBOL_TYPE = {
    IJavaNodeRef.RefType.CLASS: SYMBOL_TYPE_CLASS,
    IJavaNodeRef.RefType.METHOD: SYMBOL_TYPE_METHOD,
    IJavaNodeRef.RefType.FIELD: SYMBOL_TYPE_FIELD
}


class JADXSyncToServer(JavaSyncToServer):
    def __init__(self, context, logger, connection, rename_engine, callback):
        # type: (JadxPluginContext, Logger, ConnectionABC, RenameEngineABC, callable) -> None
        super(JADXSyncToServer, self).__init__(connection)
        self._context = context
        self._logger = logger
        self._rename_engine = rename_engine
        self._callback = callback

    def run(self):
        # type: () -> None
        self._logger.error("[JSync] Beginning Sync To Server")
        code_data = self._context.args.codeData
        renames = code_data.renames

        symbols = {}
        for rename in renames:
            ref = rename.nodeRef

            node_type = NODE_REF_TYPE_TO_SYMBOL_TYPE.get(ref.type, None)
            if node_type is None:
                continue

            node = get_node_by_class_type_and_short_id(self._context, ref.declaringClass, node_type, ref.shortId)
            if node_type == SYMBOL_TYPE_METHOD:
                nodes = get_base_methods(self._context, node)
            else:
                nodes = [node]

            for node in nodes:
                project = project_id(node)
                symbol = encode_symbol(node)

                if QUICK or not self._rename_engine.is_symbol_synced(project, symbol):
                    symbols.setdefault(project, []).append(symbol)

        for project, project_symbols in symbols.items():
            self.upload_symbols(project, project_symbols)

        self._logger.error("[JSync] Finished Sync To Server")
        self._callback()
