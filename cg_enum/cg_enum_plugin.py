"""This module implements the mypy plugin needed for the special ``is_...``
methods

SPDX-License-Identifier: AGPL-3.0-only
"""
from functools import partial

from mypy.nodes import Var, TypeInfo
from mypy.types import (
    Type, Instance, LiteralType, CallableType, get_proper_type
)
from mypy.plugin import Plugin, AttributeContext


def _enum_has(enum, attr: str):
    try:
        return isinstance(enum.names[attr].node, Var)
    except KeyError:
        return False


def analyze_is_method(ctx: AttributeContext):
    typ = ctx.type
    name = ctx.context.name
    enum_value = name[len('is_'):]

    bool_type = ctx.api.named_generic_type('builtins.bool', [])
    if isinstance(typ, Instance):
        last_known_value = typ.last_known_value
        if isinstance(last_known_value, LiteralType):
            is_value = last_known_value.value == enum_value
            enum_type = last_known_value.fallback.type
            if not is_value and not _enum_has(enum_type, enum_value):
                ctx.api.fail((
                    f'The enum {enum_type.name} has no attribute "{name}" as'
                    f' the enum has no member "{enum_value}"'
                ), ctx.context)
            literal_type = LiteralType(is_value, fallback=bool_type)
            return bool_type.copy_modified(last_known_value=literal_type)

    enum_type = typ.type
    if not _enum_has(enum_type, enum_value):
        ctx.api.fail((
            f'The enum {enum_type.name} has no attribute "{name}" as the enum'
            f' has no member "{enum_value}"'
        ), ctx.context)

    return bool_type


class CgEnumPlugin(Plugin):
    def get_attribute_hook(self, fullname: str):
        if fullname.startswith('cg_enum.CGEnum.is_'):
            return analyze_is_method


def plugin(version: str):
    # ignore version argument if the plugin works with all mypy versions.
    return CgEnumPlugin
