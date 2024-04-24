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
