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
from typing_extensions import Literal

from psef import app
from cg_json import jsonify
from cg_dt_utils import DatetimeWithTimezone

from . import api
from .. import errors, models, helpers, parsers, features, exceptions
from ..lti import LTIVersion
from ..lti import v1_1 as lti_v1_1
from ..lti import v1_3 as lti_v1_3
from ..models import db
from ..lti.abstract import LTILaunchData

logger = structlog.get_logger()


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
) -> werkzeug.wrappers.Response:
    data = {
        'params': {
            'data': params,
            'version': version.__to_json__(),
        },
        'exp': DatetimeWithTimezone.utcnow() + timedelta(minutes=1)
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
            '&redirect={redirect}'
        ).format(
            host=app.config['EXTERNAL_URL'],
            blob_id=blob.id,
            redirect=urllib.parse.quote(
                flask.request.args.get('codegrade_redirect', ''),
            ),
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
    return _make_blob_and_redirect(params, LTIVersion.v1_1)


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


class _LTILaunchResult(TypedDict):
    data: LTILaunchData
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
    except jwt.DecodeError:
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
            f'The decoding of jwt failed.',
            errors.APICodes.INVALID_PARAM,
            400,
        )
    else:
        db.session.delete(blob)

    version = LTIVersion[launch_params.get('version', LTIVersion.v1_1)]
    data = launch_params['data']

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
            )

        launch_message = lti_v1_3.FlaskMessageLaunch.from_message_data(
            launch_data=data['launch_data'],
        )

        if not launch_message.is_resource_launch():
            raise exceptions.APIException(
                'Unknown LTI launch received, please contact support',
                'The received launch is not a resource launch',
                exceptions.APICodes.INVALID_STATE, 400
            )

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


@api.route('/lti1.3/login', methods=['GET', 'POST'])
def do_oidc_login() -> werkzeug.wrappers.Response:
    req = helpers.maybe_unwrap_proxy(flask.request, flask.Request)
    if req.method == 'GET':
        target = req.args.get('target_link_uri')
    else:
        target = req.form.get('target_link_uri')
    assert target is not None

    try:
        oidc = lti_v1_3.FlaskOIDCLogin.from_request()
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
            },
            version=LTIVersion.v1_3,
        )
    except pylti1p3.exception.OIDCException as exc:
        return _make_blob_and_redirect(
            {
                'type': 'exception',
                'exception_message': exc.args[0],
            },
            version=LTIVersion.v1_3,
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


@api.route('/lti1.3/launch', methods=['POST'])
def handle_lti_advantage_launch() -> t.Union[str, werkzeug.wrappers.Response]:
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'

    try:
        message_launch = lti_v1_3.FlaskMessageLaunch.from_request().validate()
    except (exceptions.APIException, pylti1p3.exception.LtiException) as exc:
        logger.info('Incorrect LTI launch encountered', exc_info=True)
        return _make_blob_and_redirect(
            {
                'type': 'exception',
                'exception_message':
                    (
                        exc.message
                        if isinstance(exc, exceptions.APIException) else
                        exc.args[0]
                    ),
            },
            version=LTIVersion.v1_3,
        )

    if message_launch.is_deep_link_launch():
        deep_link = message_launch.get_deep_link()
        return deep_link.output_response_form(
            [lti_v1_3.CGDeepLinkResource.make(app)]
        )

    return _make_blob_and_redirect(
        {
            'launch_data': message_launch.get_launch_data(),
            'request_args': dict(flask.request.args),
        },
        version=LTIVersion.v1_3,
    )


@api.route('/lti1.3/config/<lti_provider_id>', methods=['GET'])
def get_lti1_3_config(lti_provider_id: str) -> helpers.JSONResponse:
    lti_provider = helpers.filter_single_or_404(
        models.LTI1p3Provider, models.LTI1p3Provider.id == lti_provider_id
    )
    return jsonify(lti_provider.get_json_config())
