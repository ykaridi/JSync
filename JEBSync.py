# This is for jython
from __future__ import division

import importlib
import itertools
import runpy
import sys
import os
import traceback
from contextlib import contextmanager


# Code for module <common.commands>
PYBUNCH_COMMON_COMMANDS = """
import json

from .dataclass import Dataclass
from .symbol import Symbol


COMMAND_ENCODER = None  # type: json.JSONEncoder
COMMAND_DECODER = None  # type: json.JSONDecoder


class Command(Dataclass):
    def encode(self):
        # type: () -> bytes
        global COMMAND_ENCODER
        return COMMAND_ENCODER.encode(self).encode('utf-8')

    @staticmethod
    def decode(data):
        # type: (bytes) -> 'Command'
        global COMMAND_DECODER
        return COMMAND_DECODER.decode(data.decode('utf-8'))


class _CommandEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Dataclass):
            d = {'__type__': type(obj).__name__}
            d.update(vars(obj))
            return d
        return super(_CommandEncoder, self).default(obj)


class _CommandDecoder(json.JSONDecoder):
    def __init__(self):
        super(_CommandDecoder, self).__init__(object_hook=self.object_hook)
        self._types = {k: v for k, v in globals().items() if isinstance(v, type) and issubclass(v, Dataclass)}

    def object_hook(self, dct):
        if '__type__' in dct:
            typ = dct.pop('__type__')
            if typ not in self._types:
                raise ValueError(\"Unhandled dynamic type\")
            return self._types[typ](**dct)
        else:
            return dct


class Subscribe(Command):
    def __init__(self, project):
        # type: (str) -> None
        self.project = project


class Unsubscribe(Command):
    def __init__(self, project):
        # type: (str) -> None
        self.project = project


class UpstreamSymbols(Command):
    def __init__(self, project, symbols, loggable):
        # type: (str, list[Symbol], bool) -> None
        self.project = project
        self.symbols = symbols
        self.loggable = loggable


class DownstreamSymbols(Command):
    def __init__(self, project, symbols):
        # type: (str, list[Symbol]) -> None
        self.project = project
        self.symbols = symbols


class FullSyncRequest(Command):
    def __init__(self, project):
        # type: (str) -> None
        self.project = project


COMMAND_ENCODER = _CommandEncoder()
COMMAND_DECODER = _CommandDecoder()

"""[1:]


# Code for module <client.__init__>
PYBUNCH_CLIENT___INIT__ = """

"""[1:]


# Code for module <server.symbol_server>
PYBUNCH_SERVER_SYMBOL_SERVER = """
import asyncio
import logging
import socket
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Set

from .symbol_store import SymbolStore
from .utils import LazyDict, recv_packet, send_packet
from common.symbol import Symbol
from common.commands import Command, Subscribe, Unsubscribe, UpstreamSymbols, DownstreamSymbols, FullSyncRequest


logging.basicConfig(level=logging.DEBUG, format='%(message)s')


@dataclass(frozen=True, unsafe_hash=True)
class Client:
    name: str
    address: str
    reader: asyncio.StreamReader = field(repr=False, compare=False, hash=False)
    writer: asyncio.StreamWriter = field(repr=False, compare=False, hash=False)
    associated_projects: Set[str] = field(init=False, default_factory=lambda: set(), repr=False, compare=False,
                                          hash=False)


class SymbolServer(ABC):
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self._stores: LazyDict[str, SymbolStore] = LazyDict(mapping=self._get_store)
        self._clients: Set[Client] = set()
        self._project_associations: Dict[str, Set[Client]] = defaultdict(lambda: set())

    @abstractmethod
    def _get_store(self, project: str) -> SymbolStore:
        raise NotImplemented

    @staticmethod
    async def push_to_client(client: Client, payload: bytes):
        try:
            await send_packet(client.writer, payload)
        except socket.error:
            logging.debug(f\"Connection from {client.writer.get_extra_info('peername')} is closed but not yet cleared\")

    async def push_update(self, project: str, symbols: List[Symbol], originator: Client):
        command = DownstreamSymbols(project, symbols)
        payload = command.encode()
        for client in self._project_associations[project]:
            if client != originator:
                    await self.push_to_client(client, payload)

    async def push_symbols(self, client: Client, project: str, symbols: List[Symbol]):
        payload = DownstreamSymbols(project, symbols).encode()
        await self.push_to_client(client, payload)

    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        name = (await recv_packet(reader)).decode('utf-8')

        address = writer.get_extra_info('peername')
        logging.critical(f\"[Connect] New connection from {name} @ {address}\")

        client = Client(name, address, reader, writer)

        # Save the connection
        self._clients.add(client)

        while True:
            try:
                packet = await recv_packet(reader)
                command = Command.decode(packet)

                if isinstance(command, Subscribe):
                    client.associated_projects.add(command.project)
                    self._project_associations[command.project].add(client)
                elif isinstance(command, Unsubscribe):
                    client.associated_projects.remove(command.project)
                    if client in self._project_associations[command.project]:
                        self._project_associations[command.project].remove(client)
                elif isinstance(command, UpstreamSymbols):
                    store = self._stores[command.project]
                    symbols = command.symbols
                    for symbol in symbols:
                        symbol.author = name

                    symbols = list(store.changed_symbols(symbols))

                    if command.loggable:
                        for symbol in symbols:
                            logging.info(f\"[Symbol] {name}: {symbol.canonical_signature} -> {symbol.name}\")

                    store.push_symbols(symbols, only_changed=False)
                    await self.push_update(command.project, symbols, client)
                elif isinstance(command, FullSyncRequest):
                    logging.info(f\"[Full Sync] Request from {name}\")
                    store = self._stores[command.project]
                    symbols = list(store.get_latest_symbols())
                    await self.push_symbols(client, command.project, symbols)
            except (ConnectionResetError, asyncio.IncompleteReadError):
                logging.critical(f\"[Disconnect] {name} disconnected @ {address}\")
                self._clients.remove(client)
                for project in client.associated_projects:
                    self._project_associations[project].remove(client)

                break

    async def serve_forever(self):
        async with await asyncio.start_server(self.handle_connection, self._host, self._port):
            # Run forever
            await asyncio.Future()

    def close(self):
        for store in self._stores.values():
            store.close()

"""[1:]


