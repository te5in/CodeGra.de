"""This module implements generic helpers and convenience functions.

These helper functions should ideally all be pure(ish) functions that do not
depend a database choice or flask.

SPDX-License-Identifier: AGPL-3.0-only
"""
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
