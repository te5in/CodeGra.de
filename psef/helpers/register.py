"""This module contains all code needed to register classes and functions under
one or more keys.

SPDX-License-Identifier: AGPL-3.0-only
"""

import typing as t
from collections import OrderedDict

T = t.TypeVar('T')  # pylint: disable=invalid-name
V = t.TypeVar('V')  # pylint: disable=invalid-name


class Register(t.Generic[T, V]):  # pylint: disable=unsubscriptable-object
    """Register things under keys using decorators.

    This class can be viewed as a ordered dict, however instead of setting
    things using subscripts it uses decorators.

    >>> reg = Register()
    >>> @reg.register('hello')
    ... def test_func(): pass
    >>> @reg.register_all(['world', 'bye'])
    ... def test_func2(): pass
    >>> reg.get('world') == test_func2
    True
    >>> reg.get('world2') is None
    True
    >>> list(reg.get_all()) == [
    ...     ('hello', test_func),
    ...     ('world', test_func2),
    ...     ('bye', test_func2),
    ... ]
    True
    """

    def __init__(self) -> None:
        self.__map: t.Dict[T, V] = OrderedDict()

    def register(self, key: T) -> t.Callable[[V], V]:
        """A decorator that can be used to register a single key.

        This decorator can be used to register an object with the given key.

        :param key: The key to register.
        :returns: A decorator, it registers the thing applied to this decorator
            under the given key.
        """
        return self.register_all([key])

    def register_all(self, keys: t.Iterable[T]) -> t.Callable[[V], V]:
        """A decorator that can be used to register multiple keys.

        This function is the same as :py:meth:`.Register.register`, the only
        difference is that multiple keys can be given instead of one.

        :param keys: The keys to register.
        :returns: A decorator that registers the given keys.
        """

        def __decorator(cls: V) -> V:
            for key in keys:
                assert key not in self.__map
                self.__map[key] = cls
            return cls

        return __decorator

    def get(self, key: T) -> t.Optional[V]:
        return self.__map.get(key)

    def __getitem__(self, key: T) -> V:
        return self.__map[key]

    def get_all(self) -> t.Iterable[t.Tuple[T, V]]:
        return self.__map.items()

    def get_key(self, obj: V) -> t.Optional[T]:
        """Get one of the keys mapping to the given object.

        :param obj: Object to match the key with.
        :returns: A key corresponding to the given object, or ``None`` if no
            matching object is found. There may be more than one key, the first
            one matching the object will be returned.

        >>> reg = Register()
        >>> @reg.register('hello')
        ... def test_func(): pass
        >>> reg.get_key(test_func)
        'hello'
        >>> def test_func2(): pass
        >>> reg.get_key(test_func2) is None
        True
        """
        for key, value in self.__map.items():
            if obj == value:
                return key

        return None