# Code for module <common.dataclass>
PYBUNCH_COMMON_DATACLASS = """
class Dataclass(object):
    def description(self, descriptor=str):
        # type: (str | repr) -> str
        return \"%s(%s)\" % (self.__class__.__name__, ', '.join(\"%s=%s\" % (k, descriptor(v))
                                                             for k, v in vars(self).items()))

    def __str__(self):
        # type: () -> str
        return self.description(descriptor=repr)

    def __repr__(self):
        # type: () -> str
        return self.description(descriptor=repr)

"""[1:]


# Code for module <common.__init__>
PYBUNCH_COMMON___INIT__ = """

"""[1:]


# Code for module <server.__init__>
PYBUNCH_SERVER___INIT__ = """

"""[1:]


# Code for module <server.sqlite_symbol_store>
PYBUNCH_SERVER_SQLITE_SYMBOL_STORE = """
import itertools
import os
import sqlite3
from contextlib import closing
from typing import Iterable, Optional, List

from common.symbol import Symbol
from .symbol_store import SymbolStore

MAXIMAL_TRANSACTION_SIZE = 10000


class SqliteSymbolStore(SymbolStore):
    def __init__(self, path: os.PathLike):
        self._conn = sqlite3.connect(path)
        self._conn.execute(\"\"\"
        CREATE TABLE IF NOT EXISTS symbols (
            author TEXT,
            symbol_type INTEGER,
            canonical_signature TEXT,
            name TEXT,
            timestamp INTEGER,
            PRIMARY KEY (author, canonical_signature, timestamp)
        );
        \"\"\")

    @staticmethod
    def _symbol_to_row(symbol: Symbol) -> List[str | int]:
        return [symbol.author, symbol.symbol_type, symbol.canonical_signature, symbol.name, symbol.timestamp]

    def push_symbols(self, symbols: Iterable[Symbol], only_changed: bool = True) -> None:
        symbols = iter(self.changed_symbols(symbols) if only_changed else symbols)
        with closing(self._conn.cursor()) as cur:
            while batch := [self._symbol_to_row(row) for row in itertools.islice(symbols, MAXIMAL_TRANSACTION_SIZE)]:
                cur.executemany(\"INSERT OR IGNORE INTO symbols(author, symbol_type, canonical_signature, name, timestamp)\"
                                \" VALUES (?, ?, ?, ?, ?)\", batch)
        self._conn.commit()

    def get_symbols(self, canonical_signature: Optional[str] = None, author: Optional[str] = None) -> Iterable[Symbol]:
        with closing(self._conn.cursor()) as cur:
            if canonical_signature is None and author is None:
                cur.execute(\"SELECT *, max(timestamp) FROM symbols GROUP BY canonical_signature, author;\")
            elif canonical_signature is not None and author is None:
                cur.execute(\"SELECT *, max(timestamp) FROM symbols WHERE canonical_signature = ? GROUP BY author;\",
                            [canonical_signature])
            elif canonical_signature is None and author is not None:
                cur.execute(\"SELECT *, max(timestamp) FROM symbols WHERE author = ? GROUP BY canonical_signature;\",
                            [author])
            elif canonical_signature is not None and author is not None:
                cur.execute(\"SELECT *, max(timestamp) FROM symbols WHERE canonical_signature = ? AND author = ?\",
                            [canonical_signature, author])

            for row in cur:
                if all(x is None for x in row):
                    continue

                author, symbol_type, canonical_signature, name, timestamp, _ = row
                yield Symbol(symbol_type, canonical_signature, name, timestamp=timestamp, author=author)

    def get_latest_symbols(self, canonical_signature: Optional[str] = None) -> Iterable[Symbol]:
        with closing(self._conn.cursor()) as cur:
            if canonical_signature is None:
                cur.execute(\"SELECT author, symbol_type, canonical_signature, name, timestamp , max(timestamp) \"
                            \"FROM symbols GROUP BY canonical_signature;\")
            elif canonical_signature is not None:
                cur.execute(\"SELECT author, symbol_type, canonical_signature, name, timestamp, max(timestamp) FROM symbols WHERE canonical_signature = ?;\",
                            [canonical_signature])

            for row in cur:
                author, symbol_type, canonical_signature, name, timestamp, _ = row
                yield Symbol(symbol_type, canonical_signature, name, timestamp=timestamp, author=author)

    def close(self):
        self._conn.close()

"""[1:]


