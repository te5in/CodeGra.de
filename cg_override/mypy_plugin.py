from functools import partial

from mypy.nodes import TypeInfo
from mypy.types import Type, CallableType
from mypy.plugin import Plugin, FunctionContext, AttributeContext


def _has_method(name: str, cls: TypeInfo) -> bool:
    if name in cls.names:
        return True
    return any(_has_method(name, sub.type) for sub in cls.bases)


def override_callback(ctx: FunctionContext) -> Type:
    args = ctx.arg_types[0]
    ret = ctx.default_return_type
    if len(args) != 1:
        return ret

    fun = args[0]
    if not isinstance(fun, CallableType) or fun.arg_names[0] != 'self':
        ctx.api.fail('@override should be applied to method', ctx.context)
        return ret

    cls_type = fun.arg_types[0].type

    if not any(
        _has_method(ret.definition.name, base.type) for base in cls_type.bases
    ):
        msg = f'The method {fun.name} is not defined in any base class of {cls_type.name}'
        ctx.api.fail(msg, ctx.context)
    return ret


class CgOverridePlugin(Plugin):
    def get_function_hook(self, fullname: str):
        if fullname == 'cg_override.override':
            # We need to return a method that will be called later on by mypy
            return override_callback


def plugin(version: str):
    # ignore version argument if the plugin works with all mypy versions.
    return CgOverridePlugin
