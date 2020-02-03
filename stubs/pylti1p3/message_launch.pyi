import typing as t
from abc import ABC, abstractmethod

from mypy_extensions import TypedDict
from typing_extensions import Literal

from .cookie import CookieService
from .request import Request
from .session import SessionService
from .deep_link import DeepLink
from .names_roles import NamesRolesProvisioningService
from .tool_config import ToolConfAbstract
from .assignments_grades import AssignmentsGradesService

T_SELF = t.TypeVar('T_SELF', bound='MessageLaunch')
REQ = t.TypeVar('REQ', bound=Request)
TCONF = t.TypeVar('TCONF', bound=ToolConfAbstract)
SES = t.TypeVar('SES', bound=SessionService)
COOK = t.TypeVar('COOK', bound=CookieService)

_RequiredLaunchData = TypedDict(
    '_RequiredLaunchData', {
        'https://purl.imsglobal.org/spec/lti/claim/message_type':
            Literal['LtiResourceLinkRequest', 'LtiDeepLinkingRequest'],
        'https://purl.imsglobal.org/spec/lti/claim/version': Literal['1.3.0'],
        'https://purl.imsglobal.org/spec/lti/claim/deployment_id': str,
        'https://purl.imsglobal.org/spec/lti/claim/target_link_uri': str,
        'https://purl.imsglobal.org/spec/lti/claim/resource_link':
            t.Mapping[str, str],
        'https://purl.imsglobal.org/spec/lti/claim/roles': t.List[str],
    },
    total=True
)

_OptionalLaunchData = TypedDict(
    '_OptionalLaunchData', {
        'https://purl.imsglobal.org/spec/lti/claim/context':
            t.Mapping[str, str],
        'https://purl.imsglobal.org/spec/lti/claim/lis': t.Mapping[str, str],
        'https://purl.imsglobal.org/spec/lti/claim/custom':
            t.Mapping[str, str],
    },
    total=False
)


class _LaunchData(_RequiredLaunchData, _OptionalLaunchData):
    pass


class MessageLaunch(ABC, t.Generic[REQ, TCONF, SES, COOK]):
    _request: REQ
    _tool_config: TCONF
    _session_service: SES
    _cookie_service: COOK

    def __init__(
        self,
        request: REQ,
        tool_config: TCONF,
        session_service: SES,
        cookie_service: COOK,
    ) -> None:
        ...

    @abstractmethod
    def _get_request_param(self, key: str) -> object:
        raise NotImplementedError

    def validate(self: T_SELF) -> T_SELF:
        ...

    def get_launch_data(self) -> _LaunchData:
        ...

    def is_resource_launch(self) -> bool:
        ...

    def is_deep_link_launch(self) -> bool:
        ...

    def get_launch_id(self) -> str:
        ...

    def get_deep_link(self) -> DeepLink:
        ...

    def has_nrps(self) -> bool:
        ...

    def get_nrps(self) -> NamesRolesProvisioningService:
        ...

    def has_ags(self) -> bool:
        ...

    def get_ags(self) -> AssignmentsGradesService:
        ...

    def save_launch_data(self: T_SELF) -> T_SELF:
        ...

    def validate_deployment(self: T_SELF) -> T_SELF:
        ...
