"""This module implements the mypy plugin needed for the override decorators.

SPDX-License-Identifier: AGPL-3.0-only
"""
from functools import partial

from mypy.nodes import TypeInfo
from mypy.types import Type, CallableType
from mypy.plugin import Plugin, FunctionContext


def _has_method(name: str, cls: TypeInfo) -> bool:
    if name in cls.names:
        return True
    return any(_has_method(name, sub.type) for sub in cls.bases)


def override_callback(ctx: FunctionContext, no_override: bool) -> Type:
    args = ctx.arg_types[0]
    ret = ctx.default_return_type
    if len(args) != 1:
        return ret

    fun = args[0]
    if not isinstance(fun, CallableType) or fun.arg_names[0] not in ('self', 'cls'):
        ctx.api.fail('@override should be applied to method', ctx.context)
        return ret

    if fun.arg_names[0] == 'self':
        cls_type = fun.arg_types[0].type
    else:
        assert fun.arg_names[0] == 'cls'
        cls_type = fun.arg_types[0].item.type

    assert isinstance(cls_type, TypeInfo)

    overrides = any(_has_method(ret.definition.name, base.type) for base in cls_type.bases)
    if no_override and overrides:
        msg = f'The method {fun.name} is defined in a base class of {cls_type.name}'
        ctx.api.fail(msg, ctx.context)
    elif not no_override and not overrides:
        msg = f'The method {fun.name} is not defined in any base class of {cls_type.name}'
        ctx.api.fail(msg, ctx.context)

    return ret


class CgOverridePlugin(Plugin):
    def get_function_hook(self, fullname: str):
        if fullname == 'cg_override.override':
            # We need to return a method that will be called later on by mypy
            return partial(override_callback, no_override=False)
        if fullname == 'cg_override.no_override':
            return partial(override_callback, no_override=True)


def plugin(version: str):
    # ignore version argument if the plugin works with all mypy versions.
    return CgOverridePlugin
