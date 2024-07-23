import struct

import jarray
from java.io import DataInputStream, BufferedOutputStream
from java.net import Socket
from org.python.core.util import StringUtil
from java.net import SocketException

from client_base.connection import ConnectionABC, ConnectionError
from common.consts import PACKET_SIZE_FORMAT


class JavaConnection(ConnectionABC):
    def __init__(self, sock):
        # type: (Socket) -> None
        self._socket = sock
        self._active = True

    @property
    def active(self):
        # type: () -> bool
        return self._active

    def _recv_fully(self, amt):
        # type: (int) -> bytes
        try:
            input_stream = DataInputStream(self._socket.inputStream)
            byts = jarray.zeros(amt, "b")
            input_stream.readFully(byts)
            return StringUtil.fromBytes(byts)
        except SocketException:
            self.close(on_exception=True)
            raise ConnectionError()

    def recv_packet(self):
        # type: () -> bytes
        x = self._recv_fully(struct.calcsize(PACKET_SIZE_FORMAT))
        size = struct.unpack(PACKET_SIZE_FORMAT, x)[0]
        return self._recv_fully(size)

    def _send_fully(self, data):
        # type: (Socket, bytes) -> None
        try:
            out = BufferedOutputStream(self._socket.getOutputStream())
            out.write(data)
            out.flush()
        except SocketException:
            self.close(on_exception=True)
            raise ConnectionError()

    def send_packet(self, data):
        # type: (Socket, bytes) -> None
        self._send_fully(struct.pack(PACKET_SIZE_FORMAT, len(data)))
        self._send_fully(data)

    def close(self, on_exception=False):
        # type: (bool) -> None
        if self._active:
            self._socket.close()
        self._active = False
