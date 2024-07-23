from java.lang import Runnable
from java.lang import Thread


from client_base.connection import ConnectionABC, ConnectionError
from client_base.update_listener import UpdateListener
from client_base.rename_engine import RenameEngineABC


class JavaUpdateListener(Runnable, UpdateListener):
    def __init__(self, connection, projects, rename_engine):
        # type: (ConnectionABC, list[str], RenameEngineABC) -> None
        Runnable.__init__(self)
        UpdateListener.__init__(self, connection, projects, rename_engine)

    def run(self):
        # type: () -> None
        while not Thread.interrupted():
            try:
                packet = self.receive_packet()
            except ConnectionError:
                continue

            self.handle_packet(packet)
