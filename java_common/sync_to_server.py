from abc import ABCMeta

from java.lang import Runnable

from client_base.connection import ConnectionABC
from client_base.sync_to_server import SyncToServerABC


class JavaSyncToServer(Runnable, SyncToServerABC):
    __metaclass__ = ABCMeta

    def __init__(self, connection):
        # type: (ConnectionABC) -> None
        Runnable.__init__(self)
        SyncToServerABC.__init__(self, connection)
