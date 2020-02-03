import os
import json
import typing as t

from pylti1p3 import oidc_login, message_launch
from pylti1p3.tool_config import ToolConfDict

import flask

from ... import PsefFlask, current_app
from .flask import (
    FlaskRequest, FlaskRedirect, FlaskCookieService, FlaskSessionService
)

if t.TYPE_CHECKING:
    MessageLaunch = message_launch.MessageLaunch
    OIDCLogin = oidc_login.OIDCLogin
else:
    # MessageLaunch, Redirect, and OIDCLogin are not really a generic class, so
    # we hack it to make it look like it is.

    class FakeGenericMeta(type):
        def __getitem__(self, item):
            return self

    class MessageLaunch(
        message_launch.MessageLaunch, metaclass=FakeGenericMeta
    ):
        pass

    class OIDCLogin(oidc_login.OIDCLogin, metaclass=FakeGenericMeta):
        pass


def init_app(app: PsefFlask) -> None:
    app.config['LTI1.3_CONFIG_JSON'] = {}
    app.config['LTI1.3_CONFIG_DIRNAME'] = ''

    path = app.config['_LTI1.3_CONFIG_JSON_PATH']
    if path is not None:
        app.config['LTI1.3_CONFIG_DIRNAME'] = os.path.dirname(path)
        with open(path, 'r') as f:
            conf = json.load(f)

            # Make sure the config is a t.Mapping[str, t.Mapping[str, str]]
            assert all(
                (
                    isinstance(v, dict) and
                    all(isinstance(vv, str) for vv in v.values())
                ) for v in conf.values()
            )

            app.config['LTI1.3_CONFIG_JSON'] = conf


class LTIConfig(ToolConfDict):
    @classmethod
    def from_app(cls, app: PsefFlask) -> 'LTIConfig':
        conf = app.config['LTI1.3_CONFIG_JSON']
        self = cls(conf)

        for iss in conf:
            private_key_file = conf[iss]['private_key_file']

            if not os.path.isabs(private_key_file):
                private_key_file = os.path.join(
                    app.config['LTI1.3_CONFIG_DIRNAME'], private_key_file
                )
            assert os.path.isfile(
                private_key_file
            ), 'Private key file does not exist'

            with open(private_key_file, 'r') as prf:
                self.set_private_key(iss, prf.read())

        return self


class FlaskMessageLaunch(
    MessageLaunch[FlaskRequest, LTIConfig, FlaskSessionService,
                  FlaskCookieService]
):
    def _get_request_param(self, key: str) -> object:
        return self._request.get_param(key)

    @classmethod
    def from_request(cls, request: flask.Request) -> 'FlaskMessageLaunch':
        return cls(
            FlaskRequest(request, use_post=True),
            LTIConfig.from_app(current_app),
            FlaskSessionService(request),
            FlaskCookieService(request),
        )

    # We never want to save the launch data in the session, as we have no
    # use-case for it, and it slows down every request
    def save_launch_data(self) -> 'FlaskMessageLaunch':
        return self


class FlaskOIDCLogin(
    OIDCLogin[FlaskRequest, LTIConfig, FlaskSessionService, FlaskCookieService,
              FlaskRedirect]
):
    def get_redirect(self, url: str) -> FlaskRedirect:
        return FlaskRedirect(url, self._cookie_service)

    @classmethod
    def from_request(cls, request: flask.Request) -> 'FlaskOIDCLogin':
        return FlaskOIDCLogin(
            FlaskRequest(request, use_post=False),
            LTIConfig.from_app(current_app),
            FlaskSessionService(request),
            FlaskCookieService(request),
        )
