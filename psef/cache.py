"""This module contains functionality to cache functions during a request.

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t
from functools import wraps

import structlog
from flask import g

T = t.TypeVar('T', bound=t.Callable)

logger = structlog.get_logger()


def init_app(app: t.Any) -> None:
    """Init the cache for the given app.
    """

    @app.before_request
    def __create_caches() -> None:  # pylint: disable=unused-variable
        g.cache_misses = 0
        g.cache_hits = 0
        g.psef_function_cache = {}

    @app.after_request
    def __clear_caches(res: T) -> T:  # pylint: disable=unused-variable
        g.psef_function_cache = {}
        return res


_KWARGS_MARK = object()


def _make_key(args: t.Tuple[object, ...],
              kwargs: t.Dict[str, object]) -> t.Tuple[object, ...]:
    """Make a cache key.

    >>> _make_key(('a', 'b'), {'c': 'd'})
    ('a', 'b', <object object at 0x...>, 'c', 'd')

    :param args: The args of the call.
    :param args: The kwargs of the call.
    :returns: A cache
    """
    res = args

    for item in sorted(kwargs.items()):
        res += (_KWARGS_MARK, *item)

    return res


def cache_within_request(f: T) -> T:
    """Decorator to cache the given function during the request.

    All calls to ``f`` during a single request with the same parameters will be
    cached/memoized. This is done based on the ``*args`` and ``**kwargs`` it
    receives, which all need to be hashable. For the same arguments the
    function will be only called once during the request.

    :param f: The function to cache.
    :returns: A wrapped version of ``f`` that is cached.
    """
    master_key = object()

    @wraps(f)
    def __decorated(*args: t.Any, **kwargs: t.Any) -> t.Any:
        if not hasattr(g, 'psef_function_cache'):  # pragma: no cover
            # Never error because of this decorator
            return f(*args, **kwargs)
        if master_key not in g.psef_function_cache:
            g.psef_function_cache[master_key] = {}

        key = _make_key(args, kwargs)

        if key not in g.psef_function_cache[master_key]:
            g.psef_function_cache[master_key][key] = f(*args, **kwargs)
            g.cache_misses += 1
        else:
            g.cache_hits += 1
        return g.psef_function_cache[master_key][key]

    def clear_cache() -> None:  # pragma: no cover
        g.psef_function_cache[master_key] = {}

    __decorated.clear_cache = clear_cache  # type: ignore

    return t.cast(T, __decorated)
