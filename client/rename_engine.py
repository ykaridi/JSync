from com.pnfsoftware.jeb.core.units.code.android import IDexUnit
from com.pnfsoftware.jeb.core.units.code.android.dex import IDexItem, IDexField, IDexMethod, IDexClass
from com.pnfsoftware.jeb.core.units import IMetadataManager, MetadataGroup, MetadataGroupType

from threading import Lock
from common.symbol import Symbol, SYMBOL_TYPE_FIELD, SYMBOL_TYPE_METHOD, SYMBOL_TYPE_CLASS


METADATA_GROUP_NAME = 'JEBSync'


class RenameEngine(object):
    def __init__(self):
        # type: () -> None
        self._lock = Lock()

    @property
    def locked(self):
        return self._lock.locked()

    @staticmethod
    def _metadata_group(dex_unit):
        # type: (IDexUnit) -> MetadataGroup
        metadata_manager = dex_unit.metadataManager  # type: IMetadataManager
        if metadata_manager.getGroupByName(METADATA_GROUP_NAME) is None:
            metadata_manager.addGroup(MetadataGroup(METADATA_GROUP_NAME, MetadataGroupType.STRING))

        return metadata_manager.getGroupByName(METADATA_GROUP_NAME)

    def is_original_symbol(self, item):
        # type: (IDexItem) -> bool
        metadata_group = self._metadata_group(item.dex)
        data = metadata_group.getData(item.getSignature(False))
        return data != item.getName(True)

    def update_item_metadata(self, item):
        self._metadata_group(item.dex).setData(item.getSignature(False), item.getName(True))

    def enqueue_rename(self, unit, symbol):
        # type: (IDexUnit, Symbol) -> None
        item = None  # type: IDexItem
        if symbol.symbol_type == SYMBOL_TYPE_FIELD:
            item = unit.getField(symbol.canonical_signature)
        elif symbol.symbol_type == SYMBOL_TYPE_METHOD:
            item = unit.getMethod(symbol.canonical_signature)
        elif symbol.symbol_type == SYMBOL_TYPE_CLASS:
            item = unit.getClass(symbol.canonical_signature)

        if item is None:
            return

        with self._lock:
            if item.getName(True) != symbol.name:
                item.setName(symbol.name)

        self.update_item_metadata(item)
