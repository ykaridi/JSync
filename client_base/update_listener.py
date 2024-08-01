from common.commands import Command, DownstreamSymbols, FullSyncComplete
from .connection import ConnectionABC
from .rename_engine import RenameEngineABC


class UpdateListener(object):
    def __init__(self, connection, projects, rename_engine):
        # type: (ConnectionABC, list[str], RenameEngineABC) -> None
        self._connection = connection
        self._rename_engine = rename_engine
        self._projects = projects

    def handle_packet(self, packet):
        # type: (bytes) -> None
        command = Command.decode(packet)
        if isinstance(command, DownstreamSymbols):
            if command.project in self._projects:
                self._rename_engine.record_symbols(command.project, command.symbols)
                self._rename_engine.flush_all_symbols()
        elif isinstance(command, FullSyncComplete):
            if command.project in self._projects:
                self._rename_engine.set_metadata_property(command.project, 'last_sync', command.timestamp)

    def receive_packet(self):
        # type: () -> bytes
        return self._connection.recv_packet()
