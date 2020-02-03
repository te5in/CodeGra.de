import typing as t
from abc import ABC, abstractmethod

T = t.TypeVar('T')


class Request(ABC, t.Generic[T]):
    @abstractmethod
    def set_request(self, request: T) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_param(self, key: str) -> object:
        raise NotImplementedError
