import os
import atexit

from java.net import Socket
from java.lang import Thread
from javax.swing import JOptionPane

from jadx.api.plugins import JadxPluginContext
from jadx.api import JadxDecompiler
from jadx.plugins.input.dex import DexLoadResult
from org.slf4j import Logger

from .connection import JADXConnection
from .rename_engine import JADXRenameEngine
from .rename_listener import JADXRenameListener
from .sync_to_server import JADXSyncToServer
from .utils import project_id
from .config import DATA_ROOT
from java_common.update_listener import JavaUpdateListener
from common.commands import FullSyncRequest, Subscribe
from common.connection import query_server
from jsync_cache import INSTANCES


def clean_previous_executions():
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
        self._rename_engine = None

        INSTANCES.append(self)
        atexit.register(self.clean)

    @property
    def active(self):
        # type: () -> bool
        return self._active

    def clean(self):
        self._logger.error("[JSync] Cleaning instance...")
        if self in INSTANCES:
            INSTANCES.remove(self)

        if self._rename_listener is not None:
            self._rename_listener.stop()
            self._rename_listener = None
        if self._update_thread is not None:
            self._update_thread.interrupt()
            self._update_thread = None
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        if self._rename_engine is not None:
            self._rename_engine.dump_rename_records()
            self._rename_engine = None

        self._logger.error("[JSync] Instance cleaned.")

    def start(self):
        self._logger.error("[JSync] Activating...")
        self._rename_engine = JADXRenameEngine(self._context)

        config_path = os.path.join(DATA_ROOT, 'connection')
        host, port, name = query_server(
            lambda default: JOptionPane.showInputDialog(
                "Connection Configuration: <name>@<host>:<port>", default
            ),
            config_path
        )

        sock = Socket(host, port)
        self._connection = JADXConnection(self, self._logger, sock)
        self._connection.send_packet(name.encode('utf-8'))
        self._rename_listener = JADXRenameListener(self._context, self._logger, self._connection, self._rename_engine)
        self._rename_listener.start()

        sync_to_server = Thread(JADXSyncToServer(self._context, self._logger, self._connection, self._rename_engine,
                                                 self.after_sync))
        sync_to_server.start()

    def after_sync(self):
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
                self._connection.send_packet(Subscribe(project).encode())
                self._connection.send_packet(FullSyncRequest(project).encode())
                projects.append(project)

        self._update_thread = Thread(JavaUpdateListener(self._connection, projects, self._rename_engine))
        self._update_thread.start()

        self._logger.info("[JSync] Activated")


def run(context, logger):
    # type: (JadxPluginContext, Logger) -> None
    clean_previous_executions()
    JSync(context, logger).start()
