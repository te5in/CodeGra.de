"""
This module defines all API routes with the main directory "about". Thus
the APIs in this module are mostly used get information about the instance
running psef.

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t

import structlog
from flask import request, current_app

from . import api
from .. import models, permissions
from ..files import check_dir
from ..helpers import JSONResponse, jsonify
from ..permissions import CoursePermission

logger = structlog.get_logger()


@api.route('/about', methods=['GET'])
def about(
) -> JSONResponse[t.Mapping[str, t.Union[str, object, t.Mapping[str, bool]]]]:
    """Get the version and features of the currently running instance.

    .. :quickref: About; Get the version and features.

    :>json string version: The version of the running instance.
    :>json object features: A mapping from string to a boolean for every
        feature indicating if the current instance has it enabled.

    :returns: The mapping as described above.
    """
    _no_val = object()
    status_code = 200

    features = {
        key.name: bool(value)
        for key, value in current_app.config['FEATURES'].items()
    }

    res = {
        'version': current_app.config['_VERSION'],
        'features': features,
    }

    if request.args.get('health', _no_val) == current_app.config['HEALTH_KEY']:
        try:
            database = len(
                models.Permission.get_all_permissions(
                    permissions.CoursePermission
                )
            ) == len(CoursePermission)
        except:  # pylint: disable=bare-except
            logger.error('Database not working', exc_info=True)
            database = False

        uploads = check_dir(current_app.config['UPLOAD_DIR'])
        mirror_uploads = check_dir(current_app.config['MIRROR_UPLOAD_DIR'])

        res['health'] = {
            'application': True,
            'database': database,
            'uploads': uploads,
            'mirror_uploads': mirror_uploads,
        }

        if not all(res['health'].values()):
            status_code = 500

    return jsonify(res, status_code=status_code)
