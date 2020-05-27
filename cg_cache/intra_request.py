"""This module contains functionality to cache functions during a request.

SPDX-License-Identifier: AGPL-3.0-only
"""
import uuid
import typing as t
from functools import wraps
from collections import defaultdict

import structlog
from flask import Flask, g
from typing_extensions import Protocol

from cg_sqlalchemy_helpers.types import ColumnProxy


class ObjectWithId(Protocol):
    id: ColumnProxy[uuid.UUID]


T = t.TypeVar('T', bound=t.Callable)
T_OBJECT_WITH_ID = t.TypeVar('T_OBJECT_WITH_ID', bound=ObjectWithId)  # pylint: disable=invalid-name
Y = t.TypeVar('Y')
Z = t.TypeVar('Z')


def _get_id_of_object(obj: T_OBJECT_WITH_ID) -> t.Tuple[uuid.UUID]:
    return (obj.id, )


logger = structlog.get_logger()


def _set_g_vars() -> None:
    g.cache_misses = 0
    g.cache_hits = 0
    g.cg_function_cache = defaultdict(dict)


def _clear_g_vars(value: Y) -> Y:
    _set_g_vars()
    return value


def init_app(app: Flask) -> None:
    """Init the cache for the given app.
    """
    app.before_request(_set_g_vars)
    # Clear vars after request so that the values in ``cg_function_cache`` can
    # be garbage collected.
    app.after_request(_clear_g_vars)


_KWARGS_MARK = object()


def _make_key(args: t.Tuple[object, ...],
              kwargs: t.Dict[str, object]) -> t.Tuple[object, ...]:
    """Make a cache key.

    >>> key1 = _make_key(('a', 'b'), {'c': 'd'})
    >>> key2 = _make_key(('a', 'b'), {'c': 'd'})
    >>> key3 = _make_key(('a', 'b', 'd'), {})
    >>> key4 = _make_key(('a', ), {'b': 'b', 'c': 'd'})
    >>> key1 == key2
    True
    >>> key1 == key3
    False
    >>> key1 == key4
    False

    :param args: The args of the call.
    :param args: The kwargs of the call.
    :returns: A cache
    """
    res = args

    for item in sorted(kwargs.items()):
        res += (_KWARGS_MARK, *item)

    return res


def _cache_or_call(
    master_key: object,
    key: t.Tuple[object, ...],
    fun: t.Callable,
    args: t.Tuple,
    kwargs: t.Dict,
) -> t.Any:
    try:
        if not hasattr(g, 'cg_function_cache'):
            _set_g_vars()
    except:  # pylint: disable=bare-except
        # Never error because of this decorator
        return fun(*args, **kwargs)

    if key in g.cg_function_cache[master_key]:
        g.cache_hits += 1
    else:
        g.cg_function_cache[master_key][key] = fun(*args, **kwargs)
        g.cache_misses += 1

    return g.cg_function_cache[master_key][key]


def cache_within_request_make_key(
    make_key: t.Callable[[Y], t.Tuple[object, ...]]
) -> t.Callable[[t.Callable[[Y], Z]], t.Callable[[Y], Z]]:
    """Just like :func:`.cache_within_request` but with an explicit key.

    :param make_key: The method that should return the key used for caching.
    """

    def __wrapper(fun: t.Callable[[Y], Z]) -> t.Callable[[Y], Z]:
        master_key = object()

        @wraps(fun)
        def __inner(arg: Y) -> Z:
            key = make_key(arg)
            return _cache_or_call(master_key, key, fun, (arg, ), {})

        return __inner

    return __wrapper


def cache_within_request(f: T) -> T:
    """Decorator to cache the given function during the request.

    All calls to ``f`` during a single request with the same parameters will be
    cached/memoized. This is done based on the ``*args`` and ``**kwargs`` it
    receives, which all need to be hashable. For the same arguments the
    function will be only called once during the request.

    This decorator can also be used outside of flask, in which case it WILL NOT
    cache anything.

    >>> p = cache_within_request(lambda: print('Hello'))
    >>> p()
    Hello
    >>> p()
    Hello

    :param f: The function to cache.
    :returns: A wrapped version of ``f`` that is cached.
    """
    master_key = object()

    @wraps(f)
    def __decorated(*args: t.Any, **kwargs: t.Any) -> t.Any:
        key = _make_key(args, kwargs)
        return _cache_or_call(master_key, key, f, args, kwargs)

    def clear_cache() -> None:  # pragma: no cover
        g.cg_function_cache[master_key] = {}

    __decorated.clear_cache = clear_cache  # type: ignore

    return t.cast(T, __decorated)


def cache_for_object_id(f: t.Callable[[T_OBJECT_WITH_ID], Y]
                        ) -> t.Callable[[T_OBJECT_WITH_ID], Y]:
    """Cache a method of an SQLAlchemy object using its ``id`` as key.

    For now it is only possible to cache methods that take no arguments.
    """
    return cache_within_request_make_key(_get_id_of_object)(f)
