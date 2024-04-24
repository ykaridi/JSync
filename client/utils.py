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
    byts = jarray.zeros(amt, "b")
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
