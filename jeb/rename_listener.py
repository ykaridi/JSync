from com.pnfsoftware.jeb.core.units.code.android import IDexUnit
from com.pnfsoftware.jeb.core.units.code.android.dex import IDexMethod, IDexClass, IDexField
from com.pnfsoftware.jeb.util.events import IEventListener
from com.pnfsoftware.jeb.core.units import UnitChangeEventData
from com.pnfsoftware.jeb.core.events import JebEvent, J
from com.pnfsoftware.jeb.client.api import IClientContext

from client_base.connection import ConnectionABC
from client_base.rename_listener import RenameListenerABC
from .utils import project_id, method_is_override, encode_symbol, is_internal
from .rename_engine import JEBRenameEngine


class JEBRenameListener(IEventListener, RenameListenerABC):
    def __init__(self, jsync, context, connection, rename_engine):
        # type: ('JSync', IClientContext, ConnectionABC, JEBRenameEngine) -> None
        IEventListener.__init__(self)
        RenameListenerABC.__init__(self, connection, rename_engine)

        self._jsync = jsync
        self._is_jsync = True
        self._jeb_project = context.mainProject
        self._minimal_classes = {}  # type: dict[int, int]
        self._rename_engine = rename_engine  # type: JEBRenameEngine

    def onEvent(self, e):
        # type: (JebEvent) -> None
        if isinstance(e, JebEvent) and e.type == J.UnitChange and e.data is not None:
            if e.data.type == UnitChangeEventData.NameUpdate:
                target = e.data.target

                if not (isinstance(target, (IDexField, IDexMethod, IDexClass)) and is_internal(target)):
                    return

                project = project_id(target)
                symbol = encode_symbol(target)

                if isinstance(target, IDexMethod) and method_is_override(target):
                    return

                self.on_rename(project, symbol)

    def start(self):
        # type: () -> None
        for dex in self._jeb_project.findUnits(IDexUnit):
            dex.addListener(self)
