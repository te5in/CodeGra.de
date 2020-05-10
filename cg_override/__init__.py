"""A module containing an override decorator.
"""
import typing as t

from typing_extensions import Final

T = t.TypeVar('T', bound=t.Callable)


def override(fun: T) -> T:
    """Indicate that this method overrides a method from a base class.

    This decorator doesn't introduce any runtime checks, but a accompanying
    mypy plugin does check it.

    :param fun: The function that is an override of a base class, this argument
        is simply returned.
    """
    return fun
