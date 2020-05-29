"""
This module implements all lti routes. Please note that a lot of these routes
are not useful for most clients as the ``/lti/launch/1`` route can only be used
by an approved LTI provider and the ``/lti/launch/2`` route can only be used
directly after a successful lti launch.

SPDX-License-Identifier: AGPL-3.0-only
"""
import uuid
import typing as t
import urllib
import urllib.parse
from datetime import timedelta

import jwt
import flask
import werkzeug
import structlog
import pylti1p3.exception
from mypy_extensions import TypedDict
from typing_extensions import Final, Literal
from pylti1p3.deep_link import DeepLink

from psef import app
from cg_json import JSONResponse, jsonify
from cg_dt_utils import DatetimeWithTimezone

from . import api
from .. import (
    auth, errors, models, helpers, parsers, features, registry, exceptions
)
from ..lti import LTIVersion
from ..lti import v1_1 as lti_v1_1
from ..lti import v1_3 as lti_v1_3
from ..models import db
from ..lti.abstract import LTILaunchData

logger = structlog.get_logger()


def _maybe_get_provider(provider_id: t.Optional[str]
                        ) -> t.Optional[models.LTI1p3Provider]:
    if provider_id is None:
        return None
    else:
        return helpers.get_or_404(models.LTI1p3Provider, provider_id)


def _convert_boolean(value: t.Union[bool, str, None], default: bool) -> bool:
    """Convert possible string value to boolean.

    >>> cv = _convert_boolean
    >>> s = object()
    >>> cv('true', s)
    True
    >>> cv('false', s)
    False
    >>> cv(True, s)
    True
    >>> cv('not a bool', s) is s
    True
    >>> cv(None, s) is s
    True
    """
    if isinstance(value, bool):
        return value
    elif isinstance(value, str) and value.lower() in {'true', 'false'}:
        return value.lower() == 'true'
    return default


def _make_blob_and_redirect(
    params: t.Mapping[str, object],
    version: LTIVersion,
    goto_latest_submission: bool,
) -> werkzeug.wrappers.Response:
    data = {
        'params': {
            'data': params,
            'version': version.__to_json__(),
        },
        'exp': DatetimeWithTimezone.utcnow() + timedelta(minutes=5)
    }
    blob = models.BlobStorage(
        data=jwt.encode(
            data,
            app.config['LTI_SECRET_KEY'],
            algorithm='HS512',
        )
    )
    db.session.add(blob)
    db.session.commit()

    return flask.redirect(
        (
            '{host}/lti_launch/?inLTI=true&blob_id={blob_id}'
            '&redirect={redirect}&goto_latest_submission={goto_latest}'
        ).format(
            host=app.config['EXTERNAL_URL'],
            blob_id=blob.id,
            redirect=urllib.parse.quote(
                flask.request.args.get('codegrade_redirect', ''),
            ),
            goto_latest=goto_latest_submission,
        ),
        code=303,
    )


@api.route('/lti/launch/1', methods=['POST'])
@features.feature_required(features.Feature.LTI)
def launch_lti() -> t.Any:
    """Do a LTI launch.

    .. :quickref: LTI; Do a LTI Launch.
    """
    params = lti_v1_1.LTI.create_from_request(flask.request).launch_params
    return _make_blob_and_redirect(
        params, LTIVersion.v1_1, goto_latest_submission=False
    )


@api.route('/lti/', methods=['GET'])
def get_lti_config() -> werkzeug.wrappers.Response:
    """Get a LTI config xml for this CodeGrade instance

    .. :quickref: LTI; Get the configuration for a LMS.

    :qparam str lms: The name of the LMS to get the config for. This is
        required.

    :returns: An xml that can be used as a config for the specified LMS.
    """
    helpers.ensure_keys_in_dict(flask.request.args, [('lms', str)])
    lms: str = flask.request.args.get('lms', '')
    cls = lti_v1_1.lti_classes.get(lms)
    if cls is None:
        raise errors.APIException(
            f'The given LMS "{lms}" was not found',
            f'The LMS "{lms}" is not yet supported by CodeGrade',
            errors.APICodes.OBJECT_NOT_FOUND, 404
        )

    if cls.supports_lti_common_cartridge():
        res = flask.make_response(cls.generate_xml())
        res.headers['Content-Type'] = 'application/xml; charset=utf-8'
        return res
    else:
        raise errors.APIException(
            f'{lms} does not support Common Cartridge configuration',
            f'The LMS "{lms}" does not support Common Cartridge configuration',
            errors.APICodes.INVALID_PARAM, 400
        )


class LTIDeeplinkResult(TypedDict):
    type: Literal['deep_link']
    deep_link_blob_id: str
    auth_token: str


class _LTILaunchResult(TypedDict):
    data: t.Union[LTILaunchData, LTIDeeplinkResult]
    version: LTIVersion


