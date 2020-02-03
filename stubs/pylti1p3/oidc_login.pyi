import abc
import typing as t

from .cookie import CookieService
from .request import Request
from .session import SessionService
from .redirect import Redirect
from .tool_config import ToolConfAbstract
from .registration import Registration

RED = t.TypeVar('RED')
REQ = t.TypeVar('REQ', bound=Request)
TCONF = t.TypeVar('TCONF', bound=ToolConfAbstract)
SES = t.TypeVar('SES', bound=SessionService)
COOK = t.TypeVar('COOK', bound=CookieService)


class OIDCLogin(abc.ABC, t.Generic[REQ, TCONF, SES, COOK, RED]):
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

    @abc.abstractmethod
    def get_redirect(self, url: str) -> RED:
        raise NotImplementedError

    def redirect(self, launch_url: str, js_redirect: bool = False) -> RED:
        ...

    def get_redirect_object(self, launch_url: str) -> Redirect[RED]:
        ...

    def validate_oidc_login(self) -> Registration:
        ...

    def pass_params_to_launch(self, params: t.Dict[str, str]) -> None:
        ...
