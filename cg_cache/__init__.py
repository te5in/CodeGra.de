import abc
import enum
import json
import typing as t
from datetime import timedelta

import redis
import structlog

logger = structlog.get_logger()


class NotSetType(enum.Enum):
    token = '__CG_CACHE_UNSET__'


T = t.TypeVar('T')
Y = t.TypeVar('Y')


class Backend(abc.ABC, t.Generic[T]):
    def __init__(self, namespace: str, ttl: timedelta) -> None:
        self._namespace = namespace
        self._ttl = ttl

    def _make_key(self, key: str) -> str:
        return f'{self._namespace}/{key}'

    @abc.abstractmethod
    def get(self, key: str) -> T:
        raise NotImplementedError

    @abc.abstractmethod
    def get_or(self, key: str, dflt: Y) -> t.Union[T, Y]:
        raise NotImplementedError

    @abc.abstractmethod
    def set(self, key: str, value: T) -> None:
        raise NotImplementedError

    def get_or_set(
        self, key: str, get_value: t.Callable[[], T]
    ) -> T:
        found = self.get_or(key, NotSetType.token)
        if found is NotSetType.token:
            found = get_value()
            self.set(key, found)
        else:
            logger.info('Found key in cache', key=key)
        return found


class RedisBackend(Backend[T], t.Generic[T]):
    def __init__(self, namespace: str, ttl: timedelta, redis: redis.Redis) -> None:
        super().__init__(namespace=namespace, ttl=ttl)
        self._redis = redis

    def get(self, key: str) -> T:
        found = self._redis.get(self._make_key(key))

        if found is None:
            raise KeyError(key)

        return json.loads(found)

    def get_or(self, key: str, dflt: Y) -> t.Union[T, Y]:
        found = self._redis.get(self._make_key(key))
        if found is None:
            return dflt
        return json.loads(found)

    def set(self, key: str, value: T) -> None:
        self._redis.set(
            name=self._make_key(key),
            value=json.dumps(value),
            px=round(self._ttl.total_seconds() * 1000),
        )
