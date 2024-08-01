import hashlib

from com.pnfsoftware.jeb.core.units.code.android.dex import IDexMethod, IDexClass, IDexField, IDexType
from com.pnfsoftware.jeb.core.actions import Actions, ActionContext, ActionOverridesData
from com.pnfsoftware.jeb.core.units.code.android import IDexFile

from common.symbol import Symbol, SYMBOL_TYPE_FIELD, SYMBOL_TYPE_METHOD, SYMBOL_TYPE_CLASS


# dex_unit.uid -> typ.getSignature(False) -> method.getName(False) -> method
TYPE_METHOD_MAPPING = {}  # type: dict[int, dict[str, dict[str, IDexMethod]]]
# id(IDexFile) -> str
CACHED_IDENTIFIERS = {}


def project_id(item):
    # type: (IDexMethod | IDexClass | IDexField | IDexType | IDexFile) -> str
    if isinstance(item, IDexFile):
        dex_file = item
    elif isinstance(item, (IDexMethod, IDexField, IDexClass)):
        if isinstance(item, (IDexMethod, IDexField)):
            dex_file_index = item.data.dexFileIndex
        elif isinstance(item, IDexClass):
            dex_file_index = item.dexFileIndex

        if dex_file_index < 0:
            raise ValueError("Invalid dex file index. Is project JDB2 from jeb version < 5.13?")
        dex_file = item.dex.getDexFile(dex_file_index)
    else:
        raise TypeError("Unexpected %s encountered" % type(item))

    internal_id = id(dex_file)
    if internal_id not in CACHED_IDENTIFIERS:
        CACHED_IDENTIFIERS[internal_id] = hashlib.md5(dex_file.data).hexdigest()
    return CACHED_IDENTIFIERS[internal_id]


def method_is_override(method):
    # type: (IDexMethod) -> bool
    data = ActionOverridesData()
    unit = method.dex
    if unit.prepareExecution(ActionContext(unit, Actions.QUERY_OVERRIDES, method.itemId, None), data):
        return len(data.parents) > 0

    return False


def is_internal(item):
    # type: (IDexClass | IDexMethod | IDexField | IDexType) -> bool
    if isinstance(item, IDexClass):
        return True
    else:
        return item.internal


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
