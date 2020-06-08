"""A module containing an override decorator.

.. todo::

    Currently it is not possible to specify which class you expect to be
    overriding. It would be very useful to add this in the future.

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t

T = t.TypeVar('T', bound=t.Callable)


def override(fun: T) -> T:
    """Indicate that this method overrides a method from a base class.

    This decorator doesn't introduce any runtime checks, but a accompanying
    mypy plugin does check it.

    :param fun: The function that is an override of a base class, this argument
        is simply returned.
    """
    return fun


def no_override(fun: T) -> T:
    """Indicate that this method does **not** override a method from a base
        class.

    This decorator doesn't introduce any runtime checks, but a accompanying
    mypy plugin does check it.

    :param fun: The function that is **not** an override of a base class, this
        argument is simply returned.
    """
    return fun
