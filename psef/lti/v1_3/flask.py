import typing as t
from datetime import timedelta
from dataclasses import dataclass

import pylti1p3
import structlog
import werkzeug.wrappers
from pylti1p3.cookie import CookieService
from pylti1p3.request import Request
from pylti1p3.session import SessionService
from pylti1p3.redirect import Redirect

import flask
from cg_dt_utils import DatetimeWithTimezone

logger = structlog.get_logger()


class FlaskRequest(Request):
    def __init__(self, request: flask.Request, *, force_post: bool) -> None:
        self._request = request
        self._force_post = force_post

    def set_request(self, request: flask.Request) -> None:
        self._request = request

    def get_request(self) -> flask.Request:
        return self._request

    def get_param(self, key: str) -> object:
        if self._force_post or self._request.method == 'POST':
            return self._request.form.get(key, None)
        return self._request.args.get(key, None)


class FlaskSessionService(SessionService):
    def __init__(self, request: flask.Request):
        self._request = request

    def _get_key(self, key: str) -> str:
        return self._session_prefix + '-' + key

    def get_launch_data(self, key: str) -> t.Dict[str, object]:
        return flask.session.get(self._get_key(key), None)

    def save_launch_data(
        self, key: str, jwt_body: t.Dict[str, object]
    ) -> None:
        flask.session[self._get_key(key)] = jwt_body

    def save_nonce(self, nonce: str) -> None:
        flask.session[self._get_key('lti-nonce')] = nonce

    def check_nonce(self, nonce: str) -> bool:
        nonce_key = self._get_key('lti-nonce')
        session_nonce = flask.session.get(nonce_key, None)
        logger.info(
            'Checking nonce',
            session_nonce=session_nonce,
            nonce_key=nonce_key,
            wanted_nonce=nonce,
        )
        return session_nonce == nonce

    def save_state_params(
        self, state: str, params: t.Dict[str, object]
    ) -> None:
        flask.session[self._get_key(state)] = params

    def get_state_params(self, state: str) -> t.Dict[str, object]:
        logger.info('Getting state params', state=state, session=flask.session)
        return flask.session[self._get_key(state)]


class FlaskCookieService(CookieService):
    @dataclass
    class _CookieData:
        key: str
        value: str
        exp: DatetimeWithTimezone

    def __init__(self, request: flask.Request):
        self._request = request
        self._cookie_data_to_set: t.List[FlaskCookieService._CookieData] = []

    def _get_key(self, key: str) -> str:
        return self._cookie_prefix + '-' + key

    def get_cookie(self, name: str) -> t.Optional[str]:
        logger.info(
            'Getting cookie', cookie_key=name, cookies=self._request.cookies
        )
        return self._request.cookies.get(self._get_key(name))

    def set_cookie(self, name: str, value: str, exp: int = 60) -> None:
        self._cookie_data_to_set.append(
            FlaskCookieService._CookieData(
                key=self._get_key(name),
                value=value,
                exp=DatetimeWithTimezone.utcnow() + timedelta(seconds=exp),
            )
        )

    def update_response(
        self, response: werkzeug.wrappers.Response
    ) -> werkzeug.wrappers.Response:
        for cookie_data in self._cookie_data_to_set:
            logger.info('Setting cookie', cookie=cookie_data)
            response.set_cookie(
                key=cookie_data.key,
                value=cookie_data.value,
                expires=cookie_data.exp,
                httponly=True,
                secure=True,
                samesite='None',
            )
        return response


class FlaskRedirect(Redirect[werkzeug.wrappers.Response]):
    def __init__(
        self,
        location: str,
        cookie_service: FlaskCookieService,
    ):
        self._location = location
        self._cookie_service = cookie_service

    def __repr__(self) -> str:
        return '{}.{}(location={})'.format(
            self.__class__.__module__,
            self.__class__.__qualname__,
            repr(self._location),
        )

    def _process_response(
        self, response: werkzeug.wrappers.Response
    ) -> werkzeug.wrappers.Response:
        return self._cookie_service.update_response(response)

    def do_redirect(self) -> werkzeug.wrappers.Response:
        return self._process_response(flask.redirect(self._location, code=303))

    def do_js_redirect(self) -> werkzeug.wrappers.Response:
        return self._process_response(
            flask.Response(
                (
                    '<!DOCTYPE html>'
                    '<html><script type="text/javascript">'
                    'window.location="{}";'
                    '</script></html>'
                ).format(self._location)
            )
        )

    def set_redirect_url(self, location: str) -> None:
        self._location = location

    def get_redirect_url(self) -> str:
        return self._location
