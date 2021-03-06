"""This module implements the needed abstract connector classes for
``pylti1p3``.

The main library we use for LTI 1.3 (:mod:`.pylti1p3`) abstracts the
web-framework used away using classes that have to implement specific
functionality, such as access to cookies. This file implements these methods
for ``flask``, as used by :mod:`.psef`.

This file predates the implementation of the contrib module in ``pylti1p3`` for
``flask``, which now exists. However, this module implements these classes
different than ``pylti1p3`` does, and we depend on this behavior in quite some
locations.

SPDX-License-Identifier: AGPL-3.0-only
"""
import json
import typing as t
from datetime import timedelta
from dataclasses import dataclass

import flask
import structlog
import flask.sessions
import werkzeug.wrappers
from pylti1p3.cookie import CookieService
from pylti1p3.request import Request
from pylti1p3.session import SessionService
from pylti1p3.redirect import Redirect

from cg_dt_utils import DatetimeWithTimezone

logger = structlog.get_logger()
T = t.TypeVar('T')
Y = t.TypeVar('Y')
TEST_COOKIE_NAME = 'CG_TEST_COOKIE'


class FlaskRequest(Request):
    """Implements a pylti1p3 :class:`.Request` for flask.

    This class gets all its information from the global flask ``request``
    object. So creating multiple is really useless.
    """

    def __init__(self, *, force_post: bool) -> None:
        self._force_post = force_post

    def is_secure(self) -> bool:  # pragma: no cover
        """Check if request is secure.
        """
        # Method is not used, but we have to implement it for to adhere to the
        # base class.
        return flask.request.is_secure

    @property
    def session(self) -> t.MutableMapping[str, t.Any]:
        return flask.session

    def get_param(self, key: str) -> object:
        if self._force_post or flask.request.method == 'POST':
            return flask.request.form.get(key, None)
        return flask.request.args.get(key, None)


class FlaskSessionService(SessionService):
    """Implements the :class:`.SessionService` for flask.
    """

    # This delegation is not useless it used for mypy to make sure we only
    # allow ``FlaskRequest`` objects to given as argument.
    def __init__(self, request: FlaskRequest) -> None:  # pylint: disable=useless-super-delegation
        super().__init__(request)

    def _get_key(
        self, key: str, nonce: t.Optional[str] = None, add_prefix: bool = True
    ) -> str:
        prefix = f'{self._session_prefix}-' if add_prefix else ''
        nonce = '' if nonce is None else f'-{nonce}'
        return f'{prefix}{key}{nonce}'

    def get_launch_data(self, key: str) -> t.Dict[str, object]:
        assert False, 'We never want to save the launch data in the session'

    def save_launch_data(
        self, key: str, jwt_body: t.Dict[str, object]
    ) -> None:
        assert False, 'We never want to save the launch data in the session'

    def save_nonce(self, nonce: str) -> None:
        logger.info('Saving nonce', nonce=nonce)
        flask.session[self._get_key('lti-nonce')] = nonce

    def check_nonce(self, nonce: str) -> bool:
        nonce_key = self._get_key('lti-nonce')
        session_nonce = self.data_storage.get_value(nonce_key)
        logger.info(
            'Checking nonce',
            session_nonce=session_nonce,
            nonce_key=nonce_key,
            wanted_nonce=nonce,
        )
        return session_nonce == nonce


class FlaskCookieService(CookieService):
    """The implementation for the :class:`.CookieService` for flask.
    """

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
        self._cookie_data_to_set.append(
            FlaskCookieService._CookieData(
                key=self._get_key(name),
                value='',
                exp=DatetimeWithTimezone.utcfromtimestamp(0),
            )
        )

    def set_cookie(self, name: str, value: str, exp: int = 60) -> None:
        """Set a cookie named ``name`` to the given ``value``.

        This doesn't actually set the cookie yet, you seed to use
        :meth:`.CookieService.update_response` to actually set the cookies on a
        response.

        :param name: The name of the cookie to set.
        :param value: The value of the cookie.
        :param exp: The expiration date of the cookie in seconds.

        :returns: Nothing.
        """
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
        """Update the given ``response`` to actually set the cookies set by
        this instance.

        :param response: The response to update. This response will be mutated.

        :returns: The same response as given, but now updated with the cookies
                  that need to be set.
        """
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
    """This implements the :class:`.Redirect` class for flask.

    This sets all the cookies set by the cookie service before redirecting, as
    this needs to be done on the response object in flask, to which the
    :class:`.FlaskCookieService` has no access.
    """

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
        return self._process_response(
            flask.redirect(self.get_redirect_url(), code=303)
        )

    def do_js_redirect(self) -> werkzeug.wrappers.Response:  # pragma: no cover
        """This method does a redirect using javascript

        .. note::

            Don't use this method, simply redirect using
            :meth:`.FlaskRedirect.do_redirect`
        """
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

    def set_redirect_url(self, location: str) -> None:  # pragma: no cover
        """Set the redirect url of this redirect.
        """
        # We have to override this method, but we don't actually use it.
        self._location = location

    def get_redirect_url(self) -> str:
        return self._location
