import os
import atexit

from java.lang import Thread
from javax.swing import JOptionPane

from jadx.api.plugins import JadxPluginContext
from jadx.api import JadxDecompiler
from jadx.plugins.input.dex import DexLoadResult
from org.slf4j import Logger

from .connection import JADXConnection
from .rename_engine import JADXRenameEngine
from .rename_listener import JADXRenameListener
from .scan_updated_symbols import JADXScanUpdatedSymbols
from .utils import project_id, get_all_projects
from .config import JSYNC_JADX_ROOT
from java_common.update_listener import JavaUpdateListener
from java_common.sqlite_adapter import SqliteAdapter
from java_common.wrappers import ThreadWrapper
from common.commands import FullSyncRequest, Subscribe
from client_base.server_query import query_server
from jsync_cache import INSTANCES


def clean_previous_executions():
    # type: () -> None
    for instance in INSTANCES:
        instance.clean()


class JSync(object):
    def __init__(self, context, logger):
        # type: (JadxPluginContext, Logger) -> None
        self._context = context
        self._logger = logger
        self._connection = None  # type: JADXConnection
        self._rename_listener = None  # type: JADXRenameListener
        self._update_thread = None  # type: Thread
        self._initialization_thread = None  # type: Thread
        self._rename_engine = None

        INSTANCES.append(self)
        atexit.register(self.clean)

    @property
    def active(self):
        # type: () -> bool
        return self._active

    def clean(self):
        # type: () -> None
        if self in INSTANCES:
            INSTANCES.remove(self)

        if self._rename_listener is not None:
            self._rename_listener.stop()
            self._rename_listener = None
        if self._update_thread is not None:
            self._update_thread.interrupt()
            self._update_thread = None
        if self._initialization_thread is not None:
            self._initialization_thread.interrupt()
            self._initialization_thread = None
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def start(self):
        # type: () -> None
        config_path = os.path.join(JSYNC_JADX_ROOT, 'connection')
        host, port, name = query_server(
            lambda default: JOptionPane.showInputDialog(
                "Connection Configuration: <name>@<host>:<port>", default
            ),
            config_path
        )

        if host is None or port is None or name is None:
            self._logger.error("[JSync] No server specified, exiting...")
            return

        self._logger.error("[JSync] Activating...")

        self._connection = JADXConnection(self, self._logger, host, port, name)

        self._initialization_thread = Thread(ThreadWrapper(self.initialize))
        self._initialization_thread.start()

    def initialize(self):
        SqliteAdapter.ensure_jars(self._connection)

        self._rename_engine = JADXRenameEngine(self._context, self._connection.name)
        self._rename_listener = JADXRenameListener(self._context, self._connection, self._rename_engine)
        self._rename_listener.start()

        scan_updated_symbols = Thread(JADXScanUpdatedSymbols(
            self._context, self._logger, self._connection, self._rename_engine,
            get_all_projects(self._context), self.after_sync
        ))
        scan_updated_symbols.start()

        self._initialization_thread = None

    def after_sync(self):
        # type: () -> None
        loaded_inputs_field = JadxDecompiler.getDeclaredField('loadedInputs')
        loaded_inputs_field.setAccessible(True)

        dex_readers_field = DexLoadResult.getDeclaredField('dexReaders')
        dex_readers_field.setAccessible(True)

        projects = []
        for code_loader in loaded_inputs_field.get(self._context.decompiler):
            if not isinstance(code_loader, DexLoadResult):
                continue

            for dex_reader in dex_readers_field.get(code_loader):
                project = project_id(dex_reader)
                projects.append(project)

                self._connection.send_packet(Subscribe(project).encode())

                last_sync = int(self._rename_engine.get_metadata_property(project, 'last_sync') or 0)
                self._connection.send_packet(FullSyncRequest(project, last_sync).encode())

        self._update_thread = Thread(JavaUpdateListener(self._connection, projects, self._rename_engine))
        self._update_thread.start()

        self._logger.error("[JSync] Activated")


def run(context, logger):
    # type: (JadxPluginContext, Logger) -> None
    logger.error("[JSync] Cleaning previous instances...")
    clean_previous_executions()
    JSync(context, logger).start()
