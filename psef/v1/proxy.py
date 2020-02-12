"""This file contains all routes for proxies.

SPDX-License-Identifier: AGPL-3.0-only
"""
import os
import uuid
import mimetypes

import flask
import werkzeug

from . import api
from .. import files, models, helpers
from ..exceptions import APICodes, APIException


@api.route('/proxy/<uuid:proxy_id>/<path:path_str>', methods=['GET'])
def get_proxy_file(
    proxy_id: uuid.UUID, path_str: str
) -> werkzeug.wrappers.Response:
    """Get a file for the given proxy.

    :param proxy_id: The proxy in which you want to get a file.
    :param path: The path of the file you want to get.
    :returns: The found file, or a 404 error.
    """
    proxy = helpers.get_or_404(
        models.Proxy, proxy_id, also_error=lambda p: p.deleted
    )
    if proxy.expired:
        raise APIException(
            'This proxy has expired, please reload the page',
            f'The proxy "{proxy_id}" has expired.',
            APICodes.OBJECT_EXPIRED,
            400,
        )

    path, is_dir = files.split_path(os.path.normpath(path_str))
    if not path or is_dir:
        raise APIException(
            'The given path is empty or a directory.',
            f'The path "{path_str}" is not a normal file.',
            APICodes.OBJECT_NOT_FOUND, 404
        )
    found_file = proxy.get_file(path)
    if found_file is None:
        raise APIException(
            'The given file could not be found.',
            f'The path "{path_str}" was not found in this proxy.',
            APICodes.OBJECT_NOT_FOUND, 404
        )

    ctype, encoding = mimetypes.guess_type(path_str)
    res = flask.Response(found_file.open(), mimetype=ctype)
    res.headers['Content-Security-Policy'] = proxy.csp_header
    return res
