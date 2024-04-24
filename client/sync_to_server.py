import time
import socket
import itertools

from common.commands import UpstreamSymbols
from .rename_engine import RenameEngine
from .utils import project_id, encode_symbol, send_packet, method_is_override

from java.lang import Runnable
from com.pnfsoftware.jeb.core.units.code.android.dex import IDexMethod
from com.pnfsoftware.jeb.core.units.code.android import IDexUnit
from com.pnfsoftware.jeb.core import IRuntimeProject


class SyncToServer(Runnable):
    def __init__(self, ctx, sock, rename_engine, callback):
        # type: (IRuntimeProject, socket.socket, RenameEngine, callable) -> None
        super(SyncToServer, self).__init__()
        self._ctx = ctx
        self._socket = sock
        self._callback = callback
        self._rename_engine = rename_engine

    def run(self):
        # type: () -> None
        for dex_unit in self._ctx.mainProject.findUnits(IDexUnit):
            symbols = []
            for item in itertools.chain(dex_unit.fields, dex_unit.methods, dex_unit.classes):
                if (not item.renamed) or (not self._rename_engine.is_original_symbol(item)):
                    continue

                if isinstance(item, IDexMethod) and method_is_override(item):
                    continue

                symbol = encode_symbol(item)
                symbol.timestamp = int(time.time())
                symbols.append(symbol)

            if symbols:
                command = UpstreamSymbols(project_id(dex_unit), symbols, loggable=False)
                # send_packet(self._socket, command.encode())

        self._callback()
