import typing as t

from mypy_extensions import TypedDict

from .registration import Registration


class _ServiceConnectorResponse(TypedDict):
    headers: t.Dict[str, str]
    body: t.Union[None, int, float, t.List[object], t.Dict[str, object], str]


class ServiceConnector:
    def __init__(self, registration: Registration) -> None:
        ...

    def make_service_request(
        self,
        scopes: t.List[str],
        url: str,
        is_post: bool = False,
        data: t.Optional[str] = None,
        content_type: str = 'application/json',
        accept: str = 'application/json',
    ) -> _ServiceConnectorResponse:
        ...
