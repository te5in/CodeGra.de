"""
This module implements all lti routes. Please note that a lot of these routes
are not useful for most clients as the ``/lti/launch/1`` route can only be used
by an approved LTI provider and the ``/lti/launch/2`` route can only be used
directly after a successful lti launch.

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t
import urllib
import datetime
import urllib.parse

import jwt
import flask
import werkzeug
import structlog

from psef import app

from . import api
from .. import lti, auth, errors, models, helpers, features
from ..lti import LTI
from ..models import db

logger = structlog.get_logger()


@api.route('/lti/launch/1', methods=['POST'])
@features.feature_required(features.Feature.LTI)
def launch_lti() -> t.Any:
    """Do a LTI launch.

    .. :quickref: LTI; Do a LTI Launch.
    """
    data = {
        'params': LTI.create_from_request(flask.request).launch_params,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=1)
    }
    return flask.redirect(
        '{host}/lti_launch/?inLTI=true&jwt={jwt}&redirect={redirect}'.format(
            host=app.config['EXTERNAL_URL'],
            jwt=urllib.parse.quote(
                jwt.encode(
                    data,
                    app.config['LTI_SECRET_KEY'],
                    algorithm='HS512',
                ).decode('utf8')
            ),
            redirect=urllib.parse.quote(
                flask.request.args.get('codegrade_redirect', '')
            )
        )
    )


@api.route('/lti/', methods=['GET'])
def get_lti_config() -> werkzeug.wrappers.Response:
    """Get a LTI config xml for this CodeGrade instance

    :qparam str lms: The name of the LMS to get the config for. This is
        required.

    :returns: An xml that can be used as a config for the specified LMS.
    """
    helpers.ensure_keys_in_dict(flask.request.args, [('lms', str)])
    lms: str = flask.request.args.get('lms', '')
    cls = lti.lti_classes.get(lms)
    if cls is not None:
        try:
            res = flask.make_response(cls.generate_xml())
        except NotImplementedError:
            pass
        else:
            res.headers['Content-Type'] = 'application/xml; charset=utf-8'
            return res

    raise errors.APIException(
        'The requested LMS does not support XML configuration',
        f'The LMS "{lms}" does not support XML configuration',
        errors.APICodes.INVALID_PARAM, 400
    )


@api.route('/lti/launch/2', methods=['POST'])
@features.feature_required(features.Feature.LTI)
def second_phase_lti_launch() -> helpers.JSONResponse[
    t.Mapping[str, t.Union[str, models.Assignment, bool, None]]]:
    """Do the second part of an LTI launch.

    .. :quickref: LTI; Do the callback of a LTI launch.

    :>json string jwt_token: The JWT token that is the current LTI state. This
        token can only be acquired using the ``/lti/launch/1`` route.

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
    helpers.ensure_keys_in_dict(content, [('jwt_token', str)])
    jwt_token = t.cast(str, content['jwt_token'])

    try:
        launch_params = jwt.decode(
            jwt_token,
            app.config['LTI_SECRET_KEY'],
            algorithms=['HS512'],
        )['params']
    except jwt.DecodeError:
        logger.warning(
            'Invalid JWT token encountered',
            token=jwt_token,
            exc_info=True,
        )
        raise errors.APIException(
            (
                'Decoding given JWT token failed, LTI is probably '
                'not configured right. Please contact your site admin.'
            ),
            f'The decoding of "{flask.request.headers.get("Jwt")}" failed.',
            errors.APICodes.INVALID_PARAM,
            400,
        )
    inst = LTI.create_from_launch_params(launch_params)

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
        'custom_lms_name': lti.lti_classes.get_key(inst.__class__),
    }
    if new_token is not None:
        result['access_token'] = new_token
    if updated_email:
        result['updated_email'] = updated_email

    return helpers.jsonify(result)