# Code for module <client.jebsync>
PYBUNCH_CLIENT_JEBSYNC = """
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
        self.rename_engine = RenameEngine()

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
        print(\"[JEBSync] Clearing previous listeners\")
        self.clean_previous_executions(ctx)

        config_path = os.path.expanduser('~/.jebsync')
        default_connection = 'user@localhost:9501'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                default_connection = f.read()

        while True:
            connection = ctx.displayQuestionBox('Input', 'Connection Configuration: <name>@<host>:<port>',
                                                default_connection)
            if connection == \"\":
                return
            m = re.match(r'(?P<name>.*)@(?P<host>.*)(:(?P<port>[0-9]*))', connection)
            if m is not None:
                break

        with open(config_path, 'w') as f:
            f.write(connection)

        name = m.group('name').encode('utf-8')
        host = m.group('host').encode('utf-8')
        port = int(m.group('port'))

        # Create server connection socket
        self.sock = Socket(host, port)
        # Send name to server
        send_packet(self.sock, name)
        print(\"[JEBSync] Successfully connected to server\")

        prj = ctx.mainProject
        rename_listener = RenameListener(self, self.sock, self.rename_engine)
        for dex in prj.findUnits(IDexUnit):
            dex.addListener(rename_listener)

        print(\"[JEBSync] Preparing to push symbols to server\")
        self.sync_to_server_thread = Thread(SyncToServer(ctx, self.sock, self.rename_engine,
                                                         functools.partial(self.after_sync, ctx=ctx)))
        self.sync_to_server_thread.start()

    def after_sync(self, ctx):
        # type: (IClientContext) -> None
        print(\"[JEBSync] Finished pushing symbols to server\")
        print(\"[JEBSync] Subscribing to active projects\")
        try:
            prj = ctx.mainProject

            for dex in prj.findUnits(IDexUnit):
                pid = project_id(dex)
                send_packet(self.sock, Subscribe(pid).encode())
                send_packet(self.sock, FullSyncRequest(pid).encode())

            self.update_listener_thread = Thread(UpdateListener(ctx, self.sock, self.rename_engine))
            self.update_listener_thread.start()
        except:  # noqa
            traceback.print_exc(file=sys.stdout)

        print(\"[JEBSync] Ready!\")

"""[1:]


# Code for module <server.__main__>
PYBUNCH_SERVER___MAIN__ = """
import argparse
import asyncio
from pathlib import Path

from .default_symbol_server import DefaultSymbolServer

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='JEBSync_Server',
                                     description='JEBSync Server')
    parser.add_argument('-d', '--directory', type=Path, required=True, help='Directory for symbol stores')
    parser.add_argument('-p', '--port', type=int, default=9501,
                        help='Port to listen on')

    args = parser.parse_args()
    port = args.port
    directory = args.directory

    server = DefaultSymbolServer('0.0.0.0', port, directory)
    asyncio.run(server.serve_forever())

"""[1:]


