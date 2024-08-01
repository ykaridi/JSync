from abc import ABCMeta

from java.lang import Runnable

from client_base.connection import ConnectionABC
from client_base.scan_updated_symbols import ScanUpdatedSymbols
from client_base.rename_engine import RenameEngineABC


class JavaScanUpdatedSymbols(Runnable, ScanUpdatedSymbols):
    __metaclass__ = ABCMeta

    def __init__(self, connection, rename_engine, projects):
        # type: (ConnectionABC, RenameEngineABC, list[str]) -> None
        Runnable.__init__(self)
        ScanUpdatedSymbols.__init__(self, connection, rename_engine, projects)
