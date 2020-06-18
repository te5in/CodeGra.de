"""This module implements generic helpers and convenience functions.

These helper functions should ideally all be pure(ish) functions that do not
depend a database choice or flask.

SPDX-License-Identifier: AGPL-3.0-only
"""
import enum
import typing as t

T = t.TypeVar('T')
Y = t.TypeVar('Y')

__all__ = ['handle_none']


def handle_none(value: t.Optional[T], default: Y) -> t.Union[T, Y]:
    """Get the given ``value`` or ``default`` if ``value`` is ``None``.

    >>> handle_none(None, 5)
    5
    >>> handle_none(5, 6)
    5
    >>> handle_none(5.5, 6)
    5.5
    """
    return default if value is None else value


def assert_never(x: t.NoReturn, of_enum: t.Type[enum.Enum]) -> t.NoReturn:
    """Assert that the value ``x`` never exists according to mypy.

    This allows you to enforce that you do an exhaustive check for an enum:

    >>> import enum
    >>> class MyEnum(enum.Enum):
    ...  a = 1
    ...  b = 2
    >>> var: MyEnum = MyEnum.a
    >>> if var is MyEnum.a:
    ...  pass
    ... elif var is MyEnum.b:
    ...  pass
    ... else:
    ...  assert_never(var, MyEnum)

    :param x: The value that should never exist

    :raises AssertionError: This function always raises an assertion error.
    """
    raise AssertionError(
        'Unhandled value "{}" for Enum "{}"'.format(x, of_enum.__name__)
    )
