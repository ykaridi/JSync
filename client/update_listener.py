import socket

from common.commands import Command, DownstreamSymbols
from .rename_engine import RenameEngine
from .utils import project_id, recv_packet

from java.lang import Runnable
from com.pnfsoftware.jeb.core.units.code.android import IDexUnit
from com.pnfsoftware.jeb.core import IRuntimeProject


class UpdateListener(Runnable):
    def __init__(self, ctx, sock, rename_engine):
        # type: (IRuntimeProject, socket.socket, RenameEngine) -> None
        super(UpdateListener, self).__init__()
        self._socket = sock
        self._rename_engine = rename_engine
        self._dexes = {project_id(unit): unit for unit in ctx.mainProject.findUnits(IDexUnit)}

    def run(self):
        # type: () -> None
        while True:
            try:
                packet = recv_packet(self._socket)
                if packet is None:
                    break

                command = Command.decode(packet)
                if isinstance(command, DownstreamSymbols):
                    if command.project in self._dexes:
                        dex_unit = self._dexes[command.project]
                        for symbol in command.symbols:
                            self._rename_engine.enqueue_rename(dex_unit, symbol)
            except:  # noqa
                return