# Code for module <client.utils>
PYBUNCH_CLIENT_UTILS = """
import struct

from common.consts import PACKET_SIZE_FORMAT
from common.symbol import Symbol, SYMBOL_TYPE_FIELD, SYMBOL_TYPE_METHOD, SYMBOL_TYPE_CLASS

import jarray
from java.io import DataInputStream, BufferedOutputStream
from java.net import Socket
from org.python.core.util import StringUtil
from com.pnfsoftware.jeb.core.units.code.android import IDexUnit
from com.pnfsoftware.jeb.core.units.code.android.dex import IDexMethod, IDexClass, IDexField, IDexType
from com.pnfsoftware.jeb.core.actions import Actions, ActionContext, ActionOverridesData


# dex_unit.uid -> typ.getSignature(False) -> method.getName(False) -> method
TYPE_METHOD_MAPPING = {}  # type: dict[int, dict[str, dict[str, IDexMethod]]]


def recv_fully(sock, amt):
    # type: (Socket, int) -> bytes
    input_stream = DataInputStream(sock.inputStream)
    byts = jarray.zeros(amt, \"b\")
    input_stream.readFully(byts)
    return StringUtil.fromBytes(byts)


def recv_packet(sock):
    # type: (Socket) -> bytes
    size = struct.unpack(PACKET_SIZE_FORMAT, recv_fully(sock, struct.calcsize(PACKET_SIZE_FORMAT)))[0]
    return recv_fully(sock, size)


def send_fully(sock, data):
    # type: (Socket, bytes) -> None
    out = BufferedOutputStream(sock.getOutputStream())
    out.write(data)
    out.flush()


def send_packet(sock, data):
    # type: (Socket, bytes) -> None
    send_fully(sock, struct.pack(PACKET_SIZE_FORMAT, len(data)))
    send_fully(sock, data)


def project_id(unit):
    # type: (IDexUnit) -> str
    _identifier = abs(hash(tuple(sorted(file.expectedChecksum for file in unit.dexFiles))))
    identifier = hex(_identifier)[2:].rstrip('L').rjust(8, '0')
    return identifier


def method_is_override(method):
    # type: (IDexMethod) -> bool
    data = ActionOverridesData()
    unit = method.dex
    if unit.prepareExecution(ActionContext(unit, Actions.QUERY_OVERRIDES, method.itemId, None), data):
        return len(data.parents) > 0

    return False


def encode_symbol(o):
    # type: (IDexField | IDexMethod | IDexClass) -> Symbol
    canonical_signature = o.getSignature(False)
    name = o.getName(True) or o.getName(False)

    if isinstance(o, IDexField):
        return Symbol(SYMBOL_TYPE_FIELD, canonical_signature, name)
    elif isinstance(o, IDexMethod):
        return Symbol(SYMBOL_TYPE_METHOD, canonical_signature, name)
    else:
        return Symbol(SYMBOL_TYPE_CLASS, canonical_signature, name)

"""[1:]


# Code for module <server.symbol_store>
PYBUNCH_SERVER_SYMBOL_STORE = """
from abc import ABC, abstractmethod
from typing import Iterable, Optional

from common.symbol import Symbol


class SymbolStore(ABC):
    def push_symbol(self, symbol: Symbol) -> None:
        return self.push_symbols([symbol])

    def changed_symbols(self, symbols: Iterable[Symbol]) -> Iterable[Symbol]:
        for symbol in symbols:
            existing_symbols = list(self.get_symbols(canonical_signature=symbol.canonical_signature,
                                                     author=symbol.author))

            if len(existing_symbols) == 0:
                yield symbol
            else:
                existing_symbol, = existing_symbols
                if symbol.name != existing_symbol.name:
                    yield symbol

    def push_symbols(self, symbols: Iterable[Symbol], only_changed: bool = True) -> None:
        raise NotImplemented

    @abstractmethod
    def get_symbols(self, canonical_signature: Optional[str] = None, author: Optional[str] = None) -> Iterable[Symbol]:
        raise NotImplemented

    def get_latest_symbols(self, canonical_signature: Optional[str] = None) -> Iterable[Symbol]:
        raise NotImplemented

    @abstractmethod
    def close(self) -> None:
        raise NotImplemented

"""[1:]


# Code for module <server.default_symbol_server>
PYBUNCH_SERVER_DEFAULT_SYMBOL_SERVER = """
from pathlib import Path

from .sqlite_symbol_store import SqliteSymbolStore
from .symbol_store import SymbolStore
from .symbol_server import SymbolServer


class DefaultSymbolServer(SymbolServer):
    def __init__(self, host: str, port: int, store_directory: Path):
        super().__init__(host, port)
        self._store_directory = store_directory

    def _get_store(self, project: str) -> SymbolStore:
        return SqliteSymbolStore((self._store_directory / project).with_suffix('.symbol_store'))

"""[1:]


