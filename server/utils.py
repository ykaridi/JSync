import struct
import asyncio
from common.consts import PACKET_SIZE_FORMAT


async def recv_packet(reader: asyncio.StreamReader) -> bytes:
    size = struct.unpack(PACKET_SIZE_FORMAT, await reader.readexactly(struct.calcsize(PACKET_SIZE_FORMAT)))[0]
    return await reader.readexactly(size)


async def send_packet(writer: asyncio.StreamWriter, data: bytes):
    writer.write(struct.pack(PACKET_SIZE_FORMAT, len(data)))
    writer.write(data)
    await writer.drain()
