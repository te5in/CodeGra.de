import typing as t
from abc import ABC, abstractmethod


class CookieService(ABC):
    _cookie_prefix: str

    @abstractmethod
    def get_cookie(self, name: str) -> t.Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def set_cookie(self, name: str, value: str, exp: int = 3600) -> None:
        raise NotImplementedError
