# ?description=Activate JSync
# ?shortcut=Mod1+J
import atexit
import functools
import os
import sys
import traceback

from java.net import Socket
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
from common.commands import Subscribe, FullSyncRequest
from common.connection import query_server


class JSync(IScript):
    def __init__(self):
        # type: () -> None
        self.connection = None  # type: JEBConnection
        self.update_listener_thread = None  # type: Thread
        self.sync_to_server_thread = None  # type: Thread
        self._rename_engine = None  # type: JEBRenameEngine
        self._context = None  # type: IClientContext

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

        # Create server connection socket
        self.connection = JEBConnection(self, Socket(host, port))
        # Send name to server
        self.connection.send_packet(name)
        print("[jsync] Successfully connected to server as %s" % name)

        self._rename_engine = JEBRenameEngine(ctx)

        rename_listener = JEBRenameListener(self, ctx, self.connection, self._rename_engine, name)
        rename_listener.start()

        print("[jsync] Preparing to push symbols to server")
        self.sync_to_server_thread = Thread(
            JEBSyncToServer(ctx, self.connection, self._rename_engine, functools.partial(self.after_sync, ctx=ctx))
        )
        self.sync_to_server_thread.start()

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
