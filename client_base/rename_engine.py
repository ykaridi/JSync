import os
from abc import ABCMeta, abstractmethod
from threading import Lock

from client_base.config import JSYNC_ROOT
from common.symbol import Symbol
from common.lazy_dict import LazyDict
from client_base.client_symbol_store import ClientSymbolStoreABC


def evaluate_symbol(symbols, self_author):
    return max(symbols, key=lambda s: s.timestamp)


def get_symbol_evaluator():
    # type: () -> evaluate_symbol
    symbol_evaluator_file = os.path.join(JSYNC_ROOT, 'symbol_evaluator.py')
    if os.path.exists(symbol_evaluator_file):
        dct = {}
        with open(symbol_evaluator_file, 'r') as f:
            exec(f.read(), dct, dct)

        return dct['evaluate_symbol']
    else:
        return evaluate_symbol


class RenameEngineABC(object):
    __metaclass__ = ABCMeta

    def __init__(self, self_author):
        # type: (str) -> None
        self._self_author = self_author
        self._symbol_stores = LazyDict(lambda project:
                                       self.get_client_symbol_store(project))  # type: dict[str, ClientSymbolStoreABC]
        self._dirty_symbols = {}  # type: dict[str, set[Symbol]]
        self._records_lock = Lock()

        self._symbol_evaluator = get_symbol_evaluator()  # type: evaluate_symbol

    @property
    def self_author(self):
        # type: () -> str
        return self._self_author

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

    def get_symbol_latest_known_rename(self, project, symbol):
        # type: (str, Symbol) -> str
        symbol = self._symbol_stores[project].get_latest_known_rename(symbol.canonical_signature)
        return None if symbol is None else symbol.name

    def get_latest_known_renames(self, project):
        # type: (str) -> iter[Symbol]
        return self._symbol_stores[project].latest_known_renames.values()

    def is_symbol_rename_known(self, project, symbol, is_renamed):
        # type: (str, Symbol, bool) -> bool
        latest_rename = self.get_symbol_latest_known_rename(project, symbol)
        return ((not is_renamed) and latest_rename is None) or (is_renamed and latest_rename == symbol.name)

    def record_latest_known_renames(self, project, symbols):
        # type: (str, list[Symbol]) -> None
        symbols = [
            symbol if symbol.name is not None and symbol.name != self.get_original_name(project, symbol)
            else symbol.named(None)
            for symbol in symbols
        ]
        with self._records_lock:
            self._symbol_stores[project].record_latest_known_renames(symbols)

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
            return symbol.stripped.named(self.get_original_name(project, symbol))

        return self._symbol_evaluator(symbols, self.self_author)

    def flush_symbol(self, project, symbol):
        # type: (str, Symbol) -> None
        _symbol = self.evaluate_symbol(project, symbol.stripped)
        if symbol.canonical_signature != _symbol.canonical_signature:
            raise EnvironmentError("Symbol Evaluator is inconsistent - changes canonical signature!")

        symbol = _symbol

        old_name = self.get_symbol_latest_known_rename(project, symbol)
        self.record_latest_known_renames(project, [symbol])
        if not self._enqueue_rename(project, symbol):
            self.record_latest_known_renames(project, [symbol.named(old_name)])

        self._dirty_symbols.setdefault(project, set()).remove(symbol.stripped)

    def flush_all_symbols(self):
        for project, dirty_symbols in self._dirty_symbols.items():
            for dirty_symbol in list(dirty_symbols):
                self.flush_symbol(project, dirty_symbol)

    @abstractmethod
    def _enqueue_rename(self, project, symbol):
        # type: (str, Symbol) -> bool
        raise NotImplementedError

    def set_metadata_property(self, project, prop, value):
        # type: (str, str, str) -> None
        self._symbol_stores[project].set_metadata_property(prop, value)

    def get_metadata_property(self, project, prop):
        # type: (str, str) -> str | None
        return self._symbol_stores[project].get_metadata_property(prop)
