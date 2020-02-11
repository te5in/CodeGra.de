import os
import json
import typing as t

import werkzeug
from pylti1p3.deployment import Deployment
from pylti1p3.oidc_login import OIDCLogin
from pylti1p3.tool_config import ToolConfAbstract
from pylti1p3.registration import Registration
from pylti1p3.message_launch import MessageLaunch

import flask

from ... import PsefFlask, models, helpers, current_app
from .flask import (
    FlaskRequest, FlaskRedirect, FlaskCookieService, FlaskSessionService
)

if t.TYPE_CHECKING:
    from pylti1p3.message_launch import _JwtData


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


class LTIConfig(ToolConfAbstract):
    def find_registration_by_issuer_and_client(
        self, iss: str, client_id: t.Optional[str]
    ) -> t.Optional[Registration]:
        if client_id is None:
            return self.find_registration_by_issuer(iss)

        return helpers.filter_single_or_404(
            models.LTI1p3Provider,
            models.LTI1p3Provider.iss == iss,
            models.LTI1p3Provider.client_id == client_id,
        ).get_registration()

    def find_registration_by_issuer(self, iss: str) -> Registration:
        return helpers.filter_single_or_404(
            models.LTI1p3Provider,
            models.LTI1p3Provider.iss == iss,
        ).get_registration()

    def find_deployment(
        self,
        iss: str,
        deployment_id: str,
    ) -> t.Optional[Deployment]:
        return None


class FlaskMessageLaunch(
    MessageLaunch[FlaskRequest, LTIConfig, FlaskSessionService,
                  FlaskCookieService]
):
    def _get_request_param(self, key: str) -> object:
        return self._request.get_param(key)

    @classmethod
    def from_request(cls, request: flask.Request) -> 'FlaskMessageLaunch':
        return cls(
            FlaskRequest(request, force_post=True),
            LTIConfig(),
            FlaskSessionService(request),
            FlaskCookieService(request),
        )

    # We never want to save the launch data in the session, as we have no
    # use-case for it, and it slows down every request
    def save_launch_data(self) -> 'FlaskMessageLaunch':
        return self

    def validate_deployment(self) -> 'FlaskMessageLaunch':
        return self

    @classmethod
    def from_message_data(
        cls,
        request: flask.Request,
        launch_data: t.Mapping[str, object],
    ) -> 'FlaskMessageLaunch':
        obj = cls(
            FlaskRequest(request, force_post=False),
            LTIConfig(),
            session_service=FlaskSessionService(request),
            cookie_service=FlaskCookieService(request),
        )

        return obj.set_auto_validation(enable=False) \
            .set_jwt(t.cast('_JwtData', {'body': launch_data})) \
            .set_restored() \
            .validate_registration()


class FlaskOIDCLogin(
    OIDCLogin[FlaskRequest, LTIConfig, FlaskSessionService, FlaskCookieService,
              werkzeug.wrappers.Response]
):
    def get_redirect(self, url: str) -> FlaskRedirect:
        return FlaskRedirect(url, self._cookie_service)

    @classmethod
    def from_request(cls, request: flask.Request) -> 'FlaskOIDCLogin':
        return FlaskOIDCLogin(
            FlaskRequest(request, force_post=False),
            LTIConfig(),
            FlaskSessionService(request),
            FlaskCookieService(request),
        )
