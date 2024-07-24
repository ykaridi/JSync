from abc import ABC, abstractmethod
from typing import Iterable, Optional

from common.symbol import Symbol


class SymbolStore(ABC):
    def push_symbol(self, symbol: Symbol):
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

    def push_symbols(self, symbols: Iterable[Symbol], only_changed: bool = True):
        raise NotImplementedError

    @abstractmethod
    def get_symbols(self, canonical_signature: Optional[str] = None, author: Optional[str] = None) -> Iterable[Symbol]:
        raise NotImplementedError

    def get_latest_symbols(self, canonical_signature: Optional[str] = None) -> Iterable[Symbol]:
        raise NotImplementedError

    @abstractmethod
    def close(self):
        raise NotImplementedError
