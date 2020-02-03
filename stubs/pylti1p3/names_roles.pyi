import typing as t

from mypy_extensions import TypedDict
from typing_extensions import Literal

from .service_connector import ServiceConnector


class _Member(TypedDict):
    name: str
    status: Literal['Active', 'Inactive', 'Deleted']
    picture: str
    given_name: str
    family_name: str
    middle_name: str
    email: str
    user_id: str
    lis_person_sourcedid: str
    roles: t.List[str]


class NamesRolesProvisioningService:
    def __init__(
        self,
        service_connector: ServiceConnector,
        service_data: t.Dict[str, object],
    ) -> None:
        ...

    def get_members(self) -> t.List[_Member]:
        pass
