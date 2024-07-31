import asyncio
import logging
import socket
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Set

from .utils import recv_packet, send_packet
from common.lazy_dict import LazyDict
from common.symbol import Symbol
from common.symbol_store import SymbolStoreABC
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
        self._stores: LazyDict[str, SymbolStoreABC] = LazyDict(mapping=self._get_store)
        self._clients: Set[Client] = set()
        self._project_associations: Dict[str, Set[Client]] = defaultdict(lambda: set())

    @abstractmethod
    def _get_store(self, project: str) -> SymbolStoreABC:
        raise NotImplementedError

    @staticmethod
    async def push_to_client(client: Client, payload: bytes):
        try:
            await send_packet(client.writer, payload)
        except socket.error:
            logging.debug(f"Connection from {client.writer.get_extra_info('peername')} is closed but not yet cleared")

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
        logging.critical(f"[Connect] New connection from {name} @ {address}")

        client = Client(name, address, reader, writer)

        # Save the connection
        self._clients.add(client)

        while True:
            try:
                packet = await recv_packet(reader)
                command = Command.decode(packet)

                if isinstance(command, Subscribe):
                    logging.info(f"[Subscribe] Request from {name} for project <{command.project}>")
                    client.associated_projects.add(command.project)
                    self._project_associations[command.project].add(client)
                elif isinstance(command, Unsubscribe):
                    logging.info(f"[Unsubscribe] Request from {name} for project <{command.project}>")
                    client.associated_projects.remove(command.project)
                    if client in self._project_associations[command.project]:
                        self._project_associations[command.project].remove(client)
                elif isinstance(command, UpstreamSymbols):
                    store = self._stores[command.project]
                    symbols = command.symbols
                    for symbol in symbols:
                        symbol.author = name

                    # TODO: Is this really needed?
                    # symbols = list(store.changed_symbols(symbols))

                    if command.loggable:
                        for symbol in symbols:
                            logging.info(f"[Symbol] {name} @ {command.project}:"
                                         f" {symbol.canonical_signature} -> {symbol.name}")

                    store.push_symbols(symbols)
                    await self.push_update(command.project, symbols, client)
                elif isinstance(command, FullSyncRequest):
                    logging.info(f"[Full Sync] Request from {name} for project <{command.project}>")
                    store = self._stores[command.project]
                    symbols = list(store.get_symbols())
                    await self.push_symbols(client, command.project, symbols)
            except (ConnectionResetError, asyncio.IncompleteReadError):
                logging.critical(f"[Disconnect] {name} disconnected @ {address}")
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
