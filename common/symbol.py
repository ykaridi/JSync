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
