# ?description=Activate JSync
# ?shortcut=Mod1+J
import atexit
import functools
import os
import sys
import traceback

from java.lang import Thread

from com.pnfsoftware.jeb.client.api import IScript, IClientContext
from com.pnfsoftware.jeb.core.units.code.android import IDexUnit

from .config import JSYNC_JEB_ROOT
from .connection import JEBConnection
from .rename_engine import JEBRenameEngine
from .rename_listener import JEBRenameListener
from .sync_to_server import JEBSyncToServer
from .utils import project_id
from java_common.update_listener import JavaUpdateListener
from java_common.sqlite_adapter import SqliteAdapter
from java_common.wrappers import ThreadWrapper
from common.commands import Subscribe, FullSyncRequest
from client_base.server_query import query_server


class JSync(IScript):
    def __init__(self):
        # type: () -> None
        self.connection = None  # type: JEBConnection
        self.update_listener_thread = None  # type: Thread
        self.sync_to_server_thread = None  # type: Thread
        self._rename_engine = None  # type: JEBRenameEngine
        self._context = None  # type: IClientContext
        self._initialization_thread = None  # type: Thread

        atexit.register(self.clean)

    @staticmethod
    def clean_previous_executions(ctx):
        # type: (IClientContext) -> None
        for dex in ctx.mainProject.findUnits(IDexUnit):
            for listener in list(dex.listeners):
                jsync = getattr(listener, "_jsync", None)
                if jsync is not None:
                    jsync.clean()

    def clean(self):
        # type: () -> None
        if self.update_listener_thread is not None:
            self.update_listener_thread.interrupt()
            self.update_listener_thread = None
        if self._initialization_thread is not None:
            self._initialization_thread.interrupt()
            self._initialization_thread = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None

        if self._context is None:
            return

        for dex in self._context.mainProject.findUnits(IDexUnit):
            for listener in dex.listeners:
                jsync = getattr(listener, "_jsync", None)
                if jsync is self:
                    dex.removeListener(listener)

    def run(self, ctx):
        # type: (IClientContext) -> None
        self._context = ctx
        print("[jsync] Clearing previous listeners")
        self.clean_previous_executions(ctx)

        config_path = os.path.join(JSYNC_JEB_ROOT, 'connection')
        host, port, name = query_server(
            lambda default: ctx.displayQuestionBox(
                "Input", "Connection Configuration: <name>@<host>:<port>", default
            ),
            config_path
        )

        if host is None or port is None or name is None:
            print("[JSync] No server specified, exiting...")
            return

        print("[JSync] Activating...")

        # Create server connection socket
        self.connection = JEBConnection(self, host, port, name)
        print("[JSync] Successfully connected to server as %s" % name)

        self._initialization_thread = Thread(ThreadWrapper(self.initialize, ctx))
        self._initialization_thread.start()

    def initialize(self, ctx):
        # type: (IClientContext) -> None
        SqliteAdapter.ensure_jars(self.connection)

        self._rename_engine = JEBRenameEngine(ctx, self.connection.name)

        rename_listener = JEBRenameListener(self, ctx, self.connection, self._rename_engine, self.connection.name)
        rename_listener.start()

        print("[jsync] Preparing to push symbols to server")
        self.sync_to_server_thread = Thread(
            JEBSyncToServer(ctx, self.connection, self._rename_engine, functools.partial(self.after_sync, ctx=ctx))
        )
        self.sync_to_server_thread.start()

        self._initialization_thread = None

    def after_sync(self, ctx):
        # type: (IClientContext) -> None
        print("[jsync] Finished pushing symbols to server")
        print("[jsync] Subscribing to active projects")
        try:
            prj = ctx.mainProject

            projects = []
            for dex_unit in prj.findUnits(IDexUnit):
                for dex_file in dex_unit.dexFiles:
                    pid = project_id(dex_file)
                    projects.append(pid)
                    self.connection.send_packet(Subscribe(pid).encode())
                    self.connection.send_packet(FullSyncRequest(pid).encode())

            self.update_listener_thread = Thread(JavaUpdateListener(self.connection, projects, self._rename_engine))
            self.update_listener_thread.start()
        except:  # noqa
            traceback.print_exc(file=sys.stdout)

        print("[jsync] Ready!")
