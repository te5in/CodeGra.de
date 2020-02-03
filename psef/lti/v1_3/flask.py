import typing as t
from dataclasses import dataclass

import flask
import werkzeug.wrappers
from pylti1p3 import redirect
from pylti1p3.cookie import CookieService
from pylti1p3.request import Request
from pylti1p3.session import SessionService

if t.TYPE_CHECKING:
    Redirect = redirect.Redirect
else:
    # Redirect is not really a generic class, so we hack it to make it look
    # like it is.

    class FakeGenericMeta(type):
        def __getitem__(self, item):
            return self

    class Redirect(redirect.Redirect, metaclass=FakeGenericMeta):
        pass


class FlaskRequest(Request):
    def __init__(self, request: flask.Request, use_post: bool) -> None:
        self._request = request
        self._use_post = use_post

    def set_request(self, request: flask.Request) -> None:
        self._request = request

    def get_param(self, key: str) -> object:
        if self._use_post:
            return self._request.form.get(key, None)
        return self._request.args.get(key, None)


class FlaskSessionService(SessionService):
    def __init__(self, request: flask.Request):
        self._request = request

    def _get_key(self, key: str) -> str:
        return self._session_prefix + '-' + key

    def get_launch_data(self, key: str) -> t.Dict[str, object]:
        return self._request.session.get(self._get_key(key), None)

    def save_launch_data(
        self, key: str, jwt_body: t.Dict[str, object]
    ) -> None:
        self._request.session[self._get_key(key)] = jwt_body

    def save_nonce(self, nonce: str) -> None:
        self._request.session[self._get_key('lti-nonce')] = nonce

    def check_nonce(self, nonce: str) -> bool:
        nonce_key = self._get_key('lti-nonce')
        return self._request.session.get(nonce_key, None) == nonce_key

    def save_state_params(
        self, state: str, params: t.Dict[str, object]
    ) -> None:
        self._request.session[self._get_key(state)] = params

    def get_state_params(self, state: str) -> t.Dict[str, object]:
        return self._request.session[self._get_key(state)]


class FlaskCookieService(CookieService):
    @dataclass
    class _CookieData:
        key: str
        value: str
        exp: int

    def __init__(self, request: flask.Request):
        self._request = request
        self._cookie_data_to_set: t.List[FlaskCookieService._CookieData] = []

    def _get_key(self, key: str) -> str:
        return self._cookie_prefix + '-' + key

    def get_cookie(self, name: str) -> t.Optional[str]:
        return self._request.cookies.get(self._get_key(name))

    def set_cookie(self, name: str, value: str, exp: int = 3600) -> None:
        self._cookie_data_to_set.append(
            FlaskCookieService._CookieData(
                key=name,
                value=value,
                exp=exp,
            )
        )

    def update_response(self, response: werkzeug.wrappers.Response) -> None:
        for cookie_data in self._cookie_data_to_set:
            response.set_cookie(
                key=cookie_data.key,
                value=cookie_data.value,
                expires=cookie_data.exp,
                httponly=True,
                secure=True,
            )


class FlaskRedirect(Redirect[werkzeug.wrappers.Response]):
    def __init__(
        self,
        location: str,
        cookie_service: t.Optional[FlaskCookieService] = None
    ):
        self._location = location
        self._cookie_service = cookie_service

    def _process_response(
        self, response: werkzeug.wrappers.Response
    ) -> werkzeug.wrappers.Response:
        if self._cookie_service is not None:
            self._cookie_service.update_response(response)
        return response

    def do_redirect(self) -> werkzeug.wrappers.Response:
        return self._process_response(flask.redirect(self._location))

    def do_js_redirect(self) -> werkzeug.wrappers.Response:
        return self._process_response(
            flask.Response(
                (
                    '<!DOCTYPE html>'
                    '<html><script type="text/javascript">'
                    'window.location={};'
                    '</script></html>'
                ).format(self._location)
            )
        )

    def set_redirect_url(self, location: str) -> None:
        self._location = location

    def get_redirect_url(self) -> str:
        return self._location