# Code for module <client.rename_engine>
PYBUNCH_CLIENT_RENAME_ENGINE = """
from com.pnfsoftware.jeb.core.units.code.android import IDexUnit
from com.pnfsoftware.jeb.core.units.code.android.dex import IDexItem, IDexField, IDexMethod, IDexClass
from com.pnfsoftware.jeb.core.units import IMetadataManager, MetadataGroup, MetadataGroupType

from threading import Lock
from common.symbol import Symbol, SYMBOL_TYPE_FIELD, SYMBOL_TYPE_METHOD, SYMBOL_TYPE_CLASS


METADATA_GROUP_NAME = 'JEBSync'


class RenameEngine(object):
    def __init__(self):
        # type: () -> None
        self._lock = Lock()

    @property
    def locked(self):
        return self._lock.locked()

    @staticmethod
    def _metadata_group(dex_unit):
        # type: (IDexUnit) -> MetadataGroup
        metadata_manager = dex_unit.metadataManager  # type: IMetadataManager
        if metadata_manager.getGroupByName(METADATA_GROUP_NAME) is None:
            metadata_manager.addGroup(MetadataGroup(METADATA_GROUP_NAME, MetadataGroupType.STRING))

        return metadata_manager.getGroupByName(METADATA_GROUP_NAME)

    def is_original_symbol(self, item):
        # type: (IDexItem) -> bool
        metadata_group = self._metadata_group(item.dex)
        data = metadata_group.getData(item.getSignature(False))
        return data != item.getName(True)

    def update_item_metadata(self, item):
        self._metadata_group(item.dex).setData(item.getSignature(False), item.getName(True))

    def enqueue_rename(self, unit, symbol):
        # type: (IDexUnit, Symbol) -> None
        item = None  # type: IDexItem
        if symbol.symbol_type == SYMBOL_TYPE_FIELD:
            item = unit.getField(symbol.canonical_signature)
        elif symbol.symbol_type == SYMBOL_TYPE_METHOD:
            item = unit.getMethod(symbol.canonical_signature)
        elif symbol.symbol_type == SYMBOL_TYPE_CLASS:
            item = unit.getClass(symbol.canonical_signature)

        if item is None:
            return

        with self._lock:
            if item.getName(True) != symbol.name:
                item.setName(symbol.name)

        self.update_item_metadata(item)

"""[1:]


# Code for module <server.utils>
PYBUNCH_SERVER_UTILS = """
import struct
import asyncio
from typing import Mapping, TypeVar, Callable, Iterator
from common.consts import PACKET_SIZE_FORMAT


KT = TypeVar('KT', covariant=True)  # Key type
VT = TypeVar('VT', contravariant=True)  # Value type


class LazyDict(Mapping[KT, VT]):
    def __init__(self, mapping: Callable[[KT], VT]):
        self._mapping = mapping
        self._dict = {}

    def __getitem__(self, item: KT) -> VT:
        if item not in self._dict:
            self._dict[item] = self._mapping(item)

        return self._dict[item]

    def __len__(self) -> int:
        return len(self._dict)

    def __iter__(self) -> Iterator[VT]:
        return iter(self._dict)


async def recv_packet(reader: asyncio.StreamReader) -> bytes:
    size = struct.unpack(PACKET_SIZE_FORMAT, await reader.readexactly(struct.calcsize(PACKET_SIZE_FORMAT)))[0]
    return await reader.readexactly(size)


async def send_packet(writer: asyncio.StreamWriter, data: bytes):
    writer.write(struct.pack(PACKET_SIZE_FORMAT, len(data)))
    writer.write(data)
    await writer.drain()

"""[1:]


# Code for module <client.update_listener>
PYBUNCH_CLIENT_UPDATE_LISTENER = """
import socket

from common.commands import Command, DownstreamSymbols
from .rename_engine import RenameEngine
from .utils import project_id, recv_packet

from java.lang import Runnable
from com.pnfsoftware.jeb.core.units.code.android import IDexUnit
from com.pnfsoftware.jeb.core import IRuntimeProject


class UpdateListener(Runnable):
    def __init__(self, ctx, sock, rename_engine):
        # type: (IRuntimeProject, socket.socket, RenameEngine) -> None
        super(UpdateListener, self).__init__()
        self._socket = sock
        self._rename_engine = rename_engine
        self._dexes = {project_id(unit): unit for unit in ctx.mainProject.findUnits(IDexUnit)}

    def run(self):
        # type: () -> None
        while True:
            try:
                packet = recv_packet(self._socket)
                if packet is None:
                    break

                command = Command.decode(packet)
                if isinstance(command, DownstreamSymbols):
                    if command.project in self._dexes:
                        dex_unit = self._dexes[command.project]
                        for symbol in command.symbols:
                            self._rename_engine.enqueue_rename(dex_unit, symbol)
            except:  # noqa
                return

"""[1:]


# Code for module <common.consts>
PYBUNCH_COMMON_CONSTS = """
PACKET_SIZE_FORMAT = \"!L\"

"""[1:]


# Code for module <common.symbol>
PYBUNCH_COMMON_SYMBOL = """
from .dataclass import Dataclass


SYMBOL_TYPE_FIELD = 0
SYMBOL_TYPE_METHOD = 1
SYMBOL_TYPE_CLASS = 2


class Symbol(Dataclass):
    def __init__(self, symbol_type, canonical_signature, name, timestamp=None, author=None):
        # type: (int, str, str, int, str) -> None
        self.author = author
        self.symbol_type = symbol_type
        self.canonical_signature = canonical_signature
        self.name = name
        self.timestamp = timestamp

"""[1:]


