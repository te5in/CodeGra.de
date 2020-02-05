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

from psef import app
from cg_dt_utils import DatetimeWithTimezone

from . import api
from .. import auth, errors, models, helpers, features
from ..lti import v1_1 as lti_v1_1
from ..lti import v1_3 as lti_v1_3
from ..models import db

logger = structlog.get_logger()


def _make_blob_and_redirect(
    params: t.Mapping[str, object],
    version: str,
) -> werkzeug.wrappers.Response:
    data = {
        'params': {
            'data': params,
            'version': version,
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
    return _make_blob_and_redirect(params, 'lti_v1_1')


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


@api.route('/lti/launch/2', methods=['POST'])
@features.feature_required(features.Feature.LTI)
def second_phase_lti_launch() -> helpers.JSONResponse[
    t.Mapping[str, t.Union[str, models.Assignment, bool, None]]]:
    """Do the second part of an LTI launch.

    .. :quickref: LTI; Do the callback of a LTI launch.

    :>json string blob_id: The id of the blob which you got from the lti launch
        redirect.

    :<json assignment: The assignment that the LTI launch was for.
    :<json bool new_role_created: Was a new role created in the LTI launch.
    :<json access_token: A fresh access token for the current user. This value
        is not always available, this depends on internal state so you should
        simply check.
    :<json updated_email: The new email of the current user. This is value is
        also not always available, check!
    :raises APIException: If the given Jwt token is not valid. (INVALID_PARAM)
    """
    content = helpers.ensure_json_dict(flask.request.get_json())
    with helpers.get_from_map_transaction(content) as [get, _]:
        blob_id = get('blob_id', str)

    def also_error(b: models.BlobStorage) -> bool:
        age = helpers.get_request_start_time() - b.created_at
        # Older than 5 minutes is too old
        return age.total_seconds() > (60 * 5)

    blob = helpers.filter_single_or_404(
        models.BlobStorage,
        models.BlobStorage.id == uuid.UUID(blob_id),
        with_for_update=True,
        also_error=also_error,
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
                f'Decoding given JWT token failed, LTI is probably '
                'not configured correctly. Please contact your site admin.'
            ),
            f'The decoding of "{flask.request.headers.get("Jwt")}" failed.',
            errors.APICodes.INVALID_PARAM,
            400,
        )
    else:
        db.session.delete(blob)

    version = launch_params.pop('lti_version', 'lti_v1_1')
    if version == 'lti_v1_1':
        inst = lti_v1_1.LTI.create_from_launch_params(launch_params['data'])

        user, new_token, updated_email = inst.ensure_lti_user()
        auth.set_current_user(user)

        course = inst.get_course()
        assig = inst.get_assignment(user, course)
        inst.set_user_role(user)
        new_role_created = inst.set_user_course_role(user, course)

        db.session.commit()

        result: t.Mapping[str, t.Union[str, models.Assignment, bool, None]]
        result = {
            'assignment': assig,
            'new_role_created': new_role_created,
            'custom_lms_name': inst.lti_provider.lms_name,
        }
        if new_token is not None:
            result['access_token'] = new_token
        if updated_email:
            result['updated_email'] = updated_email
    elif version == 'lti_v1_3':
        result = {}
    else:
        assert False

    return helpers.jsonify(result)


@api.route('/lti1.3/login', methods=['GET', 'POST'])
def do_oidc_login() -> werkzeug.wrappers.Response:
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'

    req = flask.request
    if req.method == 'GET':
        target = req.args.get('target_link_uri')
    else:
        target = req.form.get('target_link_uri')

    assert target is not None
    oidc = lti_v1_3.FlaskOIDCLogin.from_request(req)
    red = oidc.get_redirect_object(target)
    logger.info(
        'Redirecting after oidc',
        target=target,
        get_args=req.args,
        post_args=req.form,
        redirect=red,
    )
    response = red.do_redirect()
    response.set_cookie(
        'cross-site-cookie', 'bar', samesite='None', secure=True
    )
    return response


@api.route('/lti1.3/launch', methods=['POST'])
def handle_lti_advantage_launch() -> werkzeug.wrappers.Response:
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'

    import pprint
    message_launch = lti_v1_3.FlaskMessageLaunch.from_request(flask.request)
    pprint.pprint(message_launch)
    message_launch_data = message_launch.get_launch_data()
    pprint.pprint(message_launch_data)

    return _make_blob_and_redirect(message_launch_data, version='lti_v1_3')
