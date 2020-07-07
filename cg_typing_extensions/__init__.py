import typing as t

from typing_extensions import TypedDict

T_DICT = t.TypeVar('T_DICT', bound=dict)


def make_typed_dict_extender(base: t.Any, extends_to: t.Type) -> t.Callable:
    def _extend(**kwargs: t.Any) -> dict:
        kwargs.update(base)
        return kwargs

    return _extend
