from jadx.api.plugins import JadxPluginContext
from jadx.api.plugins.events import JadxEvents
from jadx.core.dex.nodes import MethodNode
from jadx.api.plugins.events.types import NodeRenamedByUser
from org.slf4j import Logger

from client_base.connection import ConnectionABC
from client_base.rename_listener import RenameListenerABC
from java_common.wrappers import JavaConsumer
from .utils import encode_symbol, project_id, get_internal_base_methods
from .rename_engine import JADXRenameEngine


class JADXRenameListener(RenameListenerABC):
    def __init__(self, context, logger, connection, rename_engine):
        # type: ('JSync', JadxPluginContext, Logger, ConnectionABC, JADXRenameEngine) -> None
        super(JADXRenameListener, self).__init__(connection, rename_engine)
        self._context = context
        self._logger = logger
        self._active = False
        self._activated = False

    def _on_jadx_rename(self, rename):
        # type: (NodeRenamedByUser) -> None
        if self._active:
            _node = rename.node
            if isinstance(_node, MethodNode):
                nodes = get_internal_base_methods(_node)
            else:
                nodes = [_node]

            for node in nodes:
                self.on_rename(project_id(node), encode_symbol(node, new_name=rename.newName))

    def start(self):
        # type: () -> None
        self._active = True
        if not self._activated:
            self._context.events().addListener(JadxEvents.NODE_RENAMED_BY_USER,
                                               JavaConsumer(self._on_jadx_rename))
            self._activated = True

    def stop(self):
        # type: () -> None
        self._active = False
