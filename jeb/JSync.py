# ?description=Activate JSync
# ?shortcut=Mod1+J

import functools
import os
import re
import sys
import traceback

from java.net import Socket
from java.lang import Thread

from com.pnfsoftware.jeb.client.api import IScript, IClientContext
from com.pnfsoftware.jeb.core.units.code.android import IDexUnit

from .config import DATA_ROOT
from .connection import JEBConnection
from .rename_engine import JEBRenameEngine
from .rename_listener import JEBRenameListener
from .sync_to_server import JEBSyncToServer
from .utils import project_id
from java_common.update_listener import JavaUpdateListener
from common.commands import Subscribe, FullSyncRequest


class JSync(IScript):
    def __init__(self):
        # type: () -> None
        self.connection = None  # type: JEBConnection
        self.update_listener_thread = None  # type: Thread
        self.sync_to_server_thread = None  # type: Thread
        self._rename_engine = None  # type: JEBRenameEngine

    @staticmethod
    def clean_previous_executions(ctx):
        # type: (IClientContext) -> None
        for dex in ctx.mainProject.findUnits(IDexUnit):
            for listener in list(dex.listeners):
                jsync = getattr(listener, "_jsync", None)
                if jsync is not None:
                    jsync.clean(ctx)

    def clean(self, ctx):
        if self.update_listener_thread is not None:
            self.update_listener_thread.interrupt()
            self.update_listener_thread = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None

        for dex in ctx.mainProject.findUnits(IDexUnit):
            for listener in dex.listeners:
                jsync = getattr(listener, "_jsync", None)
                if jsync is self:
                    dex.removeListener(listener)

    def run(self, ctx):
        # type: (IClientContext) -> None
        print("[jsync] Clearing previous listeners")
        self.clean_previous_executions(ctx)

        config_path = DATA_ROOT / 'connection'
        default_connection = "user@localhost:9501"
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                default_connection = f.read()

        while True:
            connection_description = ctx.displayQuestionBox(
                "Input", "Connection Configuration: <name>@<host>:<port>", default_connection
            )
            if connection_description == "":
                return
            m = re.match(r"(?P<name>.*)@(?P<host>.*)(:(?P<port>[0-9]*))", connection_description)
            if m is not None:
                break

        with open(config_path, "w") as f:
            f.write(connection_description)

        name = m.group("name").encode("utf-8")
        host = m.group("host").encode("utf-8")
        port = int(m.group("port"))

        # Create server connection socket
        self.connection = JEBConnection(self, Socket(host, port))
        # Send name to server
        self.connection.send_packet(name)
        print("[jsync] Successfully connected to server")

        self._rename_engine = JEBRenameEngine(connection_description, ctx)

        rename_listener = JEBRenameListener(self, ctx, self.connection, self._rename_engine)
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
