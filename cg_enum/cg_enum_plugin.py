"""This module implements the mypy plugin needed for the special ``is_...``
methods

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t
from functools import partial

from mypy.nodes import Var, TypeInfo, MemberExpr
from mypy.types import Type, Instance, LiteralType, PartialType
from mypy.plugin import Plugin, AttributeContext


def _enum_has(enum: t.Any, attr: str) -> bool:
    try:
        return isinstance(enum.names[attr].node, Var)
    except KeyError:
        return False


def analyze_is_method(ctx: AttributeContext) -> Type:
    typ = ctx.type
    assert isinstance(ctx.context, MemberExpr)
    name = ctx.context.name
    enum_value = name[len('is_'):]

    assert isinstance(
        typ,
        Instance,
    ), f'Got strange type: {typ} ({type(typ)})'

    bool_type = ctx.api.named_generic_type('builtins.bool', [])
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
    def get_attribute_hook(
        self, fullname: str
    ) -> t.Optional[t.Callable[[AttributeContext], Type]]:
        if fullname.startswith('cg_enum.CGEnum.is_'):
            return analyze_is_method
        return None


def plugin(version: str) -> t.Type[CgEnumPlugin]:
    # ignore version argument if the plugin works with all mypy versions.
    return CgEnumPlugin