def _get_second_phase_lti_launch_data(blob_id: str) -> _LTILaunchResult:
    blob = helpers.filter_single_or_404(
        models.BlobStorage,
        models.BlobStorage.id == uuid.UUID(blob_id),
        with_for_update=True,
        also_error=lambda b: b.age > timedelta(minutes=5),
    )

    try:
        launch_params = jwt.decode(
            blob.data,
            app.config['LTI_SECRET_KEY'],
            algorithms=['HS512'],
        )['params']
    except jwt.PyJWTError:
        logger.warning(
            'Invalid JWT token encountered',
            blob_id=str(blob.id),
            exc_info=True,
        )
        raise errors.APIException(
            (
                'Decoding given JWT token failed, LTI is probably '
                'not configured correctly. Please contact your site admin.'
            ),
            'The decoding of jwt failed.',
            errors.APICodes.INVALID_PARAM,
            400,
        )
    else:
        db.session.delete(blob)

    version = LTIVersion[launch_params.get('version', LTIVersion.v1_1)]
    data = launch_params['data']
    result: t.Union[LTILaunchData, LTIDeeplinkResult]

    if version == LTIVersion.v1_1:
        inst = lti_v1_1.LTI.create_from_launch_params(data)
        result = inst.do_second_step_of_lti_launch()
    elif version == LTIVersion.v1_3:
        if data.get('type') == 'exception':
            raise exceptions.APIException(
                data.get('exception_message'),
                'An error occured when processing the LTI1.3 launch',
                exceptions.APICodes.LTI1_3_ERROR,
                400,
                original_exception=data.get('original_exception'),
            )

        lti_provider = helpers.get_or_404(
            models.LTI1p3Provider, data['lti_provider_id']
        )
        launch_message = lti_v1_3.FlaskMessageLaunch.from_message_data(
            launch_data=data['launch_data'], lti_provider=lti_provider
        )

        if launch_message.is_deep_link_launch():
            deep_link_settings = launch_message.get_deep_link_settings()

            auth_token = str(uuid.uuid4())
            blob = models.BlobStorage(
                json={
                    'type': 'deep_link_settings',
                    'deep_link_settings': deep_link_settings,
                    'deployment_id': launch_message._get_deployment_id(),
                    'auth_token': auth_token,
                    'lti_provider_id': str(lti_provider.id),
                },
            )
            db.session.add(blob)
            db.session.flush()
            result = {
                'type': 'deep_link',
                'deep_link_blob_id': str(blob.id),
                'auth_token': auth_token,
            }
        else:
            result = launch_message.do_second_step_of_lti_launch()
    else:
        assert False

    return {
        'version': version,
        'data': result,
    }


@api.route('/lti/launch/2', methods=['POST'])
@features.feature_required(features.Feature.LTI)
def second_phase_lti_launch(
) -> helpers.JSONResponse[t.Union[_LTILaunchResult, t.Dict[str, t.Any]]]:
    """Do the second part of an LTI launch.

    .. :quickref: LTI; Do the callback of a LTI launch.

    :>json string blob_id: The id of the blob which you got from the lti launch
        redirect.

    :returns: A _LTILaunch instance.
    :raises APIException: If the given Jwt token is not valid. (INVALID_PARAM)
    """
    with helpers.get_from_map_transaction(
        helpers.get_json_dict_from_request()
    ) as [get, _]:
        blob_id = get('blob_id', str)

    res = _get_second_phase_lti_launch_data(blob_id)
    db.session.commit()

    if helpers.extended_requested():
        return jsonify(res)

    return jsonify(t.cast(dict, res['data']))


@api.route('/lti1.3/login/<lti_provider_id>', methods=['GET', 'POST', 'HEAD'])
@api.route('/lti1.3/login', methods=['GET', 'POST', 'HEAD'])
def do_oidc_login(
    lti_provider_id: t.Optional[str] = None
) -> werkzeug.wrappers.Response:
    req = helpers.maybe_unwrap_proxy(flask.request, flask.Request)
    if req.method == 'GET':
        target = req.args.get('target_link_uri')
    else:
        target = req.form.get('target_link_uri')
    assert target is not None

    try:
        provider = _maybe_get_provider(lti_provider_id)
        oidc = lti_v1_3.FlaskOIDCLogin.from_request(lti_provider=provider)
        red = oidc.get_redirect_object(target)
    except exceptions.APIException as exc:
        logger.info('Login request went wrong', exc_info=True)

        if exc.api_code == exceptions.APICodes.OBJECT_NOT_FOUND:
            message = (
                'This LMS was not found as a LTIProvider for CodeGrade, this'
                ' is probably caused by a wrong setup.'
            )
        else:
            message = exc.message

        return _make_blob_and_redirect(
            {
                'type': 'exception',
                'exception_message': message,
                'original_exception': JSONResponse.dump_to_object(exc),
            },
            version=LTIVersion.v1_3,
            goto_latest_submission=False,
        )
    except pylti1p3.exception.OIDCException as exc:
        return _make_blob_and_redirect(
            {
                'type': 'exception',
                'exception_message': exc.args[0],
            },
            version=LTIVersion.v1_3,
            goto_latest_submission=False,
        )
    logger.info(
        'Redirecting after oidc',
        target=target,
        get_args=req.args,
        post_args=req.form,
        redirect=red,
    )
    return red.do_redirect()


