from common.commands import Command, DownstreamSymbols
from .connection import ConnectionABC
from .rename_engine import RenameEngineABC


class UpdateListener(object):
    def __init__(self, connection, projects, rename_engine):
        # type: (ConnectionABC, list[str], RenameEngineABC) -> None
        super(UpdateListener, self).__init__()
        self._connection = connection
        self._rename_engine = rename_engine
        self._projects = projects

    def handle_packet(self, packet):
        # type: (bytes) -> None
        command = Command.decode(packet)
        if isinstance(command, DownstreamSymbols):
            if command.project in self._projects:
                for symbol in command.symbols:
                    self._rename_engine.enqueue_rename(command.project, symbol)

    def receive_packet(self):
        # type: () -> bytes
        return self._connection.recv_packet()
