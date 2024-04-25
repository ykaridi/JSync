# ?description=Connect to JEBSync
import functools
import os
import re
import sys
import traceback

from java.net import Socket
from java.lang import Thread

from com.pnfsoftware.jeb.client.api import IScript, IClientContext
from com.pnfsoftware.jeb.core.units.code.android import IDexUnit

from .utils import send_packet, project_id
from .rename_engine import RenameEngine
from .rename_listener import RenameListener
from .update_listener import UpdateListener
from .sync_to_server import SyncToServer
from common.commands import Subscribe, FullSyncRequest


class JEBSync(IScript):
    def __init__(self):
        # type: () -> None
        self.sock = None  # type: Socket
        self.update_listener_thread = None  # type: Thread
        self.sync_to_server_thread = None  # type: Thread
        self._rename_engine = None  # type: RenameEngine

    @staticmethod
    def clean_previous_executions(ctx):
        # type: (IClientContext) -> None
        for dex in ctx.mainProject.findUnits(IDexUnit):
            for listener in dex.getListeners():
                jebsync = getattr(listener, '_jebsync', None)
                if jebsync is not None:
                    if jebsync.update_listener_thread is not None:
                        jebsync.update_listener_thread.interrupt()
                        jebsync.update_listener_thread = None
                    if jebsync.sock is not None:
                        jebsync.sock.close()
                        jebsync.sock = None
                    dex.removeListener(listener)

    def run(self, ctx):
        # type: (IClientContext) -> None
        print("[JEBSync] Clearing previous listeners")
        self.clean_previous_executions(ctx)

        config_path = os.path.expanduser('~/.jebsync')
        default_connection = 'user@localhost:9501'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                default_connection = f.read()

        while True:
            connection_description = ctx.displayQuestionBox('Input', 'Connection Configuration: <name>@<host>:<port>',
                                                default_connection)
            if connection_description == "":
                return
            m = re.match(r'(?P<name>.*)@(?P<host>.*)(:(?P<port>[0-9]*))', connection_description)
            if m is not None:
                break

        with open(config_path, 'w') as f:
            f.write(connection_description)

        name = m.group('name').encode('utf-8')
        host = m.group('host').encode('utf-8')
        port = int(m.group('port'))

        # Create server connection socket
        self.sock = Socket(host, port)
        # Send name to server
        send_packet(self.sock, name)
        print("[JEBSync] Successfully connected to server")

        prj = ctx.mainProject
        self._rename_engine = RenameEngine(connection_description)
        rename_listener = RenameListener(self, self.sock, self._rename_engine)
        for dex in prj.findUnits(IDexUnit):
            dex.addListener(rename_listener)

        print("[JEBSync] Preparing to push symbols to server")
        self.sync_to_server_thread = Thread(SyncToServer(ctx, self.sock, self._rename_engine,
                                                         functools.partial(self.after_sync, ctx=ctx)))
        self.sync_to_server_thread.start()

    def after_sync(self, ctx):
        # type: (IClientContext) -> None
        print("[JEBSync] Finished pushing symbols to server")
        print("[JEBSync] Subscribing to active projects")
        try:
            prj = ctx.mainProject

            for dex in prj.findUnits(IDexUnit):
                pid = project_id(dex)
                send_packet(self.sock, Subscribe(pid).encode())
                send_packet(self.sock, FullSyncRequest(pid).encode())

            self.update_listener_thread = Thread(UpdateListener(ctx, self.sock, self._rename_engine))
            self.update_listener_thread.start()
        except:  # noqa
            traceback.print_exc(file=sys.stdout)

        print("[JEBSync] Ready!")