@api.route('/lti1.3/jwks/<lti_provider_id>', methods=['GET'])
def get_lti_provider_jwks(lti_provider_id: str) -> helpers.JSONResponse:
    lti_provider = helpers.filter_single_or_404(
        models.LTI1p3Provider, models.LTI1p3Provider.id == lti_provider_id
    )
    return jsonify({'keys': [lti_provider.get_public_jwk()]})


@api.route('/lti1.3/launch/<lti_provider_id>', methods=['POST'])
@api.route('/lti1.3/launch', methods=['POST'])
def handle_lti_advantage_launch(lti_provider_id: t.Optional[str] = None
                                ) -> t.Union[str, werkzeug.wrappers.Response]:

    return _handle_lti_advantage_launch(lti_provider_id, goto_latest_sub=False)


@api.route(
    '/lti1.3/launch_to_latest_submission/<lti_provider_id>', methods=['POST']
)
@api.route('/lti1.3/launch_to_latest_submission', methods=['POST'])
def handle_lti_advantage_launch_to_latest_sub(
    lti_provider_id: t.Optional[str] = None
) -> t.Union[str, werkzeug.wrappers.Response]:
    return _handle_lti_advantage_launch(lti_provider_id, goto_latest_sub=True)


def _handle_lti_advantage_launch(
    lti_provider_id: t.Optional[str], goto_latest_sub: bool
) -> t.Union[str, werkzeug.wrappers.Response]:
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'

    plat_red_url = flask.request.args.get('platform_redirect_url')
    full_win_launch = flask.request.args.get('full_win_launch_requested')
    if full_win_launch == '1' and plat_red_url:
        return flask.redirect(plat_red_url)

    try:
        provider = _maybe_get_provider(lti_provider_id)
        message_launch = lti_v1_3.FlaskMessageLaunch.from_request(
            lti_provider=provider,
        ).validate()
    except exceptions.APIException as exc:
        logger.info('An error occurred during the LTI launch', exc_info=True)
        return _make_blob_and_redirect(
            {
                'type': 'exception',
                'exception_message': exc.message,
                'original_exception': JSONResponse.dump_to_object(exc),
            },
            version=LTIVersion.v1_3,
            goto_latest_submission=False,
        )
    except pylti1p3.exception.LtiException as exc:
        logger.info('Incorrect LTI launch encountered', exc_info=True)
        return _make_blob_and_redirect(
            {
                'type': 'exception',
                'exception_message': exc.args[0],
            },
            version=LTIVersion.v1_3,
            goto_latest_submission=False,
        )

    provider = message_launch.get_lti_provider()
    if (
        message_launch.is_deep_link_launch() and
        not provider.lms_capabilities.actual_deep_linking_required
    ):
        deep_link = message_launch.get_deep_link()
        dp_resource = lti_v1_3.CGDeepLinkResource.make(message_launch)
        return deep_link.output_response_form([dp_resource])

    return _make_blob_and_redirect(
        {
            'launch_data': message_launch.get_launch_data(),
            'lti_provider_id': message_launch.get_lti_provider().id,
            'request_args': dict(flask.request.args),
        },
        version=LTIVersion.v1_3,
        goto_latest_submission=goto_latest_sub,
    )


@api.route('/lti1.3/config/<lti_provider_id>', methods=['GET'])
def get_lti1_3_config(lti_provider_id: str) -> helpers.JSONResponse:
    lti_provider = helpers.filter_single_or_404(
        models.LTI1p3Provider, models.LTI1p3Provider.id == lti_provider_id
    )
    return jsonify(lti_provider.get_json_config())


@api.route('/lti1.3/providers/', methods=['get'])
@auth.login_required
def list_lti1p3_provider(
) -> helpers.JSONResponse[t.List[models.LTI1p3Provider]]:
    providers = [
        prov for prov in models.LTI1p3Provider.query
        if auth.LTI1p3ProviderPermissions(prov).ensure_may_see.as_bool()
    ]
    return jsonify(providers)


