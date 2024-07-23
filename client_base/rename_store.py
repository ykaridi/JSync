import struct


def read_exactly(stream, amt):
    # type: ('file', int) -> str
    result = ""
    while amt > 0:
        r = stream.read(amt)
        result += r
        amt -= len(r)
    return result


def write_exactly(stream, data):
    # type: ('file', str) -> None
    # Seems like jython always writes fully
    stream.write(data)


def read_struct(stream, fmt):
    # type: ('file', str) -> tuple
    size = struct.calcsize(fmt)
    return struct.unpack(fmt, read_exactly(stream, size))


def read_string(stream):
    # type: ('file') -> str
    size = read_struct(stream, '<I')[0]
    return read_exactly(stream, size)


def write_struct(stream, fmt, *args):
    # type: ('file', str, ...) -> None
    write_exactly(stream, struct.pack(fmt, *args))


def write_string(stream, s):
    # type: ('file', str) -> None
    write_struct(stream, '<I', len(s))
    write_exactly(stream, s)


def load_renames(path):
    with open(path, 'rb') as stream:
        num_renames = read_struct(stream, '<I')[0]
        renames = {}
        for _ in range(num_renames):
            canonical_signature = read_string(stream)
            name = read_string(stream)
            renames[canonical_signature] = name

        return renames


def dump_renames(path, renames):
    with open(path, 'wb') as stream:
        write_struct(stream, "<I", len(renames))
        for canonical_signature, symbol_name in renames.items():
            print(canonical_signature, symbol_name)
            write_string(stream, canonical_signature)
            write_string(stream, symbol_name)