# Code for module <client.rename_listener>
PYBUNCH_CLIENT_RENAME_LISTENER = """
import time

from java.net import Socket
from com.pnfsoftware.jeb.core.units.code.android.dex import IDexMethod, IDexClass, IDexField
from com.pnfsoftware.jeb.util.events import IEventListener
from com.pnfsoftware.jeb.core.units import UnitChangeEventData
from com.pnfsoftware.jeb.core.events import JebEvent, J

from common.commands import UpstreamSymbols
from .utils import project_id, method_is_override, encode_symbol, send_packet
from .rename_engine import RenameEngine


class RenameListener(IEventListener):
    def __init__(self, jebsync, socket, rename_engine):
        # type: ('JEBSync', Socket, RenameEngine) -> None
        self._jebsync = jebsync
        self._socket = socket
        self._is_jebsync = True
        self._minimal_classes = {}  # type: dict[int, int]
        self._rename_engine = rename_engine

    def onEvent(self, e):
        # type: (JebEvent) -> None
        if isinstance(e, JebEvent) and e.type == J.UnitChange and e.data is not None:
            if e.data.type == UnitChangeEventData.NameUpdate:
                target = e.data.target

                if not isinstance(target, (IDexField, IDexMethod, IDexClass)):
                    return

                if self._rename_engine.locked:
                    # TODO: Is this the right way to do it?
                    #  We want to update metadata even in renames caused by root rename...
                    self._rename_engine.update_item_metadata(target)
                    return

                if isinstance(target, IDexMethod) and method_is_override(target):
                    return

                project = project_id(target.dex)
                symbol = encode_symbol(target)
                symbol.timestamp = int(time.time())
                command = UpstreamSymbols(project, [symbol], loggable=True)
                send_packet(self._socket, command.encode())

"""[1:]


# Code for module <client.sync_to_server>
PYBUNCH_CLIENT_SYNC_TO_SERVER = """
import time
import socket
import itertools

from common.commands import UpstreamSymbols
from .rename_engine import RenameEngine
from .utils import project_id, encode_symbol, send_packet, method_is_override

from java.lang import Runnable
from com.pnfsoftware.jeb.core.units.code.android.dex import IDexMethod
from com.pnfsoftware.jeb.core.units.code.android import IDexUnit
from com.pnfsoftware.jeb.core import IRuntimeProject


class SyncToServer(Runnable):
    def __init__(self, ctx, sock, rename_engine, callback):
        # type: (IRuntimeProject, socket.socket, RenameEngine, callable) -> None
        super(SyncToServer, self).__init__()
        self._ctx = ctx
        self._socket = sock
        self._callback = callback
        self._rename_engine = rename_engine

    def run(self):
        # type: () -> None
        for dex_unit in self._ctx.mainProject.findUnits(IDexUnit):
            symbols = []
            for item in itertools.chain(dex_unit.fields, dex_unit.methods, dex_unit.classes):
                if (not item.renamed) or (not self._rename_engine.is_original_symbol(item)):
                    continue

                if isinstance(item, IDexMethod) and method_is_override(item):
                    continue

                symbol = encode_symbol(item)
                symbol.timestamp = int(time.time())
                symbols.append(symbol)

            if symbols:
                command = UpstreamSymbols(project_id(dex_unit), symbols, loggable=False)
                # send_packet(self._socket, command.encode())

        self._callback()

"""[1:]


_module_type = type(os)


class ModulePath(object):
    def __init__(self, *parts):
        # type: (*str) -> None
        self.parts = tuple(parts)

    @staticmethod
    def from_name(name):
        # type: (str) -> 'ModulePath'
        return ModulePath(*name.split('.'))

    @property
    def name(self):
        # type: () -> str
        return self.parts[-1]

    @property
    def parent(self):
        # type: () -> 'ModulePath'
        return ModulePath(*self.parts[:-1])

    def __truediv__(self, other):
        # type: ('ModulePath' | str) -> 'ModulePath'
        if isinstance(other, ModulePath):
            return ModulePath(*(self.parts + other.parts))
        elif isinstance(other, str):
            return ModulePath(*(self.parts + (other, )))
        else:
            raise ValueError("Can only concat ModulePath with str or ModulePath")

    def is_relative_to(self, other):
        # type: ('ModulePath') -> bool
        length = len(other.parts)
        return length <= len(self.parts) and self.parts[:length] == other.parts

    def relative_to(self, other):
        # type: ('ModulePath') -> 'ModulePath'
        if not self.is_relative_to(other):
            raise ValueError("ModulePath must be relative to given ModulePath")

        return ModulePath(*self.parts[len(other.parts):])

    def __hash__(self):
        # type: () -> int
        return hash(self.parts)

    def __eq__(self, other):
        # type: (object) -> bool
        if not isinstance(other, ModulePath):
            return False
        return self.parts == other.parts

    def __str__(self):
        # type: () -> str
        return '.'.join(self.parts)

    def __repr__(self):
        # type: () -> str
        return 'ModulePath%s' % repr(self.parts)


