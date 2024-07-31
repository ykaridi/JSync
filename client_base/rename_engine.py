from abc import ABCMeta, abstractmethod
from threading import Lock

from common.symbol import Symbol
from common.lazy_dict import LazyDict
from client_base.client_symbol_store import ClientSymbolStoreABC


class RenameEngineABC(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        # type: () -> None
        self._symbol_stores = LazyDict(lambda project:
                                       self.get_client_symbol_store(project))  # type: dict[str, ClientSymbolStoreABC]
        self._dirty_symbols = {}  # type: dict[str, set[Symbol]]
        self._records_lock = Lock()

    @abstractmethod
    def get_client_symbol_store(self, project):
        # type: (str) -> ClientSymbolStoreABC
        raise NotImplementedError

    @abstractmethod
    def get_name(self, project, symbol):
        # type: (str, Symbol) -> str
        raise NotImplementedError

    @abstractmethod
    def get_original_name(self, project, symbol):
        # type: (str, Symbol) -> str
        raise NotImplementedError

    def get_symbol_latest_rename(self, project, symbol):
        # type: (str, Symbol) -> str
        return self._symbol_stores[project].get_latest_rename(symbol.canonical_signature)

    def is_symbol_synced(self, project, symbol, is_renamed):
        # type: (str, Symbol, bool) -> bool
        latest_rename = self.get_symbol_latest_rename(project, symbol)
        return ((not is_renamed) and latest_rename is None) or (is_renamed and latest_rename == symbol.name)

    def record_rename(self, project, symbol):
        # type: (str, Symbol) -> None
        with self._records_lock:
            self._symbol_stores[project].record_rename(symbol.canonical_signature, symbol.name)

    def record_symbols(self, project, symbols, dirty=True):
        # type: (str, list[Symbol], bool) -> None
        symbols = symbols if isinstance(symbols, list) else list(symbols)

        deleted_symbols = []
        changed_symbols = []
        for symbol in symbols:
            original_name = self.get_original_name(project, symbol)
            if symbol.name == original_name or symbol.name is None:
                deleted_symbols.append(symbol)
            else:
                changed_symbols.append(symbol)

        if changed_symbols:
            self._symbol_stores[project].push_symbols(changed_symbols)
        if deleted_symbols:
            self._symbol_stores[project].delete_symbols(deleted_symbols)

        if dirty:
            self._dirty_symbols.setdefault(project, set()).update(symbol.stripped for symbol in symbols)

    def evaluate_symbol(self, project, symbol):
        # type: (str, Symbol) -> Symbol
        symbols = list(self._symbol_stores[project].get_symbols(canonical_signature=symbol.canonical_signature))
        if len(symbols) == 0:
            return symbol.stripped.clone(name=self.get_original_name(project, symbol))

        # TODO: Add plugin execution, allowing even to modify symbol
        return max(symbols, key=lambda s: s.timestamp)

    def flush_symbol(self, project, symbol):
        # type: (str, Symbol) -> None
        symbol = self.evaluate_symbol(project, symbol.stripped)

        old_name = self.get_symbol_latest_rename(project, symbol)
        self.record_rename(project, symbol)
        if not self._enqueue_rename(project, symbol):
            self.record_rename(project, symbol.clone(name=old_name))

        self._dirty_symbols.setdefault(project, set()).remove(symbol.stripped)

    def flush_symbols(self):
        for project, dirty_symbols in self._dirty_symbols.items():
            for dirty_symbol in list(dirty_symbols):
                self.flush_symbol(project, dirty_symbol)

    @abstractmethod
    def _enqueue_rename(self, project, symbol):
        # type: (str, Symbol) -> bool
        raise NotImplementedError
