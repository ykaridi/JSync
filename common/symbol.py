from .dataclass import Dataclass


SYMBOL_TYPE_FIELD = 0
SYMBOL_TYPE_METHOD = 1
SYMBOL_TYPE_CLASS = 2


class Symbol(Dataclass):
    def __init__(self, symbol_type, canonical_signature, name, timestamp=None, author=None):
        # type: (int, str, str, int, str) -> None
        self.symbol_type = symbol_type  # type: int
        self.canonical_signature = canonical_signature  # type: str
        self.name = name  # type: str
        self.timestamp = timestamp  # type: int
        self.author = author  # type: str

    @property
    def as_tuple(self):
        return self.symbol_type, self.canonical_signature, self.name, self.timestamp, self.author

    @property
    def stripped(self):
        return Symbol(self.symbol_type, self.canonical_signature, None)

    def __hash__(self):
        return hash(self.as_tuple)

    def __eq__(self, other):
        return isinstance(other, Symbol) and self.as_tuple == other.as_tuple
