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
        # type: () -> None
        super(_CommandDecoder, self).__init__(object_hook=self.object_hook)
        self._types = {k: v for k, v in globals().items() if isinstance(v, type) and issubclass(v, Dataclass)}

    def object_hook(self, dct):
        if '__type__' in dct:
            typ = dct.pop('__type__')
            if typ not in self._types:
                raise ValueError("Unhandled dynamic type")
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


class ResourceRequest(Command):
    def __init__(self, name):
        self.name = name


class ResourceResponse(Command):
    def __init__(self, name, content):
        self.name = name
        self.content = content


COMMAND_ENCODER = _CommandEncoder()
COMMAND_DECODER = _CommandDecoder()