class ModuleDescription(object):
    def __init__(self, name, code):
        # type: (str, str) -> None
        self.name = name
        self.file_name = 'pybunch <%s>' % name
        self.path = ModulePath(*name.split('.'))
        self.parent_name = '.'.join(self.path.parts[:-1])
        self.package = None  # type: str
        self.source_code = code
        self._compiled = None  # type: 'code'
        self._module = None  # type: _module_type | None


    @property
    def compiled(self):
        if self._compiled is None:
            self._compiled = compile(self.source_code, self.file_name, 'exec')
        return self._compiled

    def is_package(self, name):
        # type: (str) -> bool
        return self.path.parts[-1] == '__init__'

    def load_module(self, name):
        # type: (str) -> _module_type
        if self._module is None:
            if self.is_package(None):
                module = _module_type(self.parent_name)
                self.package = '.'.join(self.path.parts[:-2])
                self.name = self.parent_name
                module.__path__ = []
            else:
                module = _module_type(self.name)
                self.package = self.parent_name

            module.__package__ = self.package
            module.__file__ = self.file_name
            self.run_module(_globals=module.__dict__)
            self._module = module

        return sys.modules.setdefault(name, self._module)

    def run_module(self, _globals=None, name=None):
        # type: (str) -> None
        if _globals is None:
            _globals = {}

        _globals.update(__name__=name if name is not None else self.name,
                        __file__=self.file_name,
                        __loader__=self,
                        __package__=self.parent_name)

        restore_name = '__name__' in _globals
        old_filename = _globals.get('__name__', None)
        if name is not None:
            _globals['__name__'] = name

        exec(self.compiled, _globals)
        if restore_name:
            _globals[''] = old_filename
        else:
            del _globals['__name__']

        return _globals

    def get_code(self, name):
        # type: (str) -> 'code'
        return self.compiled

    def get_source(self, *args, **kwargs):
        return self.source_code


RESOLVED_IMPORT_EXTERNAL = 'External'
RESOLVED_IMPORT_MISSING_LOCAL = 'Missing Local'
RESOLVED_IMPORT_LEAF_MODULE = 'Leaf Module'
RESOLVED_IMPORT_INTERMEDIATE_MODULE = 'Intermediate Module'


