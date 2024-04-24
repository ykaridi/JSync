import time

from java.net import Socket
from com.pnfsoftware.jeb.core.units.code.android.dex import IDexMethod, IDexClass, IDexField
from com.pnfsoftware.jeb.util.events import IEventListener
from com.pnfsoftware.jeb.core.units import UnitChangeEventData
from com.pnfsoftware.jeb.core.events import JebEvent, J

from common.commands import UpstreamSymbols
from .utils import project_id, method_is_override, encode_symbol, send_packet
from .rename_engine import RenameEngine


class RenameListener(IEventListener):
    def __init__(self, jebsync, socket, rename_engine):
        # type: ('JEBSync', Socket, RenameEngine) -> None
        self._jebsync = jebsync
        self._socket = socket
        self._is_jebsync = True
        self._minimal_classes = {}  # type: dict[int, int]
        self._rename_engine = rename_engine

    def onEvent(self, e):
        # type: (JebEvent) -> None
        if isinstance(e, JebEvent) and e.type == J.UnitChange and e.data is not None:
            if e.data.type == UnitChangeEventData.NameUpdate:
                target = e.data.target

                if not isinstance(target, (IDexField, IDexMethod, IDexClass)):
                    return

                if self._rename_engine.locked:
                    # TODO: Is this the right way to do it?
                    #  We want to update metadata even in renames caused by root rename...
                    self._rename_engine.update_item_metadata(target)
                    return

                if isinstance(target, IDexMethod) and method_is_override(target):
                    return

                project = project_id(target.dex)
                symbol = encode_symbol(target)
                symbol.timestamp = int(time.time())
                command = UpstreamSymbols(project, [symbol], loggable=True)
                send_packet(self._socket, command.encode())
