from jadx.api.plugins import JadxPluginContext
from jadx.api.plugins.events import JadxEvents
from jadx.core.dex.nodes import MethodNode
from org.slf4j import Logger

from client_base.connection import ConnectionABC
from client_base.rename_listener import RenameListenerABC
from java_common.wrappers import JavaConsumer
from .utils import encode_symbol, project_id, get_base_methods


class JADXRenameListener(RenameListenerABC):
    def __init__(self, context, logger, connection):
        # type: ('JSync', JadxPluginContext, Logger, ConnectionABC) -> None
        super(JADXRenameListener, self).__init__(connection)
        self._context = context
        self._logger = logger
        self._active = False
        self._activated = False

    def _on_jadx_rename(self, rename):
        if self._active:
            _node = rename.node
            if isinstance(_node, MethodNode):
                nodes = get_base_methods(_node)
            else:
                nodes = [_node]

            for node in nodes:
                self.on_rename(project_id(node), encode_symbol(node))

    def start(self):
        self._active = True
        if not self._activated:
            self._context.events().addListener(JadxEvents.NODE_RENAMED_BY_USER,
                                               JavaConsumer(self._on_jadx_rename))
            self._activated = True

    def stop(self):
        self._active = False