class DynamicLocalImporter(object):
    def __init__(self, module_descriptions):
        # type: (dict[str, ModuleDescription]) -> None
        self._module_descriptions = {ModulePath.from_name(name): description
                                     for name, description in module_descriptions.items()}

        self._module_specs = {}  # dict[str, _module_type]

    @property
    def loaded_modules(self):
        # type: () -> set[str]
        return set(self._module_specs.keys())

    @staticmethod
    def attempt_resolve_local_import(name, local_modules, module_aliases=None):
        # type: (str, list[ModulePath], dict[ModulePath, ModulePath]) -> tuple[str, ModulePath | None]
        local_modules = set(local_modules)
        if module_aliases is None:
            module_aliases = {}

        if not all(a == b or not a.is_relative_to(b) for a, b in itertools.product(module_aliases.keys(), repeat=2)):
            raise ValueError("Module aliases must be distinct")

        path = ModulePath.from_name(name)
        imports_base_module = path.parts[0] in {local_module.parts[0] for local_module in local_modules}
        base_alias = next((base for base in module_aliases.keys() if path.is_relative_to(base)), None)

        if imports_base_module or base_alias is not None:
            base = ModulePath()
            if base_alias is not None:
                path = module_aliases[base_alias] / path.relative_to(base_alias)

            imported_module = base / path
            if imported_module in local_modules:
                return RESOLVED_IMPORT_LEAF_MODULE, imported_module

            if (imported_module / '__init__') in local_modules:
                return RESOLVED_IMPORT_INTERMEDIATE_MODULE, imported_module

            return RESOLVED_IMPORT_MISSING_LOCAL, None
        else:
            return RESOLVED_IMPORT_EXTERNAL, None

    @property
    @contextmanager
    def add_to_meta_path(self):
        # type: () -> 'Generator[None, None, None]'
        old_meta_path = sys.meta_path
        sys.meta_path = [self] + sys.meta_path
        yield
        sys.meta_path = old_meta_path

    @property
    @contextmanager
    def with_custom_stacktrace(self):
        old_except_hook = sys.excepthook
        print_exception = traceback.print_exception

        def except_hook(ex_type, ex, tb):
            print_exception(ex_type, ex, tb)

        sys.excepthook = except_hook
        yield
        sys.excepthook = old_except_hook

    def import_module(self, module):
        # type: (str) -> _module_type
        with self.add_to_meta_path, self.with_custom_stacktrace:
            return importlib.import_module(module)

    def execute_module(self, module):
        # type: (str) -> _module_type
        with self.add_to_meta_path, self.with_custom_stacktrace:
            try:
                new_globals = runpy.run_module(module, run_name='__main__')
            except ImportError:
                # Fallback for jython
                imported_module = importlib.import_module(module)
                new_globals = imported_module.__loader__.run_module(name='__main__')

        current_globals = globals()
        keys_to_delete = set(current_globals.keys()).difference(new_globals)
        current_globals.update(new_globals)
        for key in keys_to_delete:
            del current_globals[key]

    def find_spec(self, name, path, target=None):
        # type: (str, str, object) -> 'ModuleSpec'
        from importlib.util import spec_from_loader

        if name not in self._module_specs:
            module_aliases = {}
            resolution_type, module_path = self.attempt_resolve_local_import(name,
                                                                             self._module_descriptions.keys(),
                                                                             module_aliases)

            if resolution_type == RESOLVED_IMPORT_LEAF_MODULE:
                self._module_specs[name] = spec_from_loader(name, self._module_descriptions[module_path])
            elif resolution_type == RESOLVED_IMPORT_INTERMEDIATE_MODULE:
                self._module_specs[name] = spec_from_loader(name, self._module_descriptions[module_path / '__init__'],
                                                            is_package=True)

        module_spec = self._module_specs.get(name, None)
        if module_spec is not None:
            return module_spec

    def find_module(self, name, path=None):
        # type: (str, str) -> ModuleDescription
        module_aliases = {}
        resolution_type, module_path = self.attempt_resolve_local_import(name, self._module_descriptions.keys(),
                                                                         module_aliases)

        if resolution_type == RESOLVED_IMPORT_LEAF_MODULE:
            return self._module_descriptions[module_path]
        elif resolution_type == RESOLVED_IMPORT_INTERMEDIATE_MODULE:
            return self._module_descriptions[module_path / '__init__']


dli = DynamicLocalImporter({
    'common.commands': ModuleDescription('common.commands', code=PYBUNCH_COMMON_COMMANDS),
    'client.__init__': ModuleDescription('client.__init__', code=PYBUNCH_CLIENT___INIT__),
    'server.symbol_server': ModuleDescription('server.symbol_server', code=PYBUNCH_SERVER_SYMBOL_SERVER),
    'common.dataclass': ModuleDescription('common.dataclass', code=PYBUNCH_COMMON_DATACLASS),
    'common.__init__': ModuleDescription('common.__init__', code=PYBUNCH_COMMON___INIT__),
    'server.__init__': ModuleDescription('server.__init__', code=PYBUNCH_SERVER___INIT__),
    'server.sqlite_symbol_store': ModuleDescription('server.sqlite_symbol_store', code=PYBUNCH_SERVER_SQLITE_SYMBOL_STORE),
    'client.jebsync': ModuleDescription('client.jebsync', code=PYBUNCH_CLIENT_JEBSYNC),
    'server.__main__': ModuleDescription('server.__main__', code=PYBUNCH_SERVER___MAIN__),
    'client.utils': ModuleDescription('client.utils', code=PYBUNCH_CLIENT_UTILS),
    'server.symbol_store': ModuleDescription('server.symbol_store', code=PYBUNCH_SERVER_SYMBOL_STORE),
    'server.default_symbol_server': ModuleDescription('server.default_symbol_server', code=PYBUNCH_SERVER_DEFAULT_SYMBOL_SERVER),
    'client.rename_engine': ModuleDescription('client.rename_engine', code=PYBUNCH_CLIENT_RENAME_ENGINE),
    'server.utils': ModuleDescription('server.utils', code=PYBUNCH_SERVER_UTILS),
    'client.update_listener': ModuleDescription('client.update_listener', code=PYBUNCH_CLIENT_UPDATE_LISTENER),
    'common.consts': ModuleDescription('common.consts', code=PYBUNCH_COMMON_CONSTS),
    'common.symbol': ModuleDescription('common.symbol', code=PYBUNCH_COMMON_SYMBOL),
    'client.rename_listener': ModuleDescription('client.rename_listener', code=PYBUNCH_CLIENT_RENAME_LISTENER),
    'client.sync_to_server': ModuleDescription('client.sync_to_server', code=PYBUNCH_CLIENT_SYNC_TO_SERVER)
})
dli.execute_module('client.jebsync')
