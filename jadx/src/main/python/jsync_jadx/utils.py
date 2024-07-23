import hashlib
import re

from jadx.api.plugins import JadxPluginContext
from jadx.core.dex.nodes import ClassNode, MethodNode, FieldNode
from jadx.core.codegen import TypeGen
from jadx.plugins.input.dex.sections import DexClassData
from jadx.plugins.input.dex import DexReader
from jadx.core.dex.attributes import AType


from common.symbol import Symbol, SYMBOL_TYPE_CLASS, SYMBOL_TYPE_METHOD, SYMBOL_TYPE_FIELD


# id(DexReader) -> str
CACHED_IDENTIFIERS = {}

_in_field = DexClassData.getDeclaredField('in')
_in_field.setAccessible(True)


def get_name(node):
    # type: (ClassNode | MethodNode | FieldNode) -> str
    if isinstance(node, ClassNode):
        return node.shortName
    elif isinstance(node, MethodNode):
        return node.name
    elif isinstance(node, FieldNode):
        return node.name
    else:
        raise ValueError("Unknown node type")


def encode_symbol(node):
    # type: (ClassNode | MethodNode | FieldNode) -> Symbol
    if isinstance(node, ClassNode):
        return Symbol(SYMBOL_TYPE_CLASS,
                      TypeGen.signature(node.classInfo.type),
                      node.alias)
    elif isinstance(node, MethodNode):
        return Symbol(SYMBOL_TYPE_METHOD,
                      TypeGen.signature(node.parentClass.classInfo.type) + "->" + node.methodInfo.shortId,
                      node.alias)
    elif isinstance(node, FieldNode):
        return Symbol(SYMBOL_TYPE_FIELD,
                      TypeGen.signature(node.parentClass.classInfo.type) + "->" + node.fieldInfo.shortId,
                      node.alias)
    else:
        raise ValueError("Unknown node type")


def project_id(obj):
    # type: (DexReader | ClassNode | MethodNode | FieldNode) -> str
    if isinstance(obj, (ClassNode, MethodNode, FieldNode)):
        if isinstance(obj, (MethodNode, FieldNode)):
            cls = obj.parentClass
        elif isinstance(obj, ClassNode):
            cls = obj

        class_data = cls.clsData
        if not isinstance(class_data, DexClassData):
            raise ValueError("Only DEX files are currently supported")

        dex_reader = _in_field.get(class_data).dexReader
    elif isinstance(obj, DexReader):
        dex_reader = obj
    else:
        raise ValueError("Unknown code item")

    internal_id = id(dex_reader)
    if internal_id not in CACHED_IDENTIFIERS:
        data = dex_reader.buf.array()
        CACHED_IDENTIFIERS[internal_id] = hashlib.md5(data).hexdigest()

    return CACHED_IDENTIFIERS[internal_id]


def _get_node(context, symbol):
    # type: (JadxPluginContext, Symbol) -> ClassNode | MethodNode | FieldNode | None
    signature = symbol.canonical_signature
    match = re.match(r"^L(?P<name>[a-zA-Z0-9_$/]+);(->(?P<mf_id>.*))?$", signature)
    if not match:
        # Invalid signature: invalid class name
        return None

    name = match.group('name').replace('/', '.')
    cls = context.decompiler.searchClassNodeByOrigFullName(name)
    if not cls:
        # Invalid signature: unmatched class
        return None

    if symbol.symbol_type == SYMBOL_TYPE_CLASS:
        return cls
    elif symbol.symbol_type in [SYMBOL_TYPE_METHOD, SYMBOL_TYPE_FIELD]:
        mf_id = match.group('mf_id')
        if not mf_id:
            # Invalid signature invalid method/field short id
            return None

        if symbol.symbol_type == SYMBOL_TYPE_METHOD:
            r = cls.searchMethodByShortId(mf_id)
            if not r:
                # Invalid signature: unmatched method
                return None

            return r
        elif symbol.symbol_type == SYMBOL_TYPE_FIELD:
            r = cls.searchFieldByShortId(mf_id)
            if not r:
                # Invalid signature: unmatched field
                return None

            return r
    else:
        # Invalid signature: unknown symbol type
        return None


def get_node(context, project, symbol):
    # type: (JadxPluginContext, str, Symbol) -> ClassNode | MethodNode | FieldNode | None
    node = _get_node(context, symbol)
    if node is None:
        return None

    if project_id(node) == project:
        return node
    else:
        return None


def method_is_override(method):
    # type: (MethodNode) -> bool
    override_attr = method.get(AType.METHOD_OVERRIDE)
    if override_attr is None:
        return False

    return not override_attr.baseMethods.empty


def get_base_methods(method):
    # type: (MethodNode) -> list[MethodNode]
    override_attr = method.get(AType.METHOD_OVERRIDE)
    if override_attr is None:
        return [method]

    return override_attr.baseMethods