@api.route('/lti1.3/providers/', methods=['POST'])
@auth.login_required
def create_lti1p3_provider() -> helpers.JSONResponse[models.LTI1p3Provider]:
    with helpers.get_from_request_transaction() as [get, _]:
        iss = get('iss', str)
        caps = get(
            'lms',
            registry.lti_1_3_lms_capabilities,
            transform=lambda x: x[1],
        )
        intended_use = get('intended_use', str)

    if intended_use == '' or iss == '':
        raise exceptions.APIException(
            'Both "intended_use" and "iss" must be non empty',
            f'Either iss={iss} or intended_use={intended_use} was empty',
            exceptions.APICodes.INVALID_PARAM, 400
        )

    lti_provider = models.LTI1p3Provider.create_and_generate_keys(
        iss=iss,
        lms_capabilities=caps,
        intended_use=intended_use,
    )
    auth.LTI1p3ProviderPermissions(lti_provider).ensure_may_add()

    db.session.add(lti_provider)
    db.session.commit()

    return jsonify(lti_provider)


@api.route('/lti1.3/providers/<lti_provider_id>', methods=['GET'])
def get_lti1p3_provider(lti_provider_id: str
                        ) -> helpers.JSONResponse[models.LTI1p3Provider]:
    lti_provider = helpers.filter_single_or_404(
        models.LTI1p3Provider, models.LTI1p3Provider.id == lti_provider_id
    )
    secret = flask.request.args.get('secret')
    auth.LTI1p3ProviderPermissions(
        lti_provider, secret=secret
    ).ensure_may_see()
    return jsonify(lti_provider)


@api.route('/lti1.3/providers/<lti_provider_id>', methods=['PATCH'])
def update_lti1p3_provider(lti_provider_id: str
                           ) -> helpers.JSONResponse[models.LTI1p3Provider]:
    lti_provider = helpers.filter_single_or_404(
        models.LTI1p3Provider, models.LTI1p3Provider.id == lti_provider_id
    )
    secret = flask.request.args.get('secret')
    auth.LTI1p3ProviderPermissions(
        lti_provider, secret=secret
    ).ensure_may_edit()

    with helpers.get_from_request_transaction() as [_, opt_get]:
        client_id = opt_get('client_id', str, None)
        auth_token_url = opt_get('auth_token_url', str, None)
        auth_login_url = opt_get('auth_login_url', str, None)
        key_set_url = opt_get('key_set_url', str, None)
        auth_audience = opt_get('auth_audience', str, None)
        finalize = opt_get('finalize', bool, None)

    lti_provider.update_registration(
        client_id=client_id,
        auth_token_url=auth_token_url,
        auth_login_url=auth_login_url,
        key_set_url=key_set_url,
        auth_audience=auth_audience,
        finalize=finalize,
    )

    db.session.commit()

    return jsonify(lti_provider)


@api.route('/lti1.3/deep_link/<uuid:deep_link_blob_id>', methods=['POST'])
def deep_link_lti_assignment(
    deep_link_blob_id: uuid.UUID
) -> helpers.JSONResponse:
    # TODO: Maybe we should use some kind of session information here to do
    # more authentication.
    blob = helpers.filter_single_or_404(
        models.BlobStorage,
        models.BlobStorage.id == deep_link_blob_id,
        with_for_update=True,
    )
    db.session.delete(blob)
    blob_json = blob.as_json()
    assert isinstance(blob_json, dict)
    assert blob_json['type'] == 'deep_link_settings'

    # We need a bit longer expiration here compared to other uses of the blob
    # storage in this module as users need to have the time to actually input
    # the needed data.
    if blob.age > timedelta(days=1):
        raise errors.APIException(
            'This deep linking session has expired, please reload',
            f'The deep linking session with blob {blob.id} has expired',
            errors.APICodes.OBJECT_EXPIRED, 400
        )

    provider = helpers.get_or_404(
        models.LTI1p3Provider, blob_json['lti_provider_id']
    )

    with helpers.get_from_request_transaction() as [get, _]:
        auth_token = get('auth_token', str)
        name = get('name', str)
        deadline_str = get('deadline', str)

    if auth_token != blob_json['auth_token']:
        raise exceptions.PermissionException(
            'You did not provide the correct token to deep link an assignment',
            f'The provided token {auth_token} is not correct',
            exceptions.APICodes.INCORRECT_PERMISSION, 403
        )

    deadline = parsers.parse_datetime(deadline_str)

    dp_resource = lti_v1_3.CGDeepLinkResource.make(
        lti_provider=provider, deadline=deadline
    ).set_title(name)
    deep_link_settings = t.cast(t.Any, blob_json['deep_link_settings'])
    deep_link = DeepLink(
        lti_v1_3.CGRegistration(provider),
        t.cast(str, blob_json['deployment_id']),
        deep_link_settings,
    )
    db.session.commit()
    return JSONResponse.make(
        {
            'url': deep_link_settings['deep_link_return_url'],
            'jwt': deep_link.get_response_jwt([dp_resource]),
        }
    )
