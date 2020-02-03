import typing as t
from abc import ABC, abstractmethod

from .deployment import Deployment
from .registration import Registration


class ToolConfAbstract(ABC):
    @abstractmethod
    def find_registration_by_issuer(self, iss: str) -> Registration:
        raise NotImplementedError

    @abstractmethod
    def find_deployment(self, iss: str,
                        deployment_id: str) -> t.Optional[Deployment]:
        raise NotImplementedError


class ToolConfDict(ToolConfAbstract):
    def __init__(self, json_data: t.Mapping[str, object]) -> None:
        ...

    def find_registration_by_issuer(self, iss: str) -> Registration:
        ...

    def find_deployment(self, iss: str,
                        deployment_id: str) -> t.Optional[Deployment]:
        ...

    def set_private_key(self, iss: str, key_content: str) -> None:
        ...

    def get_private_key(self, iss: str) -> str:
        ...


class ToolConfJsonFile(ToolConfDict):
    def __init__(self, config_file: str) -> None:
        ...
