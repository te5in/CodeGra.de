import json
import typing as t
from datetime import timedelta
from dataclasses import dataclass

import structlog
import werkzeug.wrappers
from pylti1p3.cookie import CookieService
from pylti1p3.request import Request
from pylti1p3.session import SessionService
from pylti1p3.redirect import Redirect

import flask
import flask.sessions
from cg_dt_utils import DatetimeWithTimezone

logger = structlog.get_logger()
T = t.TypeVar('T')
Y = t.TypeVar('Y')
TEST_COOKIE_NAME = 'CG_TEST_COOKIE'


class FlaskRequest(Request):
    def __init__(self, *, force_post: bool) -> None:
        self._force_post = force_post

    def is_secure(self) -> bool:
        assert flask.request.is_secure, 'All LTI requests should be secure'
        return True

    @property
    def session(self) -> t.MutableMapping[str, t.Any]:
        return flask.session

    def get_param(self, key: str) -> object:
        if self._force_post or flask.request.method == 'POST':
            return flask.request.form.get(key, None)
        return flask.request.args.get(key, None)


class FlaskSessionService(SessionService):
    def __init__(self, request: FlaskRequest) -> None:
        super().__init__(request)

    def _get_key(
        self, key: str, nonce: t.Optional[str] = None, add_prefix: bool = True
    ) -> str:
        prefix = f'{self._session_prefix}-' if add_prefix else ''
        nonce = '' if nonce is None else f'-{nonce}'
        return f'{prefix}{key}{nonce}'

    def get_launch_data(self, key: str) -> t.Dict[str, object]:
        return self.data_storage.get_value(self._get_key(key))

    def save_launch_data(
        self, key: str, jwt_body: t.Dict[str, object]
    ) -> None:
        self.data_storage.set_value(self._get_key(key), jwt_body)

    def save_nonce(self, nonce: str) -> None:
        flask.session[self._get_key('lti-nonce')] = nonce

    def check_nonce(self, nonce: str) -> bool:
        nonce_key = self._get_key('lti-nonce')
        try:
            session_nonce = self.data_storage.get_value(nonce_key)
        except KeyError:
            return False
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
        self.data_storage.set_value(self._get_key(state), params)

    def get_state_params(self, state: str) -> t.Dict[str, object]:
        logger.info('Getting state params', state=state, session=flask.session)
        return self.data_storage.get_value(self._get_key(state))


class FlaskCookieService(CookieService):
    @dataclass
    class _CookieData:
        key: str
        value: str
        exp: DatetimeWithTimezone

    def __init__(self) -> None:
        self._cookie_data_to_set: t.List[FlaskCookieService._CookieData] = []

    def _get_key(self, key: str) -> str:
        return self._cookie_prefix + '-' + key

    def get_cookie(self, name: str) -> t.Optional[str]:
        logger.info(
            'Getting cookie', cookie_key=name, cookies=flask.request.cookies
        )
        return flask.request.cookies.get(self._get_key(name))

    def clear_cookie(self, name: str) -> None:
        self._cookie_data_to_set.append(FlaskCookieService._CookieData(
            key=self._get_key(name),
            value='',
            exp=DatetimeWithTimezone.utcfromtimestamp(0),
        ))

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
                path='/',
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
                    'window.location={loc};'
                    '</script></html>'
                ).format(loc=json.dumps(self._location))
            )
        )

    def set_redirect_url(self, location: str) -> None:
        self._location = location

    def get_redirect_url(self) -> str:
        return self._location
